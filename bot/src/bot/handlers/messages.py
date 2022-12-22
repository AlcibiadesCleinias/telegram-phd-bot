import logging

from aiogram import types

from bot.misc import dp
from bot.utils import is_groupchat_remembered_handler_decorator

logger = logging.getLogger(__name__)


@dp.message_handler(regexp='(phd|doctor|dog|аспирант|собака)')
@is_groupchat_remembered_handler_decorator
async def echo(message: types.Message):
    await message.answer(message.text)


@dp.message_handler()
@is_groupchat_remembered_handler_decorator
async def big_brother_logging_u(message: types.Message):
    logger.info(message)
