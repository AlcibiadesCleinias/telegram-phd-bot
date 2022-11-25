from aiogram import types

from bot.misc import bot_chats_storage


def is_chat_remembered_handler_decorator(func):
    """In order to find chats where bot already exists."""
    async def wrapper(message: types.Message):
        await bot_chats_storage.set_chat(message.chat.id)
        return await func(message)
    return wrapper
