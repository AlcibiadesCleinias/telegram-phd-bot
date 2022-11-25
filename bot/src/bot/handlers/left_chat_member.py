# To handle bot removed from a chat.
import logging

from aiogram import types

from bot.misc import dp, bot_chats_storage, bot

logger = logging.getLogger(__name__)


@dp.message_handler(
    content_types=types.ContentTypes.LEFT_CHAT_MEMBER
)
async def handle_bot_left(message: types.Message):
    left_member = message.left_chat_member
    _chat = message.chat
    if left_member.id == bot.id:
        logger.warning('%s removed the bot from a chat %s',
                       message.from_user.username, _chat)
        await bot_chats_storage.rm_chat(_chat.id)
