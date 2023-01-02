import logging

from aiogram import types

from bot.misc import dp, openai_client, bot_chat_messages_cache
from bot.utils import is_groupchat_remembered_handler_decorator, cache_message_decorator
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

    # OpenAI could not return more than COMPLETION_MAX_LENGTH.
    # Otherwise you will receive
    # 'error': {'message': "This model's maximum context length is 4097 tokens,
    # however you requested 4121 tokens (121 in your prompt; 4000 for the completion).
    # Please reduce your prompt; or completion length.",
    # 'type': 'invalid_request_error', 'param': None, 'code': None}
    message_length = len(message)
    completion_length = openai_client.COMPLETION_MAX_LENGTH - message_length
    if completion_length <= 0:
        # Hard text reduce.
        message = message[:message_length // 3]

    openai_completion = await openai_client.get_completions(message, completion_length)
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
@cache_message_decorator
async def send_openai_response(message: types.Message):
    context = await _get_message_context(message)
    logger.info('Compose openai response for context: %s and message %s...', context, message)
    composed = await _compose_openapi_completion(context, message.text)
    await message.reply(composed)
