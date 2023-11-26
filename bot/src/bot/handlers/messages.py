import logging

from aiogram import types

from bot.misc import dp
from bot.utils import is_groupchat_remembered_handler_decorator, cache_message_decorator, cache_bot_messages

logger = logging.getLogger(__name__)

_filter = {'regexp': '(phd|doctor|dog|аспирант|собака)'}


@dp.message_handler(**_filter)
@dp.channel_post_handler(**_filter)
@is_groupchat_remembered_handler_decorator
@cache_message_decorator
async def echo(message: types.Message):
    sent = await message.answer(message.text)
    await cache_bot_messages(sent)


@dp.message_handler()
@dp.channel_post_handler()
@is_groupchat_remembered_handler_decorator
@cache_message_decorator
async def big_brother_logging_u(message: types.Message):
    logger.info(message)
