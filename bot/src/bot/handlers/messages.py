import logging

from aiogram import types
from aiogram import F

from bot.misc import dp
from bot.utils import remember_groupchat_handler_decorator, cache_message_decorator

logger = logging.getLogger(__name__)

_filter = F.text.regexp(r'(phd|doctor|dog|аспирант|собака)')


@dp.message(_filter)
@dp.channel_post(_filter)
@remember_groupchat_handler_decorator
@cache_message_decorator
async def echo(message: types.Message):
    return await message.answer(message.text)


@dp.message()
@dp.channel_post()
@remember_groupchat_handler_decorator
@cache_message_decorator
async def big_brother_logging_u(message: types.Message):
    logger.info('Log the message...%s', message)
