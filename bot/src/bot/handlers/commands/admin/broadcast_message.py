import logging

from aiogram import types, Bot
from aiogram.filters import Command

from bot.handlers.commands.admin.filters import from_superadmin_filter
from bot.handlers.commands.commands import CommandAdminEnum
from bot.misc import dp, bot_chat_messages_cache, bot_chats_storage
from bot.utils import cache_message_decorator
from config.settings import settings

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
    message_to_broadcast = await bot_chat_messages_cache.get_message(message.chat.id, message_to_broadcast_id)
    if not message_to_broadcast:
        return await message.replay('Message was not found in cache.')

    excluded_chats = set(settings.TG_PHD_WORK_EXCLUDE_CHATS) if settings.TG_PHD_WORK_EXCLUDE_CHATS else set()
    counter = 0
    exceptions = []
    async for chat_keys in await bot_chats_storage.get_all_chats_iterator():
        logger.info(f'Fetched {len(chat_keys)} chat ids...filter them for excluded chats.')
        chat_ids = [bot_chats_storage.to_chat_id_from_key(x) for x in chat_keys if x is not None]
        chat_ids_to_send = [chat for chat in chat_ids if chat not in excluded_chats]

        for chat_id in chat_ids_to_send:
            try:
                await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message_to_broadcast_id,
                )
                # await cache_message_text(msg) TODO: impossible to cache message...
                counter += 1
            except Exception as e:
                exceptions.append(f'Error with chat_id {chat_id}: {e}')

    return await message.reply(f'Broadcast this message with comand to {counter} chats.')
