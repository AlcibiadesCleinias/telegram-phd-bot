import logging

from aiogram import types, html
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove

from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp
from bot.utils import cache_message_decorator

logger = logging.getLogger(__name__)


@dp.message(Command(CommandEnum.show_chat_id.name))
@dp.channel_post(Command(CommandEnum.show_chat_id.name))
@cache_message_decorator
async def show_chat_id(message: types.Message, *args, **kwargs):
    return await message.answer(
        'Here you is your **chat id**, my colleague: ' + html.code(f'{message.chat.id}'),
        reply_markup=ReplyKeyboardRemove(),
    )
