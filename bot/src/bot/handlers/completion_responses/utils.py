import logging

from aiogram import types
from utils.redis.redis_storage import BotChatMessagesCache

logger = logging.getLogger(__name__)


async def _get_raw_dialog_messages(
        bot_chat_messages_cache: BotChatMessagesCache, message_obj: types.Message, depth: int = 2) -> list[BotChatMessagesCache.MessageData]:
    """Fetches raw dialog messages from cache.
    Returns list of cached message objects.
    """
    logger.info('[_get_raw_dialog_messages] Try to fetch previous messages...')
    chat_id = message_obj.chat.id
    replay_to_id = message_obj.reply_to_message.message_id if message_obj.reply_to_message else None

    logger.info(f'replay_to_id: {replay_to_id}')

    messages = []
    while replay_to_id and depth > 0:
        previous_message = await bot_chat_messages_cache.get_message(chat_id, replay_to_id)
        logger.info(f'[_get_raw_dialog_messages] Found previous_message: {previous_message}')
        if previous_message:
            messages.append(previous_message)
            replay_to_id = previous_message.replay_to
        depth -= 1

    # Reorder messages to be from last to first.
    return messages[::-1]