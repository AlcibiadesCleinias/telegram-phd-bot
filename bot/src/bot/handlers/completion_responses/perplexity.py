import logging
import re

from aiogram import types

from bot.handlers.completion_responses.utils import get_raw_dialog_messages
from bot.misc import bot_chat_messages_cache, perplexity_client_priority
from bot.utils import safety_replay_with_long_text
from clients.perplexity.client import PerplexityClient
from clients.perplexity.scheme import PerplexityChatMessageIn, PerplexityRole
from config.settings import settings
from utils.redis.redis_storage import BotChatMessagesCache

logger = logging.getLogger(__name__)

PERPLEXITY_MESSAGE_PREFIX = 'Dear'
PERPLEXITY_MESSAGE_SUFFIX = 'Sincerely,'
PERPLEXITY_MESSAGE_FORMAT = f'{PERPLEXITY_MESSAGE_PREFIX} @{{name}},\n\n{{content}}\n\n{PERPLEXITY_MESSAGE_SUFFIX}\n{settings.TG_BOT_USERNAME}'

PERPLEXITY_MESSAGE_PREFIX_PATTERN = re.compile(f'^{PERPLEXITY_MESSAGE_PREFIX} .*,\n\n')
PERPLEXITY_MESSAGE_SUFFIX_PATTERN = re.compile(f'{PERPLEXITY_MESSAGE_SUFFIX}\n{settings.TG_BOT_USERNAME}$')

def _format_to_perplexity_response(replay_to_message: types.Message, response_text: str) -> str:
    address_name = f'{replay_to_message.from_user.username}' if replay_to_message.from_user and replay_to_message.from_user.username else 'collegue'
    return PERPLEXITY_MESSAGE_FORMAT.format(name=address_name, content=response_text)

def _try_to_remove_perplexity_format(message: str) -> str:
    """To remove perplexity format from the cached message. We do not need it in the context."""
    message = PERPLEXITY_MESSAGE_PREFIX_PATTERN.sub('', message)
    message = PERPLEXITY_MESSAGE_SUFFIX_PATTERN.sub('', message)
    return message


def _convert_to_chat_messages(raw_messages: list[BotChatMessagesCache.MessageData]) -> list[PerplexityChatMessageIn]:
    """Converts raw cached messages to ChatMessage format and clean from perplexity format."""
    return [
        PerplexityChatMessageIn(
            role=(PerplexityRole.USER.value if msg.sender != settings.TG_BOT_USERNAME
                  else perplexity_client_priority.DEFAULT_CHAT_BOT_ROLE),
            content=_try_to_remove_perplexity_format(msg.text),
        )
        for msg in raw_messages
    ]

async def _get_dialog_messages_context(message_obj: types.Message, depth: int = 2) -> list[PerplexityChatMessageIn]:
    """According to https://docs.aiogram.dev it could not handle depth more than 1.
    thus, message should be cached for depth more than 1.
    """
    raw_messages = await get_raw_dialog_messages(bot_chat_messages_cache, message_obj, depth)
    return _convert_to_chat_messages(raw_messages)


async def send_perplexity_response(message: types.Message, perplexity_client: PerplexityClient):
    """Prepare a special perplexity styled response with citations for the provided context.
    It is based on context existence.
    """
    context_messages = await _get_dialog_messages_context(message, settings.PERPLEXITY_DIALOG_CONTEXT_MAX_DEPTH)
    logger.info(
        '[_send_perplexity_response] Request chatGPT for context: %s and message %s...', context_messages, message)
    context_messages.append(
        PerplexityChatMessageIn(
            role=PerplexityRole.USER.value,
            content=message.text,
        )
    )
    response_text, citations = await perplexity_client.get_chat_completions(context_messages, settings.PERPLEXITY_CHAT_BOT_GOAL)
    citations = '\n'.join([f'{i+1}. {citation}' for i, citation in enumerate(citations)]) if citations else ''

    response= f'{response_text}\n\nUsed sources:\n{citations}'

    if not response:
        response = '.'

    response = _format_to_perplexity_response(message, response)
    return await safety_replay_with_long_text(message, response, parse_mode='Markdown')
