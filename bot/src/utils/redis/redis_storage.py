"""To get Redis keys to model objs."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from redis.asyncio import Redis

from utils.crypto import Crypto
from utils.generators import batch
from utils.redis.redis_scan_iterator import RedisScanIterAsyncIterator
from utils.time import now_utc

logger = logging.getLogger(__name__)


class BotChatsStorageABC(ABC):
    CHAT_ID_POSITION_IN_KEY = 2

    def __init__(self, bot_id: int, redis_engine: Redis, *args, **kwargs):
        self.bot_id = bot_id
        self.redis_engine = redis_engine

    @abstractmethod
    async def get_all_chats_iterator(self) -> RedisScanIterAsyncIterator:
        pass

    @classmethod
    def to_chat_id_from_key(cls, key: str) -> Optional[int]:
        try:
            return int(key.split(':')[cls.CHAT_ID_POSITION_IN_KEY])
        except Exception as e:
            logger.warning(f'[{cls.__name__}.to_chat_id_from_key] Error: %s', e)
            return


class BotChatsStorage(BotChatsStorageABC):
    """To store all chats ever used by the bot."""

    def __init__(
            self,
            bot_id: int,
            redis_engine: Redis,
    ):
        super().__init__(bot_id, redis_engine)

    def _get_storage_prefix(self):
        return f'{self.bot_id}:BChatsS:'

    def _get_key(self, chat_id: int) -> str:
        return self._get_storage_prefix() + str(chat_id)

    async def set_chat(self, chat_id: int):
        return await self.redis_engine.set(self._get_key(chat_id), chat_id)

    async def rm_chat(self, chat_id: int):
        await self.redis_engine.delete(self._get_key(chat_id))

    async def get_all_chats_iterator(self):
        return RedisScanIterAsyncIterator(
            redis=self.redis_engine, match=self._get_storage_prefix() + '*')


class BotChatMessagesCache(BotChatsStorageABC):
    """
    # Scheme:
    message_id|{text,userId}|replay_to -> message_id|{text,userId}|replay_to -> ...
    message_id = chat_id + real_message-id.
    """
    TTL_NOT_EXIST_CONSTS = [-1, -2]

    @dataclass
    class MessageData:
        replay_to: Optional[int]
        text: str
        sender: int

    def __init__(
            self,
            bot_id: int,
            redis_engine: Redis,
            ttl: int = 60 * 10,
    ):
        super().__init__(bot_id, redis_engine)
        self.ttl = ttl

    def _get_storage_prefix(self):
        return f'{self.bot_id}:BCMC:'

    def _get_chat_storage_prefix(self, chat_id: int):
        return f'{self._get_storage_prefix()}{chat_id}:'

    def _get_key_text(self, chat_id: int, message_id: int) -> str:
        return self._get_chat_storage_prefix(chat_id) + f'{message_id}:message'

    def _get_key_replay_to(self, chat_id: int, message_id: int) -> str:
        return self._get_chat_storage_prefix(chat_id) + f'{message_id}:replay_to'

    def _get_key_updated_chat_ttl(self, chat_id: int) -> str:
        return self._get_chat_storage_prefix(chat_id) + f'{chat_id}:updated_chat_ttl'

    def _get_key_sender(self, chat_id: int, message_id: int) -> str:
        return self._get_chat_storage_prefix(chat_id) + f'{message_id}:sender'

    # TODO: could be optimised: use json.dumps for messages.
    async def set_messages(self, chat_ids: list[int], message_ids: list[int], messages: list[MessageData]):
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            now = now_utc().timestamp()
            for chat_id, message_id, message in zip(chat_ids, message_ids, messages):
                pipe = pipe.set(self._get_key_text(chat_id, message_id), message.text, self.ttl)
                pipe = pipe.set(self._get_key_sender(chat_id, message_id), message.sender, self.ttl)
                pipe = pipe.set(self._get_key_updated_chat_ttl(chat_id), f'{now + self.ttl}', self.ttl)
                if message.replay_to is not None:
                    pipe = pipe.set(self._get_key_replay_to(chat_id, message_id), message.replay_to)
            return await pipe.execute()

    async def get_message(self, chat_id, message_id: int) -> Optional[MessageData]:
        logger.info(f'[BotChatMessagesCache] Getting message for {chat_id = }, {message_id = }...')
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.get(self._get_key_text(chat_id, message_id))
            pipe = pipe.get(self._get_key_sender(chat_id, message_id))
            pipe = pipe.get(self._get_key_replay_to(chat_id, message_id))
            executedPipe = await pipe.execute()

        logger.debug(f'Executed pipe, got {executedPipe}')
        if len(executedPipe) == 0:
            return None
        text = executedPipe.pop(0)
        sender = executedPipe.pop(0)
        replay_to = executedPipe.pop(0) if executedPipe else None
        return BotChatMessagesCache.MessageData(replay_to=replay_to, text=text, sender=sender)

    async def get_text(self, chat_id: int, message_id: int) -> Optional[str]:
        return await self.redis_engine.get(self._get_key_text(chat_id, message_id))

    async def get_replay_to(self, chat_id: int, message_id: int) -> Optional[int]:
        res = await self.redis_engine.get(self._get_key_replay_to(chat_id, message_id))
        return int(res) if res else None

    async def get_all_chats_iterator(self):
        """Fetch all cached chats (cached in terms of ttl of the class).
        It goes through _get_key_updated_chat_ttl keys patters as via keys should be used to store only cached chats.
        TODO: check that ttl for the keys is not in [-1, -2] E.g. Redis rm ttl on restart.
         Thus, there should be service task somewhere.
        """
        return RedisScanIterAsyncIterator(
            redis=self.redis_engine, match=self._get_storage_prefix() + '*:updated_chat_ttl')

    async def has_any_cached_messages(self, chat_ids: list[int]) -> list[bool]:
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            for chat_id in chat_ids:
                _key = self._get_key_updated_chat_ttl(chat_id)
                pipe = pipe.get(_key)
                pipe = pipe.ttl(_key)
            executed_pipe = await pipe.execute()
            return [
                bool(chat_ttl_end and ttl_response not in self.TTL_NOT_EXIST_CONSTS)
                for chat_ttl_end, ttl_response in batch(executed_pipe, 2)
            ]


class BotAIContributorChatStorage(BotChatsStorageABC):
    """Store mapping of username + chatId to token. Thus,  you can:
    - easily check if user id supplied token for the chat.
    - get all saved tokens as well with mask of the storage.

    Note, it stores ciphered tokens.
    """
    CHAT_ID_POSITION_IN_KEY = -2

    @dataclass
    class ContributorTokensOut:
        openai_token: Optional[str]
        perplexity_token: Optional[str]

    def __init__(self, bot_id: int, redis_engine: Redis, crypto: Crypto, *args, **kwargs):
        super().__init__(bot_id, redis_engine, *args, **kwargs)
        self._crypto = crypto

    def _get_storage_prefix(self):
        return f'{self.bot_id}:BAICCS:'  # Bot AI Contributor Chat Storage

    def _get_key_openai_token(self, user_id: int, chat_id: int) -> str:
        return f'{self._get_storage_prefix()}:{user_id}:{chat_id}:contribute_openai'
    
    def _get_key_perplexity_token(self, user_id: int, chat_id: int) -> str:
        return f'{self._get_storage_prefix()}:{user_id}:{chat_id}:contribute_perplexity'

    async def get(self, user_id: int, chat_id: int) -> ContributorTokensOut:
        """Get both OpenAI and Perplexity tokens for a user in a chat."""
        openai_value = await self.redis_engine.get(self._get_key_openai_token(user_id, chat_id))
        perplexity_value = await self.redis_engine.get(self._get_key_perplexity_token(user_id, chat_id))
        return self.ContributorTokensOut(
            openai_token=self._crypto.decipher_to_str(openai_value) if openai_value else None,
            perplexity_token=self._crypto.decipher_to_str(perplexity_value) if perplexity_value else None,
        )

    async def set_openai_token(self, user_id: int, chat_id: int, token: str) -> Optional[str]:
        """Store OpenAI token for a user in a chat."""
        token_ciphered = self._crypto.cipher_to_str(token)
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.set(self._get_key_openai_token(user_id, chat_id), token_ciphered)
            return await pipe.execute()

    async def set_perplexity_token(self, user_id: int, chat_id: int, token: str) -> Optional[str]:
        """Store Perplexity token for a user in a chat."""
        token_ciphered = self._crypto.cipher_to_str(token)
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.set(self._get_key_perplexity_token(user_id, chat_id), token_ciphered)
            return await pipe.execute()

    async def delete_openai_token(self, user_id: int, chat_id: int) -> Optional[str]:
        """Delete OpenAI token for a user in a chat."""
        return await self.redis_engine.delete(self._get_key_openai_token(user_id, chat_id))

    async def delete_perplexity_token(self, user_id: int, chat_id: int) -> Optional[str]:
        """Delete Perplexity token for a user in a chat."""
        return await self.redis_engine.delete(self._get_key_perplexity_token(user_id, chat_id))

    async def get_all_chats_iterator(self):
        """Get iterator over all chats that have either OpenAI or Perplexity tokens."""
        return RedisScanIterAsyncIterator(redis=self.redis_engine, match=self._get_storage_prefix() + '*')



async def get_unique_chat_ids_from_storage(
        bot_chats_storage_object: BotChatsStorageABC,
) -> set:
    """
    :param bot_chats_storage_object:  inited interator of BotChatsStorageABC.get_all_chats_iterator.
    :return: all unique chat_ids.
    """
    unique_chat_ids = set()
    async for chat_keys in await bot_chats_storage_object.get_all_chats_iterator():
        logger.info(f'[get_unique_chat_ids_from_storage] Get for this batch {chat_keys = }')
        # Convert all keys to chat ids.
        fetched_chat_ids = [bot_chats_storage_object.to_chat_id_from_key(x) for x in chat_keys if x is not None]
        unique_chat_ids.update(fetched_chat_ids)
        logger.info(f'[get_unique_chat_ids_from_storage] Convert to {fetched_chat_ids =}')
    return unique_chat_ids
