import logging
from functools import partial

from aiogram import types, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.filters import IsFromContributorInAllowedChatFilter, from_prioritised_chats_filter
from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp, bot_chat_discussion_mode_storage
from bot.utils import cache_message_decorator, remember_chat_handler_decorator

logger = logging.getLogger(__name__)

_command_filter = Command(CommandEnum.switch_mention_only_mode.name)

is_from_contributor_in_allowed_chat_filter = IsFromContributorInAllowedChatFilter()


async def _switch_mode(message: types.Message, is_mention_only_mode: bool, set_mode_func) -> types.Message:
    logger.info('[_switch_mode] Current is_mention_only_mode: %s', is_mention_only_mode)
    new_mode = not is_mention_only_mode
    await set_mode_func(is_mention_only_mode=new_mode)
    
    mode_name_status = "enabled" if new_mode else "disabled"
    return await message.reply(f'Mention only mode: {html.bold(mode_name_status)}')


@dp.message(_command_filter, from_prioritised_chats_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_mention_only_mode_in_priority_chats(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('[switch_mention_only_mode_in_priority_chats] User %s in prioritised chat used command %s...', message.from_user.username, CommandEnum.switch_mention_only_mode.name)
    is_mention_only_mode = await bot_chat_discussion_mode_storage.get_is_mention_only_mode(message.chat.id)
    return await _switch_mode(
        message=message, 
        is_mention_only_mode=is_mention_only_mode,
        set_mode_func=partial(bot_chat_discussion_mode_storage.set_is_mention_only_mode, chat_id=message.chat.id)
    )


@dp.message(_command_filter, is_from_contributor_in_allowed_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_mention_only_mode_in_contributor_chat(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('[switch_mention_only_mode_in_contributor_chat] User %s in contributor chat and being contributor used command %s...', message.from_user.username, CommandEnum.switch_mention_only_mode.name)
    is_mention_only_mode = await bot_chat_discussion_mode_storage.get_is_mention_only_mode_by_contributor(message.chat.id, message.from_user.id)
    return await _switch_mode(
        message=message,
        is_mention_only_mode=is_mention_only_mode,
        set_mode_func=partial(
            bot_chat_discussion_mode_storage.set_is_mention_only_mode_by_contributor,
            chat_id=message.chat.id,
            user_id=message.from_user.id,
        )
    )
