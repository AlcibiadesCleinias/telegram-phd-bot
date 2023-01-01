"""To get Redis keys to model objs."""
import logging
from typing import Optional, List

from aioredis import Redis

logger = logging.getLogger(__name__)


class BotChatsStorage:
    def __init__(
            self,
            bot_id: int,
            redis_engine: Redis,
            priority_chats: Optional[List[int]] = None,
    ):
        self.bot_id = bot_id
        self.priority_chats = set(priority_chats) if priority_chats else None
        self.redis_engine = redis_engine
        self._economy_chats_set_key = f'bot:{bot_id}:2priority'

    async def get_chats(self) -> set[int]:
        return set(int(x) for x in await self.redis_engine.smembers(self._economy_chats_set_key))

    async def set_chat(self, chat_id: int):
        return await self.redis_engine.sadd(self._economy_chats_set_key, chat_id)

    async def rm_chat(self, chat_id: int):
        await self.redis_engine.srem(self._economy_chats_set_key, chat_id)


class BotChatMessagesCache:

    def __init__(
            self,
            bot_id: int,
            redis_engine: Redis,
            ttl: int = 60 * 10,
    ):
        self.bot_id = bot_id
        self.redis_engine = redis_engine
        self.ttl = ttl

    @staticmethod
    def _get_key_text(chat_id: int, message_id: int) -> str:
        return f'message:{chat_id}{message_id}'

    @staticmethod
    def _get_key_replay_to(chat_id: int, message_id: int) -> str:
        return f'replay_to:{chat_id}{message_id}'

    async def set_message(self, chat_id: int, message_id: int, text: str, replay_to: Optional[int]):
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.set(BotChatMessagesCache._get_key_text(chat_id, message_id), text, self.ttl)
            if replay_to is not None:
                pipe = pipe.set(BotChatMessagesCache._get_key_replay_to(chat_id, message_id), replay_to)
            return await pipe.execute()

    async def get_text(self, chat_id: int, message_id: int) -> Optional[str]:
        return await self.redis_engine.get(BotChatMessagesCache._get_key_text(chat_id, message_id))

    async def get_replay_to(self, chat_id: int, message_id: int) -> Optional[int]:
        res = await self.redis_engine.get(BotChatMessagesCache._get_key_replay_to(chat_id, message_id))
        return int(res) if res else None
