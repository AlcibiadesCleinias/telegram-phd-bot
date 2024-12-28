import logging

from aiogram import types
from aiogram.enums import ChatType

from bot.misc import bot_chats_storage, bot_chat_messages_cache
from config.settings import settings
from utils.generators import batch

logger = logging.getLogger(__name__)

UNKNOWN_USER_ID = 0


# Deprecated.
def remember_groupchat_handler_decorator(func):
    """In order to find group chats where bot already exists."""
    async def wrapper(message: types.Message, *args, **kwargs):
        if not message.content_type == ChatType.PRIVATE:
            await bot_chats_storage.set_chat(message.chat.id)
        return await func(message, *args, **kwargs)
    return wrapper


def remember_chat_handler_decorator(func):
    """In order to find group chats where bot already exists."""
    async def wrapper(message: types.Message, *args, **kwargs):
        await bot_chats_storage.set_chat(message.chat.id)
        return await func(message, *args, **kwargs)
    return wrapper


async def cache_messages_text(messages: list[types.Message]) -> None:
    """Cache multiple messages efficiently using Redis pipeline.
    
    Args:
        messages: List of Telegram messages to cache
    """
    messages_data = []
    chat_ids = []
    message_ids = []
    
    for message in messages:
        if not message.text:
            continue
            
        message_replay_to = message.reply_to_message
        replay_to = message_replay_to.message_id if message_replay_to else None
        
        message_data = bot_chat_messages_cache.MessageData(
            sender=(
                message.from_user.username if message.from_user and message.from_user.username 
                else UNKNOWN_USER_ID
            ),
            replay_to=replay_to,
            text=message.text,
        )
        
        messages_data.append(message_data)
        chat_ids.append(message.chat.id)
        message_ids.append(message.message_id)
    
    if messages_data:
        await bot_chat_messages_cache.set_messages(
            chat_ids=chat_ids,
            message_ids=message_ids,
            messages=messages_data,
        )


async def cache_message_text(message: types.Message) -> None:
    """Cache single message text.
    
    Args:
        message: Telegram message to cache
    """
    await cache_messages_text([message])


def cache_message_decorator(func):
    """Cache both received and sent messages."""
    async def wrapper(message: types.Message, *args, **kwargs):
        messages_to_cache = [message]
        response = await func(message, *args, **kwargs)
        
        if response:
            messages_to_cache.append(response)
            
        await cache_messages_text(messages_to_cache)
        return response
    return wrapper


async def safety_replay_with_long_text(
        message_reply_to: types.Message, 
        text: str, 
        cache_previous_batches=False,
        parse_mode: str = None,
) -> types.Message:
    """Send message replies consisting of long text in several parts.
    Creates a chain of replies where each part replies to the previous one,
    except for the first message which replies to the original message.
    
    Args:
        message_reply_to: Original message to reply to
        text: Long text to be split and sent in parts
        cache_previous_batches: Whether to cache the sent messages
        parse_mode: Optional parse mode for message formatting
    
    Returns:
        The last sent message in the chain (already cached)
    """
    current_reply_to = message_reply_to
    messages_to_cache = []
    last_message = None
    
    for symbols in batch(text, settings.TG_BOT_MAX_TEXT_SYMBOLS - 1):
        last_message = await current_reply_to.reply(symbols, parse_mode=parse_mode)
        
        if cache_previous_batches:
            messages_to_cache.append(last_message)
            
        # Update the message to reply to for the next iteration
        current_reply_to = last_message
    
    # Cache all messages in a single operation if requested
    if cache_previous_batches and messages_to_cache:
        await cache_messages_text(messages_to_cache)
        
    return last_message
