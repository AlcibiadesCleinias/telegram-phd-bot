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
