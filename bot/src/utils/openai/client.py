import json
import logging
from enum import Enum

from utils.openai.scheme import OpenAICompletion, ChatMessage, ChatMessages, OpenAIChatChoices
from utils.token_api_request_manager import TokenApiRequestManager

logger = logging.getLogger(__name__)


class ExceptionMaxTokenExceeded(Exception):
    pass


class OpenAIClient:
    COMPLETION_MAX_LENGTH = 4097
    ERROR_MAX_TOKEN_MESSAGE = 'This model\'s maximum context'
    DEFAULT_NO_COMPLETION_CHOICE_RESPONSE = 'A?'
    DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES = {401, 429}

    DEFAULT_CHAT_BOT_ROLE = 'assistant'

    class Method(Enum):
        COMPLETIONS = 'completions'
        CHAT_COMPLETIONS = 'chat/completions'

    def __init__(
            self,
            token: str,
            token_api_request_manager: TokenApiRequestManager,
            endpoint: str = 'https://api.openai.com/v1/',
    ):
        self.token = token
        self.endpoint = endpoint
        self.token_api_request_manager = token_api_request_manager

    async def _make_request(self, method: Method, data: dict):
        url = self.endpoint + method.value
        api_manager_response = await self.token_api_request_manager.make_request(
            url, data, rotate_statuses=self.DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES,
        )
        response = api_manager_response.json
        status = api_manager_response.status

        if status == 400 and response.get('error', {}).get('message', '').startswith(
                self.ERROR_MAX_TOKEN_MESSAGE):
            logger.warning('Got invalid_request_error from openai, raise related exception.')
            raise ExceptionMaxTokenExceeded
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
            'model': 'text-davinci-003',
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
        messages = ChatMessages(__root__=[chat_bot_goal] + messages)
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': json.loads(messages.json()),
            'n': 1,
        }
        response = await self._make_request(self.Method.CHAT_COMPLETIONS, data)
        return await self.parse_chat_choices(OpenAIChatChoices(**response))
