import logging

from bot.filters import IsImageRequestByContributorFilter, from_superadmin_filter
from bot.utils import remember_chat_handler_decorator, cache_message_decorator
from config.settings import settings

from aiogram import types, F
from aiogram.filters import Command
from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp, openai_client_priority, bot_openai_contributor_chat_storage
from clients.openai.client import OpenAIClient

logger = logging.getLogger(__name__)

DEFAULT_HELP_PHD_PROMPT = 'I want to generate a random MIPT PhD image for the article about dogs. Please help me.'

from_prioritised_chats_filter = F.chat.func(lambda chat: chat.id in settings.PRIORITY_CHATS)
_is_image_request_by_contributor_chat_filter = IsImageRequestByContributorFilter()
_generate_image_command = Command(CommandEnum.generate_image.name)


def _compose_response(revised_prompt: str, url: str):
    return f'OpenAI revised your prompt: "{revised_prompt}"\n\nAnd generated the following <a href="{url}">image</a>'


def _serialize_prompt(message: types.Message) -> (str, types.Message):
    """
    It returns prompt and message bot should to replay on.
    It chooses message or replay message text or caption, or use DEFAULT_HELP_PHD_PROMPT in the end.
    """
    # Possibly this command used on message replay.
    if message.reply_to_message is None:
        logger.info('[_serialize_prompt] It will generate image for on the replayed message...')
        message_with_prompt = message
        # Remove command mention from text.
        #  E.g. /generate_image@test_features_bot
        if message.text:
            text = (
                message.text
                .replace(CommandEnum.generate_image.tg_command, '')
                .replace(f'@{settings.TG_BOT_USERNAME}', '') if message.text else ''
            )
        elif message.caption:
            text = message.caption
        else:
            text = ''
    else:
        message_with_prompt = message.reply_to_message
        if message.reply_to_message.text:
            text = message.reply_to_message.text
        elif message.reply_to_message.caption:
            text = message.reply_to_message.caption
        else:
            text = ''

    if len(text) < 2:
        text = DEFAULT_HELP_PHD_PROMPT

    return text, message_with_prompt


async def _impl_replay_with_generated_image(
        text: str,
        message_with_prompt: types.Message,
        openai_client: OpenAIClient,
) -> types.Message:
    openai_response = await openai_client.get_generated_image(text)
    # Check if response composed, otherwise try 1 more time
    if openai_response.error:
        logger.warning('OpenAI response is None, try to get 1 more time with secure phrase from bot...')
        few_strings = text[:99] if len(text) > 100 else text
        openai_response = await openai_client.get_generated_image(
            'interpreter the following text for the scientific MIPT PhD student article work: ' + few_strings
        )
        if openai_response.error:
            return await message_with_prompt.reply(
                f'No success response from server, got: {openai_response.error}\n\n'
                f'PS. Possibly that means that profile can not use Dall-E based models, '
                f'and you need to top up your account for 5+ USD.'
            )
        return await message_with_prompt.reply(_compose_response(openai_response.revised_prompt, openai_response.url))
    return await message_with_prompt.reply(_compose_response(openai_response.revised_prompt, openai_response.url))


@dp.message(_generate_image_command, from_prioritised_chats_filter)
@dp.channel_post(_generate_image_command, from_prioritised_chats_filter)
@dp.message(_generate_image_command, from_superadmin_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_generated_image(message: types.Message, *args, **kwargs):
    logger.info(
        f'User {message.from_user.username if message.from_user else "UNKNOWN"} request image '
        f'generation on {message = } '
        f'with replayed message text {message.reply_to_message.text if message.reply_to_message else "NO_REPLAY"}...'
    )
    (text, message_with_prompt) = _serialize_prompt(message)
    return await _impl_replay_with_generated_image(text, message_with_prompt, openai_client_priority)


@dp.message(_generate_image_command, _is_image_request_by_contributor_chat_filter)
@dp.channel_post(_generate_image_command, _is_image_request_by_contributor_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def send_generated_image_for_contributor(message: types.Message, *args, **kwargs):
    tokens = await bot_openai_contributor_chat_storage.get(message.from_user.id, message.chat.id)
    logger.info(
        f'User {message.from_user.username} request image generation as for contributor {message = } '
        f'with replayed message text {message.reply_to_message.text if message.reply_to_message else ""}...'
    )
    (text, message_with_prompt) = _serialize_prompt(message)
    return await _impl_replay_with_generated_image(text, message_with_prompt, OpenAIClient(tokens.openai_token))
