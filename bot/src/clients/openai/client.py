import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from clients.openai.scheme import OpenAICompletion, ChatMessage, ChatMessages, OpenAIChatChoices
from utils.token_api_request_manager import TokenApiRequestPureManager, TokenApiManagerABC

logger = logging.getLogger(__name__)


class OpenAIMaxTokenExceededError(Exception):
    pass


class OpenAIInvalidRequestError(Exception):
    pass


@dataclass
class DallEResponse:
    url: str
    revised_prompt: str
    error: Optional[str] = None


class OpenAIClient:
    COMPLETION_MAX_LENGTH = 4097
    ERROR_MAX_TOKEN_MESSAGE = 'This model\'s maximum context'
    DEFAULT_NO_COMPLETION_CHOICE_RESPONSE = 'A?'
    DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES = {401}
    DEFAULT_FORCE_MAIN_TOKEN_STATUSES = {400}
    DEFAULT_RETRY_ON_429 = 1  # Thus, totally 2 times.

    DEFAULT_CHAT_BOT_ROLE = 'assistant'
    DEFAULT_IMAGE_PROMT_PREFIX = (
        'I NEED to test how the tool works with extremely simple prompts. '
        'DO NOT add any detail, just use it AS-IS:'
    )

    class Method(Enum):
        COMPLETIONS = 'completions'
        CHAT_COMPLETIONS = 'chat/completions'
        IMAGE_GENERATION = 'images/generations'

    def __init__(
        self,
        token: Optional[str] = None,
        token_api_request_manager: Optional[TokenApiManagerABC] = None,
        endpoint: str = 'https://api.openai.com/v1/',
    ):
        if not token and not token_api_request_manager:
            raise Exception('Rather token or token_api_request_manager should be defined.')
        if not token_api_request_manager:
            self.token_api_request_manager = TokenApiRequestPureManager(token)
        else:
            self.token_api_request_manager = token_api_request_manager

        self.endpoint = endpoint

    async def _make_request(self, method: Method, data: dict, try_count: int = 0):
        url = self.endpoint + method.value
        api_manager_response = await self.token_api_request_manager.make_request(
            url=url, data=data, rotate_statuses=self.DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES,
            force_main_token_statuses=self.DEFAULT_FORCE_MAIN_TOKEN_STATUSES,
        )
        response = api_manager_response.json
        status = api_manager_response.status
        logger.debug('[OpenAIClient] Got response %s with status %s', response, status)

        if status == 400 and response.get('error', {}).get('message', '').startswith(
                self.ERROR_MAX_TOKEN_MESSAGE):
            logger.warning('[OpenAIClient] Got invalid_request_error from openai, raise related exception.')
            raise OpenAIMaxTokenExceededError

        if status == 429 and try_count <= self.DEFAULT_RETRY_ON_429:
            logger.warning(f'[OpenAIClient] Got 429 status, {try_count = }, retry 1 more time if possible...')
            return await self._make_request(method, data, try_count + 1)

        if status == 401:
            raise OpenAIInvalidRequestError(f'Got response from OpenAI: {response}')
        return response

    async def _parse_completion_choices(self, response: OpenAICompletion) -> str:
        choices = response.choices
        if not choices:
            logger.warning('No choices from OpenAI, send nothing...')
            return self.DEFAULT_NO_COMPLETION_CHOICE_RESPONSE

        logger.debug('Choose first completion in %s & send.', response)
        return choices[0].text

    async def get_completions(self, text: str, max_tokens: int = 4000, temperature: float = 1.0) -> str:
        data = {
            'model': 'gpt-3.5-turbo-instruct',
            'prompt': text,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        response = await self._make_request(self.Method.COMPLETIONS, data)
        return await self._parse_completion_choices(OpenAICompletion(**response))

    async def parse_chat_choices(self, response: OpenAIChatChoices) -> str:
        choices = response.choices
        if not choices:
            logger.warning('No choices from OpenAI, send nothing...')
            return self.DEFAULT_NO_COMPLETION_CHOICE_RESPONSE

        logger.debug('Choose first completion in %s & send.', response)
        return choices[0].message.content

    async def get_chat_completions(self, messages: [ChatMessage], chat_bot_goal: str) -> str:
        """
        :param messages: previous messages + new message from a user.
        :param chat_bot_goal: e.g. You are a helpful assistant.
        """
        chat_bot_goal = ChatMessage(
            role='system',
            content=chat_bot_goal,
        )
        messages = ChatMessages(root=[chat_bot_goal] + messages)
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': json.loads(messages.json()),
            'n': 1,
        }
        response = await self._make_request(self.Method.CHAT_COMPLETIONS, data)
        return await self.parse_chat_choices(OpenAIChatChoices(**response))

    async def get_generated_image(self, text: str, model: str = 'dall-e-3') -> DallEResponse:
        assert model in ['dall-e-3', 'dall-e-2'], f'Model {model} is not supported.'
        data = {
            'model': model,
            'prompt': self.DEFAULT_IMAGE_PROMT_PREFIX + text,
            'n': 1,  # dall-e-3 only accepts 1
            'quality': 'standard',
            'size': '1024x1024',
        }

        response = await self._make_request(self.Method.IMAGE_GENERATION, data)
        try:
            url = response['data'][0]['url']
            revised_prompt = response['data'][0]['revised_prompt']
            return DallEResponse(url=url, revised_prompt=revised_prompt)
        except KeyError:
            logger.error(f'No url in response {response}, pass empty string.')
            return DallEResponse(url='', revised_prompt='', error=f'{response}.')
