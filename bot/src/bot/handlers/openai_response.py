import logging

from aiogram import types

from bot.misc import dp, openai_client
from bot.utils import is_groupchat_remembered_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)


@dp.message_handler(chat_id=settings.PRIORITY_CHATS, content_types=types.ContentType.TEXT)
@is_groupchat_remembered_handler_decorator
async def send_openai_response(message: types.Message):
    logger.info('Compose openai response for %s...', message)
    openai_completion = await openai_client.get_completions(message.text)
    logger.info('Composed, got %s', openai_completion)
    choices = openai_completion.choices
    if not choices:
        logger.warning('No choices from OpenAI, send nothing...')
        return await message.reply('A?')

    # Choose first & send.
    await message.reply(choices[0].text)
