import json
import logging

from aiogram import types, Bot, F
from aiogram.filters import Command

from bot.handlers.commands.commands import CommandAdminEnum, CommandEnum
from bot.misc import dp, bot_chat_messages_cache, bot_contributor_chat_storage
from bot.utils import cache_message_decorator, cache_message
from config.settings import settings

logger = logging.getLogger(__name__)

from_superadmin_filter = F.chat.func(lambda chat: chat.id in settings.TG_SUPERADMIN_IDS)


@dp.message(Command(CommandEnum.show_admin_commands.name))
@cache_message_decorator
async def handle_show_admin_commands(message: types.Message, bot: Bot, *args, **kwargs):
    if message.chat.id not in settings.TG_SUPERADMIN_IDS:
        return await message.reply('You are not authorized to.')
    return await message.reply(json.dumps(CommandAdminEnum.get_all_commands_json()))


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
    await cache_message(msg)
    return message_counter


def _batch(iterable, n=100):
    iterable_len = len(iterable)
    for ndx in range(0, iterable_len, n):
        yield iterable[ndx:min(ndx + n, iterable_len)]


async def _show_all_chats_stats(send_to: int, bot: Bot, async_iterator, to_chat_id_from_key):
    total_messages_counter = 0
    unique_chat_ids = set()
    async for chat_keys in async_iterator:
        logger.info(f'Get {chat_keys =} for this batch')
        # Convert all keys to chat ids.
        fetched_chat_ids = [to_chat_id_from_key(x) for x in chat_keys if x is not None]
        unique_chat_ids.update(fetched_chat_ids)
        logger.info(f'Convert to {fetched_chat_ids =}')

    for batch_chat_ids in _batch(list(unique_chat_ids)):
        total_messages_counter += await _show_chats_stats(batch_chat_ids, send_to, bot)

    return await bot.send_message(send_to, f'\nTotal chats: {total_messages_counter}')


@dp.message(Command(CommandAdminEnum.show_chat_stats.name), from_superadmin_filter)
@cache_message_decorator
async def handle_show_chats_stats(message: types.Message, bot: Bot, *args, **kwargs):
    logger.info('[handle_show_chats_stats] Start collecting stats and send to admin...')
    iterator = await bot_chat_messages_cache.get_all_chats_iterator()
    return await _show_all_chats_stats(message.chat.id, bot, iterator, bot_chat_messages_cache.to_chat_id_from_key)


@dp.message(Command(CommandAdminEnum.show_openai_token_stats.name), from_superadmin_filter)
@cache_message_decorator
async def handle_show_openai_token_stats(message: types.Message, bot: Bot, *args, **kwargs):
    logger.info('[show_openai_token_stats] Start collecting stats and send to admin...')
    iterator = await bot_contributor_chat_storage.get_all_chats_iterator()
    return await _show_all_chats_stats(message.chat.id, bot, iterator, bot_contributor_chat_storage.to_chat_id_from_key)
