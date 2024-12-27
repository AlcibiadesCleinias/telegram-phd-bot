import logging

from aiogram import types, html

from bot.handlers.completion_responses.openai import send_openai_response
from bot.handlers.completion_responses.perplexity import send_perplexity_response
from bot.misc import dp, openai_client_priority, bot_ai_contributor_chat_storage, perplexity_client_priority, bot_chat_discussion_mode_storage
from bot.consts import AIDiscussionMode
from bot.handlers.commands.commands import CommandEnum
from clients.perplexity.client import PerplexityClient
from bot.utils import remember_chat_handler_decorator, cache_message_decorator
from clients.openai.client import OpenAIClient, OpenAIInvalidRequestError
from bot.filters import (
    IsForSuperadminIteractedWithBotFilter, IsChatGptTriggerInPriorityChatFilter,
    IsChatGPTTriggerInContributorChatFilter,
)
from config.settings import settings

logger = logging.getLogger(__name__)

superadmin_iteracted_with_bot_filter = IsForSuperadminIteractedWithBotFilter(settings.TG_SUPERADMIN_IDS)
is_trigger_in_priority_chat_filter = IsChatGptTriggerInPriorityChatFilter(settings.PRIORITY_CHATS)
is_trigger_in_contributor_chat_filter = IsChatGPTTriggerInContributorChatFilter()


@dp.message(is_trigger_in_priority_chat_filter)
@dp.message(superadmin_iteracted_with_bot_filter)
@dp.channel_post(is_trigger_in_priority_chat_filter)
@dp.channel_post(superadmin_iteracted_with_bot_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_completion_response(message: types.Message, *args, **kwargs):
    logger.info('[send_completion_response] Use priority completion client...')
    discussion_mode = await bot_chat_discussion_mode_storage.get_discussion_mode(message.chat.id)
    if discussion_mode and discussion_mode== AIDiscussionMode.PERPLEXITY:
        return await send_perplexity_response(message, perplexity_client=perplexity_client_priority)
    else:
        # In case if not specified: use default OpenAI.
        return await send_openai_response(message, openai_client=openai_client_priority)


@dp.message(is_trigger_in_contributor_chat_filter)
@dp.channel_post(is_trigger_in_contributor_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_completion_response_for_contributor(message: types.Message, *args, **kwargs):
    logger.info('[send_completion_response_for_contributor] Use contributor completion client...')
    tokens = await bot_ai_contributor_chat_storage.get(message.from_user.id, message.chat.id)
    discussion_mode = await bot_chat_discussion_mode_storage.get_discussion_mode_by_contributor(
        message.chat.id, message.from_user.id,
    )
    logger.info(f'[send_completion_response] Current discussion mode: {discussion_mode}')

    # Determine current and fallback modes
    is_perplexity = discussion_mode == AIDiscussionMode.PERPLEXITY
    current_token = tokens.perplexity_token if is_perplexity else tokens.openai_token
    fallback_token = tokens.openai_token if is_perplexity else tokens.perplexity_token
    current_mode = AIDiscussionMode.PERPLEXITY if is_perplexity else AIDiscussionMode.OPENAI
    fallback_mode = AIDiscussionMode.OPENAI if is_perplexity else AIDiscussionMode.PERPLEXITY

    # Try to handle with current mode or fallback.
    if current_token:
        handler = _handle_perplexity_contributor_message if is_perplexity else _handle_openai_contributor_message
        return await handler(message, current_token)
    elif fallback_token:
        # Switch to fallback mode since it has a valid token
        await bot_chat_discussion_mode_storage.set_discussion_mode_by_contributor(
            message.chat.id, message.from_user.id, fallback_mode,
        )
        await message.reply(
            f'Automatically switching to {html.bold(fallback_mode.get_mode_name())} mode since '
            f'{current_mode.get_mode_name()} token is missing.\n\n'
            f'Use {_get_token_command(current_mode)} to add {current_mode.get_mode_name()} token if needed.'
        )
        handler = _handle_perplexity_contributor_message if not is_perplexity else _handle_openai_contributor_message
        return await handler(message, fallback_token)
    
    # No tokens available
    return await message.reply(
        f'You have not provided your {current_mode.get_mode_name()} token for this chat. '
        f'Use {_get_token_command(current_mode)} to add it.\n\n'
        f'Or use {CommandEnum.switch_discussion_mode.tg_command} to switch to '
        f'{html.bold(fallback_mode.get_mode_name())} mode.'
    )

def _get_token_command(mode: AIDiscussionMode) -> str:
    """Helper function to get the appropriate token command based on AI mode."""
    return (CommandEnum.add_perplexity_token.tg_command 
            if mode == AIDiscussionMode.PERPLEXITY 
            else CommandEnum.add_openai_token.tg_command)

async def _handle_openai_contributor_message(message: types.Message, user_token: str):
    try:
        return await send_openai_response(message, OpenAIClient(user_token))
    except OpenAIInvalidRequestError as e:
        logger.warning('[send_openai_response_for_contributor] Could not compose response, got %s...', e)
        # Delete token since it is invalid.
        await bot_ai_contributor_chat_storage.delete_openai_token(message.from_user.id, message.chat.id)
        # Notify user about the deletion.
        return await message.reply(
            'PhD bot from prestigious university and the renowned artificial intelligence company, OpenAI, came '
            'together'
            ' to discuss the latest message from you. The atmosphere was charged with intellectuals and innovators, '
            f"ready to share their opinions and challenge each other's ideas, and short response in situ was made:\n"
            f"{html.code(f'{e}')}.\n\nThus, please, be more specific and clear with your token in the future. Also, "
            f'note that your token '
            f'was deleted from the system automatically for that chat only, you could add another any time again).'
        )
    except Exception as e:
        logger.warning('[send_openai_response_for_contributor] Could not compose response, got %s...', e)
        return await message.reply(
            f'Could not compose response. Check your token or try again later. If the problem persists and want to '
            f'resolve asap, - contribute to the project. {CommandEnum.help.value}'
        )
    

async def _handle_perplexity_contributor_message(message: types.Message, user_token: str):
    try:
        return await send_perplexity_response(message, PerplexityClient(user_token))
    except Exception as e:
        logger.warning('[send_perplexity_response_for_contributor] Could not compose response, got %s...', e)
        return await message.reply(
            f'Could not compose response. Check your token or try again later. If the problem persists and want to '
            f'resolve asap, - contribute to the project. {CommandEnum.help.value}'
        )
