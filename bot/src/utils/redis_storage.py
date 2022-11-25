"""To get Redis keys to model objs."""
from typing import Optional, List

from aioredis import Redis


class BotChatsStorage:
    # TODO: if new priority chat inserted how to sync.
    def __init__(self, bot_id: int, redis_engine: Redis, priority_chats: Optional[List[int]] = None):
        self.bot_id = bot_id
        self.priority_chats = set(priority_chats) if priority_chats else None
        self.redis_engine = redis_engine
        self._priority_chats_set_key = f'bot:{bot_id}:1priority'
        self._economy_chats_set_key = f'bot:{bot_id}:2priority'

    async def get_prioritised_chats(self) -> Optional[list[int]]:
        """Get prioritised chats that are in redis storage."""
        if not self.priority_chats:
            return

        fetched_chats = await self.redis_engine.smembers(self._priority_chats_set_key)
        if not fetched_chats:
            return
        return list(filter(lambda x: x in self.priority_chats, fetched_chats))

    async def get_economy_chats(self):
        return await self.redis_engine.smembers(self._economy_chats_set_key)

    async def set_chat(self, chat_id: int):
        if self.priority_chats and chat_id in self.priority_chats:
            return await self.redis_engine.sadd(self._priority_chats_set_key, chat_id)
        return await self.redis_engine.sadd(self._economy_chats_set_key, chat_id)

    async def rm_chat(self, chat_id: int):
        await self.redis_engine.srem(self._economy_chats_set_key, chat_id)
        await self.redis_engine.srem(self._priority_chats_set_key, chat_id)
