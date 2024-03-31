import json
import random
import time
from dataclasses import dataclass
import logging
from typing import Optional

import aiohttp
from redis.asyncio import Redis

from utils.crypto import Crypto
from utils.redis.redis_scan_iterator import get_first_n_keys

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
                _json = await response.json()
                logger.info('[TokenApiRequestPureManager] Send %s, on %s got status = %s, json = %s',
                            data, url, status, _json)

                return TokenRequestResponse(
                    status=status,
                    json=_json,
                    failed_tokens=[],
                )


class TokenApiRequestManager(TokenApiManagerABC):
    """It uses randomly main_token or one of the stored tokens (main token could not be deleted).
    Stored tokens could be deleted when request failed.
    Main token could only be flagged and never used after (instead of deletion).

    It stores ciphered tokens if Crypto is provided.

    Note, the class is adopted to run in 1 process mode, since it uses shared thread storage.
    Note, that this manager and openai_contributor_token class storage uses different storage layers.
     When this class may remove the token from its scope, but in openai_contributor_token the token may still persist.

    TODO: currently, it supports only bearer token auth.
    TODO: use external storage abstraction instead of only redis.

    # Use-case
    ```
        redis = aioredis.from_url(f'redis://localhost:6379', db=1, decode_responses=True)
        main_token = "foo"
        url = 'https://api.openai.com/v1/completions'
        manager = TokenApiRequestManager(main_token, redis)
        rotate_statuses = set([401, 429])
        await manager.add_token("foo1")
        await manager.add_token("foo2")
        res = await manager.make_request(url, {'data': 'foo'}, rotate_statuses=rotate_statuses)
    ```
    """
    _token_to_external_key = {}  # Token to external storage key.
    # To separate key from others.
    _REDIS_PREFIX_KEY = 'TokenApiRequestManager:'
    DEFAULT_NEW_TOKEN_TTL = 3600 * 24 * 30 * 2  # 2 months.

    def __init__(
        self,
        main_token: Optional[str],
        redis_storage: Redis,
        crypto_engine: Optional[Crypto] = None,
        salt: str = 'TokenApiRequestManager',
        max_tokens_to_load: int = 100,
        storage_reload_ttl: int = 500,
    ):
        """
        :param salt: do differ tokens in external storage from other ones and differ keys from other ones.
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
        self._token_to_external_key[self.main_token] = 'foo'  # Main token is not stored in external storage.

        self._crypto_engine = crypto_engine

    def _get_external_storage_key_prefix(self):
        return self._REDIS_PREFIX_KEY + f'{self.salt}:'

    async def add_token(self, token: str, key_salt: str, ttl: int = DEFAULT_NEW_TOKEN_TTL):
        """
        :param token: token to store for use of this manager.
        :param ttl: ttl for the token
        """
        key = self._get_external_storage_key_prefix() + f'{key_salt}'
        self._token_to_external_key[token] = key
        to_store = self._crypto_engine.cipher_to_str(token) if self._crypto_engine else token
        await self.external_storage.set(key, to_store, ttl)

    async def remove_token(self, token: str):
        logger.info(f'[TokenApiRequestManager] Remove {token = }.')
        if token == self.main_token:
            self._main_token_failed = True
            self._token_to_external_key.pop(self.main_token)

        if token in self._token_to_external_key:
            external_key = self._token_to_external_key.pop(token)
            try:
                await self.external_storage.delete(external_key)
            except Exception:
                logger.warning(
                    '[TokenApiRequestManager] Could not delete from external, already not exists? nvm&pass...')

    async def reload_storage(self):
        self._last_storage_reload = time.time()

        # TODO: add redis lock on get keys and get values with pipe.
        logger.info('[TokenApiRequestManager] Load keys by mask from external storage...')
        # It loads only 1 batch, and there is no need to go till the end since bad tokens should be deleted after,
        #  and new reload will take a place.
        loaded_token_keys = await get_first_n_keys(
            f'{self._get_external_storage_key_prefix()}*',
            self.max_tokens_to_load,
            self.external_storage,
        )
        if not loaded_token_keys:
            logger.info('[TokenApiRequestManager] No loaded_token_keys from storage. Hopefully, main token will work.')
            return

        logger.info('[TokenApiRequestManager] Load tokens by keys from external storage...')
        async with self.external_storage.pipeline(transaction=True) as pipe:
            for k in loaded_token_keys:
                pipe = pipe.get(k)
            loaded_tokens = await pipe.execute()
        if not loaded_tokens:
            logger.info('[TokenApiRequestManager] tried to load tokens, but empty.')
            return

        assert len(loaded_token_keys) == len(loaded_tokens), 'Impossible.'

        loaded_tokens = [self._crypto_engine.decipher_to_str(value) if value else None for value in loaded_tokens]
        to_update_with = {token: loaded_token_keys[idx] for idx, token in enumerate(loaded_tokens) if token is not None}
        self._token_to_external_key.update(to_update_with)

    async def get_current_token(self) -> str:
        # Check if no tokens left or if time & token capacity is not full.
        if (
                not self._token_to_external_key or (
                time.time() > self._last_storage_reload + self.external_storage_reload_ttl
                and len(self._token_to_external_key) < self.max_tokens_to_load
                )
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
            force_main_token_statuses={},
            force_main_token=False,
    ) -> TokenRequestResponse:
        """TODO: what if some tokens removed but with one of them error happened.
         user should be notified about removed/deleted ones anyway.
         """
        current_token = await self.get_current_token() if not force_main_token else self.main_token
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
                _text = await response.text()
                logger.info('[TokenApiRequestManager] Send %s, on %s got status = %s, text = %s',
                            data, url, status, _text)
                if status in rotate_statuses:
                    logger.info(
                        f' [TokenApiRequestManager] Rotate token before the new request '
                        f'& remove token from the manager cache {current_token}...'
                    )
                    # TODO: possibly notify admins about deletion.
                    await self.remove_token(
                        current_token,
                    )
                    removed_tokens.append(current_token)
                    return await self.make_request(
                        url=url,
                        data=data,
                        headers=headers,
                        rotate_statuses=rotate_statuses,
                        removed_tokens=removed_tokens,
                        max_rotations=max_rotations - 1,
                        force_main_token_statuses=force_main_token_statuses,
                    )

                if status in force_main_token_statuses:
                    logger.info(
                        '[TokenApiRequestManager] Use main token before the new request. Do anything with the '
                        'current token.'
                    )
                    return await self.make_request(
                        url=url,
                        data=data,
                        headers=headers,
                        rotate_statuses=rotate_statuses,
                        removed_tokens=removed_tokens,
                        max_rotations=max_rotations - 1,
                        force_main_token_statuses=force_main_token_statuses,
                        force_main_token=True,
                    )

                return TokenRequestResponse(
                    status=response.status,
                    json=json.loads(_text),
                    failed_tokens=removed_tokens,
                )
