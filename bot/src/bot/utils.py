from aiogram import types

from bot.misc import bot_chats_storage, bot_chat_messages_cache


def is_groupchat_remembered_handler_decorator(func):
    """In order to find group chats where bot already exists."""

    async def wrapper(message: types.Message):
        if not message.content_type == types.ChatType.PRIVATE:  # noqa
            await bot_chats_storage.set_chat(message.chat.id)
        return await func(message)
    return wrapper


def log_message_decorator(func):
    async def wrapper(message: types.Message):
        if message.text:
            message_replay_to = message.reply_to_message
            replay_to = message_replay_to.message_id if message_replay_to else None
            await bot_chat_messages_cache.set_message(
                message.chat.id,
                message.message_id,
                message.text,
                replay_to,
            )
        return await func(message)
    return wrapper
