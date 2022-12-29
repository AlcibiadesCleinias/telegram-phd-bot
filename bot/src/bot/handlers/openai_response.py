import logging

from aiogram import types

from bot.misc import dp, openai_client, bot_chat_messages_cache
from bot.utils import is_groupchat_remembered_handler_decorator, cache_message_text_decorator
from config.settings import settings

logger = logging.getLogger(__name__)


async def _get_message_context(message_obj: types.Message, depth: int = 2) -> str:
    """According to https://docs.aiogram.dev it could not handle depth more than 1.
    thus, message should be cached for depth more than 1.
    """
    context = ''
    chat_id = message_obj.chat.id
    replay_to_id = message_obj.message_id
    for _ in range(depth):
        # Get message replied on if exist.
        replay_to_id = await bot_chat_messages_cache.get_replay_to(chat_id, replay_to_id)
        if not replay_to_id:
            break
        previous_replay = await bot_chat_messages_cache.get_text(chat_id, replay_to_id)
        if previous_replay:
            context = f'{previous_replay}\n{context}'
    return context


async def _compose_openapi_completion(context: str, message: str):
    message = f'{context}\n{message}'

    openai_completion = await openai_client.get_completions(message)
    choices = openai_completion.choices
    if not choices:
        logger.warning('No choices from OpenAI, send nothing...')
        return 'A?'

    logger.debug('Choose first completion %s in & send.', openai_completion)
    return choices[0].text


@dp.message_handler(
    for_openai_response_chats=settings.PRIORITY_CHATS,
)
@is_groupchat_remembered_handler_decorator
@cache_message_text_decorator
async def send_openai_response(message: types.Message):
    context = await _get_message_context(message)
    logger.info('Compose openai response for context: %s and message %s...', context, message)
    composed = await _compose_openapi_completion(context, message.text)
    await message.reply(composed)
