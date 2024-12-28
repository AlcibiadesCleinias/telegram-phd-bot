from typing import Optional
from redis.asyncio import Redis
from bot.consts import AIDiscussionMode


class BotChatAIDiscussionModeStorage:
    def __init__(self, bot_id: int, redis_engine: Redis):
        self.bot_id = bot_id
        self.redis_engine = redis_engine

    def _get_key_discussion_mode(self, chat_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:discussion_mode'
    
    def _get_key_discussion_mode_by_contributor(self, chat_id: int, user_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:{user_id}:discussion_mode'
    
    def _get_key_is_mention_only_mode(self, chat_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:is_mention_only_mode'
    
    def _get_key_is_mention_only_mode_by_contributor(self, chat_id: int, user_id: int) -> str:
        return f'{self.bot_id}:{self.__class__.__name__}:{chat_id}:{user_id}:is_mention_only_mode'
    
    async def set_discussion_mode(self, chat_id: int, discussion_mode: AIDiscussionMode):
        await self.redis_engine.set(self._get_key_discussion_mode(chat_id), discussion_mode.value)

    async def get_discussion_mode(self, chat_id: int) -> Optional[AIDiscussionMode]:
        value = await self.redis_engine.get(self._get_key_discussion_mode(chat_id))
        return AIDiscussionMode(int(value)) if value else None

    async def set_discussion_mode_by_contributor(self, chat_id: int, user_id: int, discussion_mode: AIDiscussionMode):
        await self.redis_engine.set(self._get_key_discussion_mode_by_contributor(chat_id, user_id), discussion_mode.value)

    async def get_discussion_mode_by_contributor(self, chat_id: int, user_id: int) -> Optional[AIDiscussionMode]:
        value = await self.redis_engine.get(self._get_key_discussion_mode_by_contributor(chat_id, user_id))
        return AIDiscussionMode(int(value)) if value else None
    
    async def set_is_mention_only_mode(self, chat_id: int, is_mention_only_mode: bool):
        await self.redis_engine.set(self._get_key_is_mention_only_mode(chat_id), int(is_mention_only_mode))

    async def get_is_mention_only_mode_by_contributor(self, chat_id: int, user_id: int) -> bool:
        value = await self.redis_engine.get(self._get_key_is_mention_only_mode_by_contributor(chat_id, user_id))
        return bool(int(value)) if value is not None else False
    
    async def get_is_mention_only_mode(self, chat_id: int) -> bool:
        value = await self.redis_engine.get(self._get_key_is_mention_only_mode(chat_id))
        return bool(int(value)) if value is not None else False
    
    async def set_is_mention_only_mode_by_contributor(self, chat_id: int, user_id: int, is_mention_only_mode: bool):
        await self.redis_engine.set(self._get_key_is_mention_only_mode_by_contributor(chat_id, user_id), int(is_mention_only_mode))