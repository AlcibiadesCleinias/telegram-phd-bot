import logging
from typing import Optional

from bot.misc import bot, bot_chats_storage
from config.settings import settings
from utils.cron import CronTaskBase

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

    logger.info('Firstly send to prioritised_chats: %s', prioritised_chats)
    if prioritised_chats:
        await send_sticker_to_chats(prioritised_chats, sticker_id, _chats_to_exclude)

    prioritised_chats = set(prioritised_chats) if prioritised_chats else set()
    async for chat_keys in await bot_chats_storage.get_all_chats_iterator():
        economy_chats = [bot_chats_storage.to_chat_id_from_key(x) for x in chat_keys if x is not None]
        logger.info('Fetched other chats: %s', economy_chats)
        logger.info(f'Should be excluded: {prioritised_chats} and {_chats_to_exclude}')
        if not economy_chats:
            return

        await send_sticker_to_chats(
            [chat for chat in economy_chats if chat not in prioritised_chats and chat not in _chats_to_exclude],
            sticker_id,
        )


phd_work_notification_task: CronTaskBase = CronTaskBase(
    cron_expression=settings.TG_BOT_PHD_WORK_TASK_CRON,
    coro=_notify_all_chats_with_sticker,
    args=(settings.TG_PHD_WORK_STICKER_ID, settings.TG_PHD_WORK_EXCLUDE_CHATS, settings.PRIORITY_CHATS),
)
