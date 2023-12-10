import logging

from aiogram import types, Bot, F
from aiogram.filters import Command

from bot.handlers.commands.commands import CommandAdminEnum
from bot.misc import dp, bot_chat_messages_cache
from config.settings import settings

logger = logging.getLogger(__name__)

from_superadmin_filter = F.chat.func(lambda chat: chat.id in settings.TG_SUPERADMIN_IDS)


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
            message += (
                f'--------------------\n'
                f'Stats for {stored_chat_id}:\n'
                f'--------------------\n'
                f'{username = }\n'
                f'{title = }\n\n'
            )
            message_counter += 1

    await bot.send_message(send_to, message)
    return message_counter


async def _show_all_chats_stats(send_to: int, bot: Bot):
    bot_chat_messages_cache_keys_iterator = bot_chat_messages_cache.get_all_chats_iterator()
    total_messages_counter = 0
    async for chat_keys in bot_chat_messages_cache_keys_iterator:
        logger.info(f'Get {chat_keys =} for this batch')
        # Convert all keys to chat ids.
        fetched_chat_ids = [bot_chat_messages_cache.to_chat_id_from_key(x) for x in chat_keys]
        logger.info(f'Convert to {fetched_chat_ids =}')
        total_messages_counter += await _show_chats_stats(fetched_chat_ids, send_to, bot)

    return await bot.send_message(send_to, f'\nTotal chats: {total_messages_counter}')


@dp.message(Command(CommandAdminEnum.show_chat_stats.name), from_superadmin_filter)
async def handle_show_chats_stats(message: types.Message, bot: Bot, *args, **kwargs):
    logger.info('[handle_show_chats_stats] Start collecting stats and send to admin...')
    return await _show_all_chats_stats(message.chat.id, bot)
