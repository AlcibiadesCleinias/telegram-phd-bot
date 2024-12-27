import logging
from functools import partial

from aiogram import types, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.filters import IsFromContributorInAllowedChatFilter, from_prioritised_chats_filter, from_superadmin_filter
from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp, bot_chat_discussion_mode_storage
from bot.consts import AIDiscussionMode
from bot.utils import cache_message_decorator, remember_chat_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)

_command_filter = Command(CommandEnum.switch_discussion_mode.name)

is_from_contributor_in_allowed_chat_filter = IsFromContributorInAllowedChatFilter()


async def _switch_mode(message: types.Message, current_mode: AIDiscussionMode, set_mode_func) -> None:
    logger.info(f'{current_mode == AIDiscussionMode.OPENAI}')
    new_mode = AIDiscussionMode.PERPLEXITY if (current_mode is None or current_mode == AIDiscussionMode.OPENAI) else AIDiscussionMode.OPENAI
    await set_mode_func(discussion_mode=new_mode)
    return await message.reply(f'Discussion mode switched to {html.bold(new_mode.get_mode_name())}')


@dp.message(_command_filter, from_prioritised_chats_filter)
@dp.message(_command_filter, from_superadmin_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_discussion_mode_in_priority_chats(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('User %s in prioritised chat used command %s...', message.from_user.username, CommandEnum.switch_discussion_mode.name)
    current_mode = await bot_chat_discussion_mode_storage.get_discussion_mode(message.chat.id)
    logger.info('current_mode: %s', current_mode)
    return await _switch_mode(
        message, 
        current_mode,
        partial(bot_chat_discussion_mode_storage.set_discussion_mode, chat_id=message.chat.id)
    )


@dp.message(_command_filter, is_from_contributor_in_allowed_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_discussion_mode_in_contributor_chat(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('User %s in contributor chat and being contributor used command %s...', message.from_user.username, CommandEnum.switch_discussion_mode.name)
    current_mode = await bot_chat_discussion_mode_storage.get_discussion_mode_by_contributor(message.chat.id, message.from_user.id)
    return await _switch_mode(
        message,
        current_mode,
        partial(bot_chat_discussion_mode_storage.set_discussion_mode_by_contributor, 
               chat_id=message.chat.id, 
               user_id=message.from_user.id)
    )
