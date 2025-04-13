import json
import logging
from enum import Enum
from typing import Optional

from utils.token_api_request_manager import TokenApiManagerABC, TokenApiRequestPureManager
from clients.perplexity.scheme import PerplexityChatChoicesOut, PerplexityChatMessageIn, PerplexityChatMessagesIn, PerplexityRole

logger = logging.getLogger(__name__)

# Some models to list:
# - 'llama-3.1-sonar-small-128k-online'
# - TODO: add support for 'sonar-reasoning-pro'
# - 'sonar-pro'


class PerplexityClient:
    DEFAULT_NO_COMPLETION_CHOICE_RESPONSE = 'A?'
    # TODO: should be based on experience with Perplexity API.
    DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES = {401}
    DEFAULT_FORCE_MAIN_TOKEN_STATUSES = {400}
    DEFAULT_RETRY_ON_429 = 1  # Thus, totally 2 times.

    DEFAULT_CHAT_BOT_ROLE = PerplexityRole.ASSISTANT.value

    class Method(Enum):
        CHAT_COMPLETIONS = 'chat/completions'

    def __init__(
        self,
        token: Optional[str] = None,
        token_api_request_manager: Optional[TokenApiManagerABC] = None,
        openai_model: str = 'llama-3.1-sonar-small-128k-online',
        endpoint: str = 'https://api.perplexity.ai/',
    ):
        if not token and not token_api_request_manager:
            raise Exception('[PerplexityClient] Rather token or openai_token_api_request_manager should be defined.')
        if not token_api_request_manager:
            self.token_api_request_manager = TokenApiRequestPureManager(token)
        else:
            self.token_api_request_manager = token_api_request_manager

        self.endpoint = endpoint
        self.openai_model = openai_model

    async def _make_request(self, method: Method, data: dict, try_count: int = 0):
        url = self.endpoint + method.value
        api_manager_response = await self.token_api_request_manager.make_request(
            url=url, data=data, rotate_statuses=self.DEFAULT_TOKEN_TO_BE_ROTATED_STATUSES,
            force_main_token_statuses=self.DEFAULT_FORCE_MAIN_TOKEN_STATUSES,
        )
        response = api_manager_response.json
        status = api_manager_response.status
        logger.debug('[%s] Got response %s with status %s', self.__class__.__name__, response, status)

        # TODO: Handle different statuses and raise errors or make retries (should be based on experience).

        return response

    async def _parse_chat_choices(self, response: PerplexityChatChoicesOut) -> str:
        choices = response.choices
        if not choices:
            logger.warning('[%s] No choices from API, send nothing...', self.__class__.__name__)
            return self.DEFAULT_NO_COMPLETION_CHOICE_RESPONSE

        logger.debug('[%s] Choose first completion in %s & send.', self.__class__.__name__, response)
        return choices[0].message.content

    async def get_chat_completions(self, messages: list[PerplexityChatMessageIn], chat_bot_goal: str) -> tuple[str, list[str]]:
        """
        Returns response text and citations list.

        :param messages: previous messages + new message from a user.
        :param chat_bot_goal: e.g. You are a helpful assistant.
        """
        chat_bot_goal = PerplexityChatMessageIn(
            role=PerplexityRole.SYSTEM.value,
            content=chat_bot_goal,
        )
        messages = PerplexityChatMessagesIn(root=[chat_bot_goal] + messages)
        data = {
            'model': self.openai_model,
            'messages': json.loads(messages.json()),
            
            # TODO: use settings from redis, customisable.
            # "max_tokens": "Optional",
            # "temperature": 0.2,
            # "top_p": 0.9,
            # "search_domain_filter": [
            #     "perplexity.ai"
            # ],
            "return_images": False,
            # "search_recency_filter": "month",
            # "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        response = await self._make_request(self.Method.CHAT_COMPLETIONS, data)
        try:
            perplexity_response = PerplexityChatChoicesOut(**response)
        except Exception as e:
            logger.error('[%s] Error parsing response %s', self.__class__.__name__, response)
            raise e
        response_text = await self._parse_chat_choices(perplexity_response)
        return response_text, perplexity_response.citations

