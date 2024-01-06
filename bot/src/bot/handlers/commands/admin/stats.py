import logging
from typing import Optional

from aiogram import types, Bot
from aiogram.filters import Command

from bot.handlers.commands.admin.filters import from_superadmin_filter
from bot.handlers.commands.commands import CommandAdminEnum, CommandEnum
from bot.misc import dp, bot_chat_messages_cache, bot_contributor_chat_storage, bot_chats_storage
from bot.utils import cache_message_decorator, cache_message_text
from config.settings import settings
from utils.generators import batch
from utils.redis.redis_storage import get_unique_chat_ids_from_storage, BotChatsStorageABC

logger = logging.getLogger(__name__)


@dp.message(Command(CommandEnum.show_admin_commands.name))
@cache_message_decorator
async def handle_show_admin_commands(message: types.Message, bot: Bot, *args, **kwargs):
    if message.chat.id not in settings.TG_SUPERADMIN_IDS:
        return await message.reply('You are not authorized to.')
    return await message.reply(CommandAdminEnum.pretty_print_all())


async def _show_chats_stats(stored_chat_ids: list[int], send_to: int, bot: Bot) -> int:
    message_counter = 0
    message = ''
    for stored_chat_id in stored_chat_ids:
        logger.info('Compose for fetched key %s...', stored_chat_id)
        if stored_chat_id:
            try:
                chat = await bot.get_chat(stored_chat_id)
            except Exception as e:
                logger.warning('Chat %s is not fetched, error: %s. Pass...', stored_chat_id, e)
                continue

            username = chat.username
            title = chat.title
            description = chat.description
            chat_type = chat.type
            message += (
                f'--------------------\n'
                f'Stats for {stored_chat_id}:\n'
                f'--------------------\n'
                f'{username = }\n'
            )
            message += f'{title = }\n' if title else ''
            message += f'{description = }\n' if description else ''
            message += f'{chat_type = }\n' if chat_type else ''
            message += '\n'
            message_counter += 1

    msg = await bot.send_message(send_to, message)
    await cache_message_text(msg)
    return message_counter


async def _show_all_chats_stats(
        send_to: int, bot: Bot, bot_chats_storage_object: BotChatsStorageABC, prefix: Optional[str] = None
):
    unique_chat_ids = await get_unique_chat_ids_from_storage(bot_chats_storage_object)

    total_messages_counter = 0
    await bot.send_message(send_to, prefix) if prefix else None
    for batch_chat_ids in batch(list(unique_chat_ids), 5):
        total_messages_counter += await _show_chats_stats(batch_chat_ids, send_to, bot)

    return await bot.send_message(send_to, f'\nTotal chats: {total_messages_counter}')


@dp.message(Command(CommandAdminEnum.show_chat_stats.name), from_superadmin_filter)
@cache_message_decorator
async def handle_show_chats_stats(message: types.Message, bot: Bot, *args, **kwargs):
    logger.info('[handle_show_chats_stats] Start collecting stats and send to admin...')
    await _show_all_chats_stats(message.chat.id, bot, bot_chat_messages_cache, 'All active chats\n--------')
    await _show_all_chats_stats(message.chat.id, bot, bot_chats_storage, 'All ever used chats\n--------')


@dp.message(Command(CommandAdminEnum.show_openai_token_stats.name), from_superadmin_filter)
@cache_message_decorator
async def handle_show_openai_token_stats(message: types.Message, bot: Bot, *args, **kwargs):
    logger.info('[show_openai_token_stats] Start collecting stats and send to admin...')
    return await _show_all_chats_stats(message.chat.id, bot, bot_contributor_chat_storage)
