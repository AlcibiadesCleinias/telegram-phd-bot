import logging

from aiogram import types

from bot.misc import dp
from bot.utils import remember_groupchat_handler_decorator, cache_message_decorator

logger = logging.getLogger(__name__)

_filter = {'regexp': '(phd|doctor|dog|аспирант|собака)'}


@dp.message_handler(**_filter)
@dp.channel_post_handler(**_filter)
@remember_groupchat_handler_decorator
@cache_message_decorator
async def echo(message: types.Message):
    return await message.answer(message.text)


@dp.message_handler()
@dp.channel_post_handler()
@remember_groupchat_handler_decorator
@cache_message_decorator
async def big_brother_logging_u(message: types.Message):
    logger.info(message)
