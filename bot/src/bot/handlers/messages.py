from aiogram import types

from bot.misc import dp
from bot.utils import is_chat_remembered_handler_decorator


@dp.message_handler(regexp='(phd|doctor|dog|аспирант)')
@is_chat_remembered_handler_decorator
async def echo(message: types.Message):
    await message.answer(message.text)
