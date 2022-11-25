import logging

from bot.misc import bot, bot_chats_storage
from config.settings import settings
from utils.cron import CronTaskBase

logger = logging.getLogger(__name__)


async def send_sticker_to_chats(chat_ids, sticker_id: str):
    for chat_id in chat_ids:
        logger.info('Send phd sticker to chat %s...', chat_id)
        await bot.send_sticker(chat_id, sticker_id)


async def _notify_all_chats_with_sticker(sticker_id: str):
    prioritised_chats = await bot_chats_storage.get_prioritised_chats()
    logger.info('Fetched priorities chats: %s', prioritised_chats)
    if prioritised_chats:
        await send_sticker_to_chats(prioritised_chats, sticker_id)

    economy_chats = await bot_chats_storage.get_economy_chats()
    logger.info('Fetched economy chats: %s', economy_chats)
    if not economy_chats:
        return

    to_exclude_from_economy = set(
        prioritised_chats) if prioritised_chats else set()
    await send_sticker_to_chats([chat for chat in economy_chats if chat not in to_exclude_from_economy], sticker_id)


class PhDWorkNotificationTask(CronTaskBase):
    def __init__(self):
        super().__init__(
            settings.TG_BOT_PHD_WORK_TASK_CRON,
            coro=_notify_all_chats_with_sticker,
            args=(settings.TG_PHD_WORK_STICKER_ID,),
        )
