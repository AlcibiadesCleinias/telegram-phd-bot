import logging

from bot.utils import remember_chat_handler_decorator, cache_message_decorator
from config.settings import settings

from aiogram import types, F
from aiogram.filters import Command
from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp, openai_client_priority

logger = logging.getLogger(__name__)

from_superadmin_filter = F.chat.func(lambda chat: chat.id in settings.TG_SUPERADMIN_IDS)
from_prioritised_chats_filter = F.chat.func(lambda chat: chat.id in settings.PRIORITY_CHATS)
_generate_image_command = Command(CommandEnum.generate_image.name)


def compose_response(revised_prompt: str, url: str):
    return f'API revised your prompt to: {revised_prompt}. Image url: {url}'


@dp.message(_generate_image_command, from_prioritised_chats_filter)
@dp.channel_post(_generate_image_command, from_prioritised_chats_filter)
@dp.message(_generate_image_command, from_superadmin_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def generate_image(message: types.Message, *args, **kwargs):
    logger.info(f'User {message.from_user.username} request image generation from...')

    # Possibly this command used on message replay.
    if message.reply_to_message is None:
        text = message.text[len(CommandEnum.generate_image.name) + 2:]  # +2 coz of / and space
    else:
        text = message.reply_to_message.text

    if len(text) < 2:
        text = 'I want to generate a random MIPT PhD image for the article about dogs. Please help me.'

    openai_response = await openai_client_priority.get_generated_image(text)
    # Check if response composed, otherwise try 1 more time
    if not openai_response:
        logger.warning('OpenAI response is None, try to get 1 more time with secure phrase from bot...')
        few_strings = text[:99] if len(text) > 100 else text
        openai_response = await openai_client_priority.get_generated_image(
            'interpreter the following text for the scientific MIPT PhD student article work: ' + few_strings
        )
        return await message.reply(compose_response(openai_response.revised_prompt, openai_response.url))
    return await message.reply(
        compose_response(openai_response.revised_prompt, openai_response.url)
    )
