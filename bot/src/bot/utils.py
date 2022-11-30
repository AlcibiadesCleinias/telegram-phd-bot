from aiogram import types

from bot.misc import bot_chats_storage


def is_groupchat_remembered_handler_decorator(func):
    """In order to find group chats where bot already exists."""

    async def wrapper(message: types.Message):
        if not message.content_type == types.ChatType.PRIVATE:  # noqa
            await bot_chats_storage.set_chat(message.chat.id)
        return await func(message)

    return wrapper
