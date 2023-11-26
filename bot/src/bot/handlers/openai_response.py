import logging

from aiogram import types

from bot.misc import dp, openai_client, bot_chat_messages_cache
from bot.utils import remember_groupchat_handler_decorator, cache_message_decorator, cache_bot_messages
from clients.openai.client import ExceptionMaxTokenExceeded
from clients.openai.scheme import ChatMessage
from config.settings import settings

logger = logging.getLogger(__name__)

# TODO: how openai compute token number?
_OPENAI_COMPLETION_LENGTH_ROBUST = int(
    openai_client.COMPLETION_MAX_LENGTH - openai_client.COMPLETION_MAX_LENGTH // 1e3
)


# The same filters for chats and channels.
_superadmin_filters = {'is_superadmin_request': settings.TG_SUPERADMIN_IDS}
_filters = {'is_for_openai_response_chats': settings.PRIORITY_CHATS}


async def _get_dialog_messages_context(message_obj: types.Message, depth: int = 2) -> [ChatMessage]:
    """According to https://docs.aiogram.dev it could not handle depth more than 1.
    thus, message should be cached for depth more than 1.
    """
    logger.info('todo: compose dialog')
    chat_id = message_obj.chat.id
    replay_to_id = message_obj.reply_to_message.message_id if message_obj.reply_to_message else None

    logger.info(f'replay_to_id: {replay_to_id}')

    chat_messages = []
    # Compose from last one message to 1st one. Thus, I should revert list at the end.
    while replay_to_id and depth > 0:
        # Get message replied on if exist.
        previous_message = await bot_chat_messages_cache.get_message(chat_id, replay_to_id)
        logger.info(f'[_get_dialog_messages_context] Previous_message: {previous_message}')
        if previous_message:
            chat_messages.append(ChatMessage(
                role=(
                    'user' if previous_message.sender != settings.TG_BOT_USERNAME
                    else openai_client.DEFAULT_CHAT_BOT_ROLE
                ),
                content=previous_message.text
            ))

        replay_to_id = previous_message.replay_to
        depth -= 1

    return chat_messages[::-1]


async def _compose_openapi_completion(message: str):
    message = f'{message}'

    # OpenAI could not return more than COMPLETION_MAX_LENGTH.
    # Otherwise you will receive
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
    except ExceptionMaxTokenExceeded:
        # According to https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them#
        # :~:text=Token%20Limits,shared%20between%20prompt%20and%20completion.
        logger.info('Lets try with 2/3 of completion_length = %s', completion_length)
        openai_completion = await openai_client.get_completions(message, int(completion_length * 2/3))

    return openai_completion


@dp.message_handler(**_filters)
@dp.message_handler(**_superadmin_filters)
@dp.channel_post_handler(**_filters)
@dp.channel_post_handler(**_superadmin_filters)
@remember_groupchat_handler_decorator
@cache_message_decorator
async def send_openai_response(message: types.Message):
    """Rather use completion model or dialog.
    It is based on context existence.
    """
    context_messages = await _get_dialog_messages_context(message, settings.OPENAI_DIALOG_CONTEXT_MAX_DEPTH)
    # If context exists send it as a dialog.
    if not context_messages or len(context_messages) == 0:
        logger.info('[send_openai_response] Request completion for message %s...', message)
        response = await _compose_openapi_completion(message.text)
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
    sent = await message.reply(response)
    await cache_bot_messages(sent)
