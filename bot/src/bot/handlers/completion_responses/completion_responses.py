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
    discussion_mode = await bot_chat_discussion_mode_storage.get_discussion_mode(message.chat.id)
    if discussion_mode and discussion_mode == AIDiscussionMode.PERPLEXITY:
        if not tokens.perplexity_token:
            return await message.reply(
                f'You have not provided your Perplexity token for this chat. '
                f'Use {CommandEnum.add_perplexity_token.tg_command} to add it.'
            )
        return await _handle_perplexity_contributor_message(message, tokens.perplexity_token)
    else:
        # In case if not specified: use default OpenAI.
        if not tokens.openai_token:
            return await message.reply(
                f'You have not provided your OpenAI token for this chat. '
                f'Use {CommandEnum.add_openai_token.tg_command} to add it.'
            )
        return await _handle_openai_contributor_message(message, tokens.openai_token)


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
