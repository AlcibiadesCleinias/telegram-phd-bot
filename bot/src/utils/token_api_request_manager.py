import logging
import random
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class MaxRotationException(Exception):
    pass


class NoWorkableTokens(Exception):
    pass


@dataclass
class TokenRequestResponse:
    json: any
    status: int
    failed_tokens: list[str]


class TokenApiManagerABC:
    def __init__(
            self,
            main_token: Optional[str],
            *args,
            **kwargs,
    ):
        self.main_token = main_token

    async def make_request(
            self,
            url,
            data,
            headers={},
            *args,
            **kwargs,
    ) -> TokenRequestResponse:
        raise NotImplementedError


class TokenApiRequestPureManager(TokenApiManagerABC):
    """It uses only 1 token."""
    async def make_request(
            self,
            url,
            data,
            headers={},
            *args,
            **kwargs,
    ) -> TokenRequestResponse:
        current_token = self.main_token
        headers['Authorization'] = f'Bearer {current_token}'

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url,
                json=data,
                headers=headers,
            ) as response:
                status = response.status
                logger.info('[TokenApiRequestManager] Send %s, on %s got status = %s', data, url, status)

                return TokenRequestResponse(
                    status=response.status,
                    json=await response.json(),
                    failed_tokens=[],
                )


class TokenApiRequestManager(TokenApiManagerABC):
    """It uses randomly main_token or one of the stored token.
    Stored tokens could be deleted when request failed.
    Main token could only be flagged and never used after.

    Note, the class is adopted to run in 1 process mode, since it uses shared thread storage.

    TODO: currently, it supports only bearer token auth.
    TODO: use external storage abstraction instead of only redis.
    """
    _token_to_external_key = {}  # Token to external storage key.
    _REDIS_PREFIX_KEY = 'TokenApiRequestManager:'
    DEFAULT_NEW_TOKEN_TTL = 3600 * 24 * 30

    def __init__(
        self,
        main_token: Optional[str],
        redis_storage: Redis,
        salt: str = 'salt:',
        max_tokens_to_load: int = 100,
        storage_reload_ttl: int = 500,
    ):
        """
        :param salt: do differ tokens in external storage from other ones.
        :param storage_reload_ttl: to solve multi processing sync.
        :param main_token: main token, e.g. from env.
        :param redis_storage:
        :param max_tokens_to_load: max tokens to load from storage (aka batch)
        """
        super().__init__(main_token, redis_storage, salt, max_tokens_to_load, storage_reload_ttl)
        self._main_token_failed = False

        self.current_token = self.main_token
        self.salt = salt
        self.external_storage = redis_storage
        self.external_storage_reload_ttl = storage_reload_ttl
        self.max_tokens_to_load = max_tokens_to_load

        self._last_storage_reload = 0.0
        self._token_to_external_key[self.main_token] = self._get_external_storage_key(self.main_token)

    def _get_external_storage_key(self, token: str):
        return self._REDIS_PREFIX_KEY + self.salt + token

    async def add_token(self, token: str, ttl: int = DEFAULT_NEW_TOKEN_TTL):
        """
        :param token:
        :param ttl: ttl for the token
        """
        key = self._get_external_storage_key(token)
        self._token_to_external_key[token] = key
        await self.external_storage.set(key, token, ttl)

    async def remove_token(self, token: str):
        logger.info(f'[TokenApiRequestManager] Remove {token = }.')
        if token == self.main_token:
            self._main_token_failed = True

        if token in self._token_to_external_key:
            self._token_to_external_key.pop(token)
            try:
                key = self._get_external_storage_key(token)
                await self.external_storage.delete(key)
            except Exception:
                logger.warning('[TokenApiRequestManager] Could not delete from external, already not exists? pass...')

    async def reload_storage(self):
        self._last_storage_reload = time.time()
        if not self._main_token_failed:
            self._token_to_external_key[self.main_token] = self._get_external_storage_key(self.main_token)

        # TODO: add redis lock.
        logger.info('[TokenApiRequestManager] Load keys by mask from external storage...')
        loaded_token_keys = await self.external_storage.scan(
            match=f'{self._REDIS_PREFIX_KEY}*', count=self.max_tokens_to_load,
        )
        if not loaded_token_keys or len(loaded_token_keys[1]) == 0:
            return
        loaded_token_keys = loaded_token_keys[1]

        logger.info('[TokenApiRequestManager] Load tokens by keys from external storage...')
        async with self.external_storage.pipeline(transaction=True) as pipe:
            for k in loaded_token_keys:
                pipe = pipe.get(k)
            loaded_tokens = await pipe.execute()

        if not loaded_tokens:
            return
        self._token_to_external_key = {token: self._get_external_storage_key(token) for token in loaded_tokens}

    async def get_current_token(self) -> str:
        if (
                not self._token_to_external_key or time.time() >
                self._last_storage_reload + self.external_storage_reload_ttl
        ):
            await self.reload_storage()

        if len(self._token_to_external_key) == 0:
            raise NoWorkableTokens

        current_choice = random.choice(list(self._token_to_external_key.keys()))
        return current_choice

    async def make_request(
            self,
            url,
            data,
            headers={},
            rotate_statuses={},
            removed_tokens=[],
            max_rotations=100,
    ) -> TokenRequestResponse:
        """TODO: what if some tokens removed but with one of them error happened.
         user should be notified about removed/deleted ones anyway.
         """
        current_token = await self.get_current_token()
        headers['Authorization'] = f'Bearer {current_token}'
        if max_rotations == 0:
            raise MaxRotationException

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=url,
                json=data,
                headers=headers,
            ) as response:
                status = response.status
                logger.info('[TokenApiRequestManager] Send %s, on %s got status = %s', data, url, status)
                if status in rotate_statuses:
                    logger.info(
                        f' [TokenApiRequestManager]Rotate token before the new request '
                        f'& remove token from the cache {current_token}...'
                    )
                    await self.remove_token(current_token)
                    removed_tokens.append(current_token)
                    return await self.make_request(
                        url, data, rotate_statuses, headers, removed_tokens, max_rotations - 1
                    )

                return TokenRequestResponse(
                    status=response.status,
                    json=await response.json(),
                    failed_tokens=removed_tokens,
                )
