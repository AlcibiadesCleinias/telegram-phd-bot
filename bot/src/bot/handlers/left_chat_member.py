# # To handle bot removed from a chat.
import logging

from aiogram import Bot
from aiogram.filters import ChatMemberUpdatedFilter, LEAVE_TRANSITION
from aiogram.types import ChatMemberUpdated

from bot.misc import dp, bot_chats_storage

logger = logging.getLogger(__name__)


@dp.my_chat_member(~ChatMemberUpdatedFilter(~LEAVE_TRANSITION))
async def handle_bot_left(chat_member: ChatMemberUpdated, bot: Bot, *args, **kwargs) -> None:
    chat_id = chat_member.chat.id
    logger.warning('[handle_bot_left] %s removed the bot from a chat %s',
                   chat_member.from_user.username, chat_id)
    await bot_chats_storage.rm_chat(chat_id)
