"""To get Redis keys to model objs."""
import logging
from dataclasses import dataclass
from typing import Optional, List

from redis.asyncio import Redis

from utils.crypto import Crypto
from utils.redis_scan_iterator import RedisScanIterAsyncIterator

logger = logging.getLogger(__name__)


class BotStorageABC:
    def __init__(self, bot_id: int, redis_engine: Redis, *args, **kwargs):
        self.bot_id = bot_id
        self.redis_engine = redis_engine


class BotChatsStorage(BotStorageABC):
    def __init__(
            self,
            bot_id: int,
            redis_engine: Redis,
            priority_chats: Optional[List[int]] = None,
    ):
        super().__init__(bot_id, redis_engine)
        self.priority_chats = set(priority_chats) if priority_chats else None
        self._economy_chats_set_key = f'bot:{self.bot_id}:2priority'

    async def get_chats(self) -> set[int]:
        return set(int(x) for x in await self.redis_engine.smembers(self._economy_chats_set_key))

    async def set_chat(self, chat_id: int):
        return await self.redis_engine.sadd(self._economy_chats_set_key, chat_id)

    async def rm_chat(self, chat_id: int):
        await self.redis_engine.srem(self._economy_chats_set_key, chat_id)


class BotChatMessagesCache(BotStorageABC):
    """
    # Scheme:
    message_id|{text,userId}|replay_to -> message_id|{text,userId}|replay_to -> ...
    message_id = chat_id + real_message-id.
    """

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

    def _get_key_text(self, chat_id: int, message_id: int) -> str:
        return self._get_storage_prefix() + f'{chat_id}:{message_id}:message'

    def _get_key_replay_to(self, chat_id: int, message_id: int) -> str:
        return self._get_storage_prefix() + f'{chat_id}:{message_id}:replay_to'

    def _get_key_sender(self, chat_id: int, message_id: int) -> str:
        return self._get_storage_prefix() + f'{chat_id}:{message_id}:sender'

    async def set_message(self, chat_id: int, message_id: int, message: MessageData):
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.set(self._get_key_text(chat_id, message_id), message.text, self.ttl)
            pipe = pipe.set(self._get_key_sender(chat_id, message_id), message.sender, self.ttl)
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

    async def get_all_chats_iterator(self, count: int = 100):
        return RedisScanIterAsyncIterator(
            redis=self.redis_engine, match=self._get_storage_prefix() + '*:message', count=count)

    @classmethod
    def to_chat_id_from_key(cls, key: str) -> Optional[int]:
        try:
            return int(key.split(':')[2])
        except Exception as e:
            logger.warning('[to_chat_id_from_key] Error: %s', e)
            return


class BotOpenAIContributorChatStorage(BotStorageABC):
    """Store mapping of username + chatId to token.

    It stores ciphered tokens.
    """

    def __init__(self, bot_id: int, redis_engine: Redis, crypto: Crypto, *args, **kwargs):
        super().__init__(bot_id, redis_engine, *args, **kwargs)
        self._crypto = crypto

    def _get_storage_prefix(self):
        return f'{self.bot_id}:BOAICCS:'

    def _get_key_token(self, user_id: int, chat_id: int) -> str:
        return f'{self._get_storage_prefix()}:{user_id}:{chat_id}:contributor_token'

    async def get(self, user_id: int, chat_id: int) -> Optional[str]:
        value = await self.redis_engine.get(self._get_key_token(user_id, chat_id))
        if not value:
            return
        return self._crypto.decipher_to_str(value)

    async def set(self, user_id: int, chat_id: int, token: str) -> Optional[str]:
        value = self._crypto.cipher_to_str(token)
        return await self.redis_engine.set(self._get_key_token(user_id, chat_id), value)

    async def delete(self, user_id: int, chat_id: int) -> Optional[str]:
        return await self.redis_engine.delete(self._get_key_token(user_id, chat_id))

    async def get_all_chats_iterator(self, count: int = 100):
        return RedisScanIterAsyncIterator(redis=self.redis_engine, match=self._get_storage_prefix() + '*', count=count)

    @classmethod
    def to_chat_id_from_key(cls, key: str) -> Optional[int]:
        try:
            return int(key.split(':')[-2])
        except Exception as e:
            logger.warning('[to_chat_id_from_key] Error: %s', e)
            return
