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

_command_filter = Command(CommandEnum.switch_direct_iteration_only.name)

is_from_contributor_in_allowed_chat_filter = IsFromContributorInAllowedChatFilter()


async def _switch_mode(message: types.Message, is_direct_iteration_only: bool, set_mode_func) -> None:
    logger.info(f'Current direct iteration only mode: {is_direct_iteration_only}')
    new_mode = not is_direct_iteration_only
    logger.info('TODO: new_mode: %s', new_mode)
    await set_mode_func(is_direct_iteration_only=new_mode)
    
    mode_name_status = "enabled" if not new_mode else "disabled"
    return await message.reply(f'Direct iteration only mode {html.bold(mode_name_status)}')


@dp.message(_command_filter, from_prioritised_chats_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_direct_iteration_only_in_priority_chats(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('[switch_direct_iteration_only_in_priority_chats] User %s in prioritised chat used command %s...', message.from_user.username, CommandEnum.switch_direct_iteration_only.name)
    is_direct_iteration_only = await bot_chat_discussion_mode_storage.get_is_direct_iteration_only(message.chat.id)
    logger.info('is_direct_iteration_only: %s', is_direct_iteration_only)
    return await _switch_mode(
        message=message, 
        is_direct_iteration_only=is_direct_iteration_only,
        set_mode_func=partial(bot_chat_discussion_mode_storage.set_is_direct_iteration_only, chat_id=message.chat.id)
    )


@dp.message(_command_filter, is_from_contributor_in_allowed_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def switch_direct_iteration_only_in_contributor_chat(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info('[switch_direct_iteration_only_in_contributor_chat] User %s in contributor chat and being contributor used command %s...', message.from_user.username, CommandEnum.switch_direct_iteration_only.name)
    is_direct_iteration_only = await bot_chat_discussion_mode_storage.get_is_direct_iteration_only_by_contributor(message.chat.id, message.from_user.id)
    return await _switch_mode(
        message=message,
        is_direct_iteration_only=is_direct_iteration_only,
        set_mode_func=partial(bot_chat_discussion_mode_storage.set_is_direct_iteration_only_by_contributor, 
               chat_id=message.chat.id, 
               user_id=message.from_user.id)
    )
