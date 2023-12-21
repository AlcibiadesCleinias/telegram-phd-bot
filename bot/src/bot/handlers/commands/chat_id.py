import logging

from aiogram import types, html
from aiogram.filters import Command
from aiogram.utils.markdown import hbold

from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp
from bot.utils import cache_message_decorator, remember_chat_handler_decorator

logger = logging.getLogger(__name__)


@dp.message(Command(CommandEnum.show_chat_id.name))
@dp.channel_post(Command(CommandEnum.show_chat_id.name))
@remember_chat_handler_decorator
@cache_message_decorator
async def show_chat_id(message: types.Message, *args, **kwargs):
    return await message.answer(
        f'Here is your {hbold("chat id")}, my colleague: ' + html.code(f'{message.chat.id}'),
    )
