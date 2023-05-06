import logging

from aiogram import types

from bot.misc import dp
from bot.utils import is_groupchat_remembered_handler_decorator, log_message_decorator

logger = logging.getLogger(__name__)

_filter = {'regexp': '(phd|doctor|dog|аспирант|собака)'}


@dp.message_handler(**_filter)
@dp.channel_post_handler(**_filter)
@is_groupchat_remembered_handler_decorator
@log_message_decorator
async def echo(message: types.Message):
    await message.answer(message.text)


@dp.message_handler()
@dp.channel_post_handler()
@is_groupchat_remembered_handler_decorator
@log_message_decorator
async def big_brother_logging_u(message: types.Message):
    logger.info(message)
