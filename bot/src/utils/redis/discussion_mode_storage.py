from enum import Enum
from redis.asyncio import Redis



class BotChatDiscussionModeStorage:
    def __init__(self, bot_id: int, redis_engine: Redis):
        self.bot_id = bot_id
        self.redis_engine = redis_engine

    def _get_key(self, chat_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:discussion_mode'
    
    def _get_key_discussion_mode_by_contributor(self, chat_id: int, user_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:{user_id}:discussion_mode'
    
    async def set_discussion_mode(self, chat_id: int, discussion_mode: int):
        await self.redis_engine.set(self._get_key_discussion_mode(chat_id), discussion_mode)

    async def get_discussion_mode(self, chat_id: int) -> int:
        return await self.redis_engine.get(self._get_key_discussion_mode(chat_id))

    async def set_discussion_mode_by_contributor(self, chat_id: int, user_id: int, discussion_mode: int):
        await self.redis_engine.set(self._get_key_discussion_mode_by_contributor(chat_id, user_id), discussion_mode)

    async def get_discussion_mode_by_contributor(self, chat_id: int, user_id: int) -> int:
        return await self.redis_engine.get(self._get_key_discussion_mode_by_contributor(chat_id, user_id))
