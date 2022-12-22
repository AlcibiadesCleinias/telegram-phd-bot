import logging

from aiogram import types

from bot.misc import dp, openai_client
from bot.utils import is_groupchat_remembered_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)
_priority_chats_kwargs = {'chat_id': chat_id for chat_id in settings.PRIORITY_CHATS}


@dp.message_handler(**_priority_chats_kwargs)
@dp.message_handler(content_types=types.ContentType.TEXT)
@is_groupchat_remembered_handler_decorator
async def send_openai_response(message: types.Message):
    logger.info('Compose openai response...')
    openai_completion = await openai_client.get_completions(message.text)
    logger.info('Composed, got %s', openai_completion)
    choices = openai_completion.choices
    if not choices:
        logger.warning('No choices from OpenAI, send nothing...')
        return await message.answer('A?')

    # Choose first & send.
    await message.answer(choices[0].text)
