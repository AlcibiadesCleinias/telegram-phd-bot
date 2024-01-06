import logging
from typing import Optional

from bot.misc import bot, bot_chat_messages_cache
from config.settings import settings
from utils.cron import CronTaskBase
from utils.generators import batch
from utils.redis.redis_storage import get_unique_chat_ids_from_storage

logger = logging.getLogger(__name__)


async def send_sticker_to_chats(chat_ids, sticker_id: str, chats_to_exclude: Optional[set[int]] = None):
    for chat_id in chat_ids:
        if chats_to_exclude and chat_id in chats_to_exclude:
            continue
        logger.info('Send phd sticker to chat %s...', chat_id)
        try:
            await bot.send_sticker(chat_id, sticker_id)
        except Exception as e:
            logger.warning('Could not send phd sticker to the chat %s, error %s. Pass it...', chat_id, e)


async def _notify_all_chats_with_sticker(
        sticker_id: str,
        chats_to_exclude: Optional[list[int]] = None,
        prioritised_chats: Optional[list[int]] = None,
):
    _chats_to_exclude = set(chats_to_exclude) if chats_to_exclude else set()

    logger.info('[_notify_all_chats_with_sticker] Firstly send to prioritised_chats (if active): %s', prioritised_chats)
    if prioritised_chats:
        # Check if chat has recent messages.
        prioritised_active_chats = []
        # 1 query to Redis.
        prioritised_chats_is_active = await bot_chat_messages_cache.has_messages(prioritised_chats)
        for chat_id, is_active in zip(prioritised_chats, prioritised_chats_is_active):
            if is_active:
                prioritised_active_chats.append(chat_id)
        if prioritised_active_chats:
            await send_sticker_to_chats(prioritised_active_chats, sticker_id, _chats_to_exclude)

    prioritised_chats = set(prioritised_chats) if prioritised_chats else set()
    unique_chat_ids = await get_unique_chat_ids_from_storage(bot_chat_messages_cache)

    for batch_chat_ids in batch(list(unique_chat_ids), 5):
        logger.info('[_notify_all_chats_with_sticker] Fetched other chats: %s', batch_chat_ids)
        logger.info(f'[_notify_all_chats_with_sticker] Should be excluded: {prioritised_chats} and {_chats_to_exclude}')
        if not batch_chat_ids:
            continue

        await send_sticker_to_chats(
            [chat for chat in batch_chat_ids if chat not in prioritised_chats and chat not in _chats_to_exclude],
            sticker_id,
        )


phd_work_notification_task: CronTaskBase = CronTaskBase(
    cron_expression=settings.TG_BOT_PHD_WORK_TASK_CRON,
    coro=_notify_all_chats_with_sticker,
    args=(settings.TG_PHD_WORK_STICKER_ID, settings.TG_PHD_WORK_EXCLUDE_CHATS, settings.PRIORITY_CHATS),
)
