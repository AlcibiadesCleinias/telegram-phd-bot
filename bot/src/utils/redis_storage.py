"""To get Redis keys to model objs."""
import logging
from dataclasses import dataclass
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
        self.bot_id = bot_id
        self.redis_engine = redis_engine
        self.ttl = ttl

    @staticmethod
    def _get_key_text(chat_id: int, message_id: int) -> str:
        return f'{chat_id}:{message_id}:message'

    @staticmethod
    def _get_key_replay_to(chat_id: int, message_id: int) -> str:
        return f'{chat_id}:{message_id}:replay_to'

    @staticmethod
    def _get_key_sender(chat_id: int, message_id: int) -> str:
        return f'{chat_id}:{message_id}:sender'

    async def set_message(self, chat_id: int, message_id: int, message: MessageData):
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.set(BotChatMessagesCache._get_key_text(chat_id, message_id), message.text, self.ttl)
            pipe = pipe.set(BotChatMessagesCache._get_key_sender(chat_id, message_id), message.sender, self.ttl)
            if message.replay_to is not None:
                pipe = pipe.set(BotChatMessagesCache._get_key_replay_to(chat_id, message_id), message.replay_to)
            return await pipe.execute()

    async def get_message(self, chat_id, message_id: int) -> MessageData:
        logger.info(f'Getting message for {chat_id = }, {message_id = }...')
        async with self.redis_engine.pipeline(transaction=True) as pipe:
            pipe = pipe.get(BotChatMessagesCache._get_key_text(chat_id, message_id))
            pipe = pipe.get(BotChatMessagesCache._get_key_sender(chat_id, message_id))
            pipe = pipe.get(BotChatMessagesCache._get_key_replay_to(chat_id, message_id))
            executedPipe = await pipe.execute()

        logger.debug(f'Executted, got {executedPipe}')
        text = executedPipe.pop(0)
        sender = executedPipe.pop(0)
        replay_to = executedPipe.pop(0) if executedPipe else None
        return BotChatMessagesCache.MessageData(replay_to=replay_to, text=text, sender=sender)

    async def get_text(self, chat_id: int, message_id: int) -> Optional[str]:
        return await self.redis_engine.get(BotChatMessagesCache._get_key_text(chat_id, message_id))

    async def get_replay_to(self, chat_id: int, message_id: int) -> Optional[int]:
        res = await self.redis_engine.get(BotChatMessagesCache._get_key_replay_to(chat_id, message_id))
        return int(res) if res else None
