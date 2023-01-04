import logging
from enum import Enum

import aiohttp

from clients.openai.scheme import OpenAICompletion

logger = logging.getLogger(__name__)


class ExceptionMaxTokenExceeded(Exception):
    pass


class OpenAIClient:
    COMPLETION_MAX_LENGTH = 4097
    ERROR_MAX_TOKEN_MESSAGE = 'This model\'s maximum context'

    class Method(Enum):
        COMPLETIONS = 'completions'

    def __init__(self, token: str, endpoint: str = 'https://api.openai.com/v1/'):
        self.token = token
        self.endpoint = endpoint
        self._auth_header = {'Authorization': f'Bearer {self.token}'}

    async def _make_request(self, method: Method, data: dict):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self.endpoint + method.value,
                json=data,
                headers=self._auth_header,
            ) as response:
                status = response.status
                logger.info('Send %s, got status %s', data, status)
                response = await response.json()

                if status == 400 and response.get('error', {}).get('message', '').startswith(
                        self.ERROR_MAX_TOKEN_MESSAGE
                ):
                    logger.warning('Got invalid_request_error from openai, raise related exception.')
                    raise ExceptionMaxTokenExceeded

                return response

    async def get_completions(self, text: str, max_tokens: int = 4000, temperature: float = 1.0) -> OpenAICompletion:
        data = {
            'model': 'text-davinci-003',
            'prompt': text,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        response = await self._make_request(self.Method.COMPLETIONS, data)
        logger.info('Got %s', response)
        return OpenAICompletion(**response)
