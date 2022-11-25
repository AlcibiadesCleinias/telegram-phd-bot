from aiogram import types

from bot.misc import dp
from bot.utils import is_chat_remembered_handler_decorator


@dp.message_handler()
@is_chat_remembered_handler_decorator
async def echo(message: types.Message):
    await message.answer(message.text)
