import logging

from aiogram import types

from bot.misc import openai_client_priority, bot_chat_messages_cache
from bot.handlers.completion_responses.utils import get_raw_dialog_messages
from utils.redis.redis_storage import BotChatMessagesCache
from bot.utils import remember_chat_handler_decorator, cache_message_decorator, safety_replay_with_long_text
from clients.openai.client import OpenAIMaxTokenExceededError, OpenAIClient, OpenAIInvalidRequestError
from clients.openai.scheme import ChatMessage
from config.settings import settings

logger = logging.getLogger(__name__)

# TODO: how openai compute token number?
_OPENAI_COMPLETION_LENGTH_ROBUST = int(
    openai_client_priority.COMPLETION_MAX_LENGTH - openai_client_priority.COMPLETION_MAX_LENGTH // 1e3
)



def _convert_to_chat_messages(raw_messages: list[BotChatMessagesCache.MessageData]) -> list[ChatMessage]:
    """Converts raw cached messages to ChatMessage format."""
    return [
        ChatMessage(
            role=('user' if msg.sender != settings.TG_BOT_USERNAME 
                  else openai_client_priority.DEFAULT_CHAT_BOT_ROLE),
            content=msg.text
        )
        for msg in raw_messages
    ]

async def _get_dialog_messages_context(message_obj: types.Message, depth: int = 2) -> list[ChatMessage]:
    """According to https://docs.aiogram.dev it could not handle depth more than 1.
    thus, message should be cached for depth more than 1.
    """
    raw_messages = await get_raw_dialog_messages(bot_chat_messages_cache, message_obj, depth)
    return _convert_to_chat_messages(raw_messages)


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


async def send_openai_response(message: types.Message, openai_client: OpenAIClient):
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
    return await safety_replay_with_long_text(message, response, cache_previous_batches=True)
