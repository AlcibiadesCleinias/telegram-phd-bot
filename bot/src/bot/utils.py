from aiogram import types
from aiogram.enums import ChatType

from bot.misc import bot_chats_storage, bot_chat_messages_cache


def remember_groupchat_handler_decorator(func):
    """In order to find group chats where bot already exists."""
    async def wrapper(message: types.Message):
        if not message.content_type == ChatType.PRIVATE:
            await bot_chats_storage.set_chat(message.chat.id)
        return await func(message)
    return wrapper


async def _store_message(message: types.Message):
    if message.text:
        message_replay_to = message.reply_to_message
        replay_to = message_replay_to.message_id if message_replay_to else None
        await bot_chat_messages_cache.set_message(
            message.chat.id,
            message.message_id,
            bot_chat_messages_cache.MessageData(
                sender=message.from_user.username,
                replay_to=replay_to,
                text=message.text,
            )
        )


def cache_message_decorator(func):
    """It caches both: received and sent messages."""
    async def wrapper(message: types.Message):
        await _store_message(message)
        response = await func(message)
        if response:
            return await _store_message(response)
        return
    return wrapper
