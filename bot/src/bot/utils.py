from aiogram import types

from bot.misc import bot_chats_storage, bot_chat_messages_cache


def remember_groupchat_handler_decorator(func):
    """In order to find group chats where bot already exists."""
    async def wrapper(message: types.Message):
        if not message.content_type == types.ChatType.PRIVATE:  # noqa
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
    async def wrapper(message: types.Message):
        await _store_message(message)
        return await func(message)
    return wrapper


async def cache_bot_messages(message: types.Message):
    """To support bot conversation we have to store bot messages as well."""
    return await _store_message(message)
