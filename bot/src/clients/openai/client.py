import logging
from enum import Enum

import aiohttp

from clients.openai.scheme import OpenAICompletion

logger = logging.getLogger(__name__)


class OpenAIClient:

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
                logger.info('Send %s, got %s', data, response)
                # TODO: catch 401, etc
                return await response.json()

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
