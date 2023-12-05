import logging
from typing import Dict, Any

from aiogram import types, F, html, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.markdown import code

from bot.misc import bot_contributor_chat_storage, token_api_request_manager, dp
from bot.utils import cache_message_decorator
from config.settings import settings
from bot.handlers.commands import consts

logger = logging.getLogger(__name__)

# router = Router()


class AiTokenStates(StatesGroup):
    openai_token = State()
    chat_usernames = State()


BUTTON_CANCEL = KeyboardButton(text=consts.CANCEL)
BUTTON_ADD_OPENAI_TOKEN = KeyboardButton(text=consts.ADD_OPENAI_TOKEN)


@dp.message(Command(consts.ADD_OPENAI_TOKEN))
@cache_message_decorator
async def start_add_openai_token(message: types.Message, state: FSMContext):
    logger.info(f'User {message.from_user.username} want to save openai token...')
    await state.set_state(AiTokenStates.openai_token)
    return await message.answer(
        'Hi, the process consists of the next steps:\n\n'
        '1. You submit here your OpenAI token from https://platform.openai.com/api-keys\n'
        '2. You submit chat names to where you have already added this bot. '
        'Thus, you activate the OpenAI feature of the bot.\n'
        'n. You could revoke your token with command on demand.\n\n'
        f'To proceed - post your token, to stop here: {code("/cancel")}',
        reply_markup=ReplyKeyboardRemove(),
    )


def _not_valid_openai_token(value: str) -> bool:
    if len(value) != len(settings.OPENAI_TOKEN):
        return True
    return False


@dp.message(AiTokenStates.openai_token, F.args.func(_not_valid_openai_token))
@cache_message_decorator
async def process_wrong_token(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        text='You past wrong token, process cancelled. Probably try to start again.',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    BUTTON_ADD_OPENAI_TOKEN,
                    BUTTON_CANCEL,
                ]
            ],
            resize_keyboard=True,
        ),
    )


@dp.message(AiTokenStates.openai_token)
@cache_message_decorator
async def process_openai_token(message: types.Message, state: FSMContext):
    await state.update_data(openai_token=message.text)
    await state.set_state(AiTokenStates.chat_usernames)

    return await message.answer(
        f'Now specify comma separated chat usernames where you want to activate openAi features.\n'
        f'E.g. where you add @phdDog group chat and your private chat: '
        f"{html.quote(f'@phdDog,@{message.from_user.username}')}.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _remember_chat_usernames(user_id: int, chat_usernames: str, token: str, bot: Bot) -> list[str]:
    """It returns chat usernames those were parsed and assigned."""
    if not chat_usernames:
        return []
    chat_usernames_parsed = chat_usernames.strip().split(',')
    allowed_chat_usernames = set()
    for chat_username in chat_usernames_parsed:
        if not chat_username.startswith('@'):
            continue

        try:
            chat = await bot.get_chat(chat_username)
        except Exception as e:
            logger.warning(f'{user_id} tried to save {token} for {chat_usernames}, failed with {e}, pass...')
            continue

        chat_id = chat.id
        if not chat_id:
            continue

        if chat_username not in allowed_chat_usernames:
            await bot_contributor_chat_storage.set(user_id, chat_id, token)
        allowed_chat_usernames.add(chat_username)
    # Store contributor token as well.
    await token_api_request_manager.add_token(token)
    return list(allowed_chat_usernames)


async def _send_summary(message: types.Message, data: Dict[str, Any], success: bool = True) -> types.Message:
    chat_usernames = data.get('chat_usernames', ['<something unexpected>'])
    text = (
        f'Your token **** was set for the next chats, that bot have parsed'
        f' (where bot has been added, and chat usernames resolved into ids successfully):\n\n'
        f"{','.join(chat_usernames)}.\n"
        if success
        else 'Token has not set for the provided chat. Something went wrong. '
             'Submit an issue or even pull request: https://github.com/AlcibiadesCleinias/telegram-phd-bot'
    )
    return await message.answer(text=text, reply_markup=ReplyKeyboardRemove())


@dp.message(AiTokenStates.openai_token)
async def process_chat_ids(message: types.Message, state: FSMContext, bot: Bot):
    async with ChatActionSender.record_voice(bot=bot, chat_id=message.chat.id):
        chat_usernames_remembered = await _remember_chat_usernames(message.text, bot)
        data = await state.update_data(chat_usernames=chat_usernames_remembered)
        await state.clear()
        return await _send_summary(message=message, data=data)
