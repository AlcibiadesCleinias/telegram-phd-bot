# To handle that the bot entered into chat, not private one.
import logging
import random

from aiogram import types

from bot.misc import dp, bot_chats_storage
from bot.misc import bot

logger = logging.getLogger(__name__)


async def _greeting_new_chat_with_message(chat_id: int, added_by: str):
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


@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
@dp.message_handler(content_types=types.ChatType.GROUP)
@dp.message_handler(content_types=types.ChatType.SUPERGROUP)
@dp.message_handler(content_types=types.ChatType.SUPER_GROUP)
async def handle_bot_added(message: types.Message):
    new_members = message.new_chat_members
    _chat_id = message.chat.id
    if not new_members:
        return

    for new_member in new_members:
        if new_member.id == bot.id:
            logger.info(
                'Bot added to chat %s, remember chat & greeting them...', message.chat)
            await bot_chats_storage.set_chat(_chat_id)
            return await _greeting_new_chat_with_message(_chat_id, message.from_user.username)

        if new_member.is_bot:
            logger.info(
                'Seems that anther bot is added, lol what? PhD is enough!')
            await bot.send_sticker(
                chat_id=_chat_id,
                sticker=random.choice([
                    'CAACAgIAAxkBAAMXY4FGOHQEoBQOXeFNbyRsvCUjJwwAAh4AA9hqFhC54KH2Y0uvMSsE',  # x2 patience
                    'CAACAgIAAxkBAAMYY4FG0OJGNHutJs7HOB-dSib3Ka0AApALAAIZMmlLPVTPcD_fL-orBA',  # wolfs
                    'CAACAgIAAxkBAAMZY4FG9Qnbd9Ey1ke8PM6OpVZJjCwAAjsAA9hqFhCF7ZN7k0X6YSsE',  # failed forever
                ]),
            )
