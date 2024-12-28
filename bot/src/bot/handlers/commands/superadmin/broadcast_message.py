import logging

from aiogram import types, Bot
from aiogram.filters import Command

from bot.filters import from_superadmin_filter
from bot.handlers.commands.commands import CommandAdminEnum
from bot.misc import dp, bot_chats_storage
from bot.utils import cache_message_decorator
from config.settings import settings
from utils.redis.redis_storage import get_unique_chat_ids_from_storage

logger = logging.getLogger(__name__)


@dp.message(Command(CommandAdminEnum.broadcast_message.name), from_superadmin_filter)
@cache_message_decorator
async def handle_broadcast_message(message: types.Message, bot: Bot, *args, **kwargs):
    """Currently it handle only photos and videos and text."""
    logger.info('[handle_broadcast_message] Handle request to broadcast message: %s...', message)
    if message.reply_to_message is None:
        return await message.reply(
            f'No message mentioned. Start again with command: {CommandAdminEnum.broadcast_message.tg_command} '
            f'and replay on message you want to broadcast.'
        )

    message_to_broadcast_id = message.reply_to_message.message_id
    excluded_chats = set(settings.TG_PHD_WORK_EXCLUDE_CHATS) if settings.TG_PHD_WORK_EXCLUDE_CHATS else set()
    counter = 0
    exceptions = []
    # Broadcast to every remembered chat.
    unique_chat_ids = await get_unique_chat_ids_from_storage(bot_chats_storage)
    logger.info(f'Fetched {len(unique_chat_ids)} unique chat ids...filter them for excluded chats.')

    broadcasted_to = []
    broadcasted_to_failed = []
    for chat_id in unique_chat_ids:
        if chat_id in excluded_chats:
            continue
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message_to_broadcast_id,
            )
            # await cache_message_text(msg) TODO: impossible to cache message...
            counter += 1
            broadcasted_to.append(chat_id)
        except Exception as e:
            exceptions.append(f'Error with chat_id {chat_id}: {e}')
            broadcasted_to_failed.append(chat_id)

    about_failed_msg = (
        f' Failed to broadcast to {len(broadcasted_to_failed)} chats: {broadcasted_to_failed}'
        if broadcasted_to_failed else ''
    )
    return await message.reply(
        f'Broadcasted this message via command to {counter} chats: {broadcasted_to}.' + about_failed_msg
    )
