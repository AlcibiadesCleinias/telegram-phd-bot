import logging

from aiogram import types

from bot.misc import dp, openai_client
from bot.utils import is_groupchat_remembered_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)


async def _compose_openapi_completion(previous_message: str, message: str):
    message = f'{previous_message}\n{message}'

    openai_completion = await openai_client.get_completions(message)
    logger.info('Composed, got %s', openai_completion)
    choices = openai_completion.choices
    if not choices:
        logger.warning('No choices from OpenAI, send nothing...')
        return 'A?'

    # Choose first & send.
    return choices[0].text


@dp.message_handler(
    for_openai_response_chats=settings.PRIORITY_CHATS,
)
@is_groupchat_remembered_handler_decorator
async def send_openai_response(message: types.Message):
    logger.info('Compose openai response for %s...', message)
    replied_on = ''
    # Check if replied.
    try:
        replied_on = message.reply_to_message.text
        print(message.reply_to_message.from_user.username)
    except AttributeError:
        pass

    composed = await _compose_openapi_completion(replied_on, message.text)
    await message.reply(composed)
