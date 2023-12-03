# To handle that the bot entered into the group chat (not private one).
import logging
import random

from aiogram import Bot
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated

from bot.misc import dp, bot_chats_storage

logger = logging.getLogger(__name__)


async def _greeting_new_chat_with_message(chat_id: int, added_by: str, bot: Bot):
    await bot.send_message(
        chat_id=chat_id,
        text=f'Hey, @{added_by}, bro, you are a 10!',
    )

    await bot.send_sticker(
        chat_id=chat_id,
        sticker=random.choice([
            'CAACAgIAAxkBAAMPY4FEqXJOzmDn-Z9QrSQZB1NuRRUAAiMAA9hqFhBhI102zbIPGisE',  # philosophic
            'CAACAgIAAxkBAAMRY4FFEapD6yOPMq1f_8mypGFp_PMAAm8OAAI4jMFKTCG1UlBip9orBA',  # cat touch
            # no rejissers pls
            'CAACAgIAAxkBAAMSY4FFQ-zGUNNO5XXqght9bRCBk5wAApcHAAIqVRgCn3_-FB-vMNkrBA',
            # phystech privetiki
            'CAACAgIAAxkBAAMTY4FFi3ieGtKLdovKVe8H4VpHDM8AAlUAAy9JRwlAdh4AAaUhPp4rBA',
            # good from phystech
            'CAACAgIAAxkBAAMUY4FFshfDJoqHv6ra79mrsdpIcwEAAoMAAy9JRwnSx6AJJMmjkCsE',
            'CAACAgIAAxkBAAMVY4FF2oP_EuWQPssnAAGVZ9S0xCEtAALRDwACp4DIS3HWU9yAn6lZKwQ',  # kice attack
            'CAACAgIAAx0CYy9UggADPWGkPaH7jqm0cFhM6KRhSf61pttsAAINAwACEzmPEWPVqCB_X-3SIgQ',  # boi
            'CAACAgEAAxkBAAMWY4FGA6Fov34xPCZf0g9dgdoBdtAAAgIAA39wRhwFzGTYNyIryCsE',  # social credits
        ]),
    )


@dp.my_chat_member(~ChatMemberUpdatedFilter(~JOIN_TRANSITION))
async def handle_phd_bot_added(chat_member: ChatMemberUpdated, bot: Bot) -> None:
    chat_id = chat_member.chat.id
    logger.info(
        '[handle_phd_bot_added] Bot added to chat %s (username: %s), remember chat & greeting them...',
        chat_id,
        chat_member.chat.username,
    )
    await bot_chats_storage.set_chat(chat_id)
    return await _greeting_new_chat_with_message(chat_id, chat_member.from_user.username, bot)


# To support this filter you should explicitly add **chat_member** to `allowed_updates`.
@dp.chat_member(~ChatMemberUpdatedFilter(~JOIN_TRANSITION))
async def handle_member_added(chat_member: ChatMemberUpdated, bot: Bot):
    """Greeting bot in the same chat."""
    chat_id = chat_member.chat.id
    logger.info(
        '[handle_phd_bot_added] Someone added to chat %s (username: %s), greeting him...',
        chat_id,
        chat_member.chat.username,
    )
    if chat_member.new_chat_member and chat_member.new_chat_member and chat_member.new_chat_member.user.is_bot:
        logger.info(
            'Seems that another bot is added, lol what? PhD is enough!')
        await bot.send_message(
            chat_id=chat_id,
            text=f'@{chat_member.new_chat_member.user.username} added to the chat?...\n'
                 f'Great, just what we needed... another robot!',
        )
        await bot.send_sticker(
            chat_id=chat_id,
            sticker=random.choice([
                'CAACAgIAAxkBAAMXY4FGOHQEoBQOXeFNbyRsvCUjJwwAAh4AA9hqFhC54KH2Y0uvMSsE',  # x2 patience
                'CAACAgIAAxkBAAMYY4FG0OJGNHutJs7HOB-dSib3Ka0AApALAAIZMmlLPVTPcD_fL-orBA',  # wolfs
                'CAACAgIAAxkBAAMZY4FG9Qnbd9Ey1ke8PM6OpVZJjCwAAjsAA9hqFhCF7ZN7k0X6YSsE',  # failed forever
            ]),
        )
