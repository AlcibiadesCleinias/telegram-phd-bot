import logging

from aiogram import types, html

from bot.filters import (
    IsForSuperadminRequestWithTriggerFilter, IsChatGptTriggerInPriorityChatFilter,
    IsChatGPTTriggerInContributorChatFilter,
)
from bot.misc import dp, openai_client_priority, bot_chat_messages_cache, bot_contributor_chat_storage
from bot.utils import remember_chat_handler_decorator, cache_message_decorator, safety_replay_with_text
from clients.openai.client import OpenAIMaxTokenExceededError, OpenAIClient, OpenAIInvalidRequestError
from clients.openai.scheme import ChatMessage
from config.settings import settings

logger = logging.getLogger(__name__)

# TODO: how openai compute token number?
_OPENAI_COMPLETION_LENGTH_ROBUST = int(
    openai_client_priority.COMPLETION_MAX_LENGTH - openai_client_priority.COMPLETION_MAX_LENGTH // 1e3
)


# The same filters for chats and channels.
_superadmin_filter = IsForSuperadminRequestWithTriggerFilter(settings.TG_SUPERADMIN_IDS)
_is_trigger_in_priority_chat_filter = IsChatGptTriggerInPriorityChatFilter(settings.PRIORITY_CHATS)
_is_trigger_in_contributor_chat_filter = IsChatGPTTriggerInContributorChatFilter()


async def _get_dialog_messages_context(message_obj: types.Message, depth: int = 2) -> [ChatMessage]:
    """According to https://docs.aiogram.dev it could not handle depth more than 1.
    thus, message should be cached for depth more than 1.
    """
    logger.info('[_get_dialog_messages_context] Try to fetch previous messages...')
    chat_id = message_obj.chat.id
    replay_to_id = message_obj.reply_to_message.message_id if message_obj.reply_to_message else None

    logger.info(f'replay_to_id: {replay_to_id}')

    chat_messages = []
    # Compose from last one message to 1st one. Thus, I should revert list at the end.
    while replay_to_id and depth > 0:
        # Get message replied on if exist.
        previous_message = await bot_chat_messages_cache.get_message(chat_id, replay_to_id)
        logger.info(f'[_get_dialog_messages_context] Found previous_message: {previous_message}')
        if previous_message:
            chat_messages.append(ChatMessage(
                role=(
                    'user' if previous_message.sender != settings.TG_BOT_USERNAME
                    else openai_client_priority.DEFAULT_CHAT_BOT_ROLE
                ),
                content=previous_message.text
            ))

        replay_to_id = previous_message.replay_to
        depth -= 1

    return chat_messages[::-1]


async def _compose_openapi_completion(message: str, openai_client: OpenAIClient):
    message = f'{message}'

    # OpenAI could not return more than COMPLETION_MAX_LENGTH.
    # Otherwise, you will receive
    # 'error': {'message': "This model's maximum context length is 4097 tokens,
    # however you requested 4121 tokens (121 in your prompt; 4000 for the completion).
    # Please reduce your prompt; or completion length.",
    # 'type': 'invalid_request_error', 'param': None, 'code': None}
    message_length = len(message)
    completion_length = _OPENAI_COMPLETION_LENGTH_ROBUST - message_length
    if completion_length <= 0:
        # Hard text reduce.
        message = message[:message_length // 3]

    try:
        openai_completion = await openai_client.get_completions(message, completion_length)
    except OpenAIMaxTokenExceededError:
        # According to https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them#
        # :~:text=Token%20Limits,shared%20between%20prompt%20and%20completion.
        logger.info('Lets try with 2/3 of completion_length = %s', completion_length)
        openai_completion = await openai_client.get_completions(message, int(completion_length * 2 / 3))
    except OpenAIInvalidRequestError as e:
        logger.info(f'Invalid request were made, got {e}...')
        raise e

    return openai_completion


async def _send_openai_response(message: types.Message, openai_client: OpenAIClient):
    """Rather use completion model or dialog.
        It is based on context existence.
        """
    context_messages = await _get_dialog_messages_context(message, settings.OPENAI_DIALOG_CONTEXT_MAX_DEPTH)
    # If context exists send it as a dialog.
    if not context_messages or len(context_messages) == 0:
        logger.info('[send_openai_response] Request completion for message %s...', message)
        response = await _compose_openapi_completion(message.text, openai_client)
    else:
        logger.info(
            '[send_openai_response] Request chatGPT for context: %s and message %s...', context_messages, message)
        context_messages.append(
            ChatMessage(
                role='user',
                content=message.text,
            )
        )
        response = await openai_client.get_chat_completions(context_messages, settings.OPENAI_CHAT_BOT_GOAL)

    # Sometimes openai do not know what to say.
    if not response:
        response = '.'
    # Response could be bigger than expected - use safety method.
    return await safety_replay_with_text(message, response)


@dp.message(_is_trigger_in_priority_chat_filter)
@dp.message(_superadmin_filter)
@dp.channel_post(_is_trigger_in_priority_chat_filter)
@dp.channel_post(_superadmin_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_openai_response(message: types.Message, *args, **kwargs):
    logger.info('Use priority openai_client...')
    return await _send_openai_response(message, openai_client_priority)


@dp.message(_is_trigger_in_contributor_chat_filter)
@dp.channel_post(_is_trigger_in_contributor_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_openai_response_for_contributor(message: types.Message, *args, **kwargs):
    user_token = await bot_contributor_chat_storage.get(message.from_user.id, message.chat.id)
    logger.info(
        f'[send_openai_response_for_contributor] Use contributor openai_client by {message.from_user = }...')
    try:
        return await _send_openai_response(message, OpenAIClient(user_token))
    except OpenAIInvalidRequestError as e:
        await bot_contributor_chat_storage.delete(message.from_user.id, message.chat.id)
        return await message.reply(
            'PhD bot from prestigious university and the renowned artificial intelligence company, OpenAI, came '
            'together'
            ' to discuss the latest message from you. The atmosphere was charged with intellectuals and innovators, '
            f"ready to share their opinions and challenge each other's ideas, and short response in situ was made:\n"
            f"{html.code(f'{e}')}.\n\nThus, please, be more specific and clear with your token in the future. Also, "
            f'note that your token '
            f'was deleted from the system for that chat only, you could add another any time again).'
        )
    except Exception as e:
        logger.warning('[send_openai_response_for_contributor] Could not compose response, got %s...', e)
        return await message.reply(
            'Could not compose response. Check your token or try again later. If the problem persists and want to '
            'resolve asap, - contribute to the project. /help'
        )
