import logging

from aiogram import types, html, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.markdown import hitalic, hbold, link

from bot.filters import private_chat_filter
from bot.handlers.commands.commands import CommandEnum
from bot.misc import bot_contributor_chat_storage, token_api_request_manager, dp
from bot.utils import cache_message_decorator, remember_chat_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)

# router = Router()


class AiTokenStates(StatesGroup):
    openai_token = State()
    chat_ids = State()


BUTTON_CANCEL = KeyboardButton(text=CommandEnum.cancel.tg_command)
BUTTON_ADD_OPENAI_TOKEN = KeyboardButton(text=CommandEnum.add_openai_token.tg_command)


@dp.message(Command(CommandEnum.add_openai_token.name), private_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def start_add_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    logger.info(f'User {message.from_user.username} want to save openai token...')
    await state.set_state(AiTokenStates.openai_token)
    return await message.answer(
        'Hi, to activate ChatGPT PhD assistant for your chats and messages you follow the process. '
        'It consists of the next steps:\n\n'
        '1. You submit here your OpenAI token from https://platform.openai.com/api-keys\n'
        f'{hitalic("On fresh register you could get 3-10 trial USD")}\n\n'
        f'2. You submit chat id`s to where {hbold("you have already added this bot.")}'
        ' Thus, you will activate the OpenAI feature of the bot for the provided chats for yourself.\n\n'
        'n. You could revoke your token with command on demand.\n\n'
        f'To proceed - firstly, {hbold("post your OpenAI token/key")}.\n'
        f'To stop here: /cancel\n'
        f'To read more about: check {link("source code", "https://github.com/AlcibiadesCleinias/telegram-phd-bot")}',
        reply_markup=ReplyKeyboardRemove(),
    )


class _IsNotValidToken(Filter):
    async def __call__(self, message: types.Message):
        if len(message.text) != len(settings.OPENAI_TOKEN):
            return True
        return False


@dp.message(AiTokenStates.openai_token, _IsNotValidToken(), private_chat_filter)
@cache_message_decorator
async def process_wrong_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    await state.clear()
    return await message.answer(
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


@dp.message(AiTokenStates.openai_token, private_chat_filter)
@cache_message_decorator
async def process_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    await state.update_data(openai_token=message.text)
    await state.set_state(AiTokenStates.chat_ids)

    return await message.answer(
        f'Now specify comma separated **chat id**...\n\n'
        f'Note, to get chat id you could send command to the bot: {CommandEnum.show_chat_id.tg_command}\n\n'
        f'E.g. where you add 2 chats (starting with this private chat id):'
        f"{html.code(f'{message.from_user.id},-1001806712922someRandomChatID')}.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _remember_chat_ids(user_id: int, unparsed_ids: str, token: str, bot: Bot) -> list[int]:
    """It returns chat usernames those were parsed and assigned."""
    if not unparsed_ids:
        return []
    chat_ids_parsed = unparsed_ids.strip().split(',')
    allowed_chat_ids = set()
    for chat_id in chat_ids_parsed:
        try:
            chat_id = int(chat_id)
        except Exception as e:
            logger.warning(f'{user_id} tried to save {token} for {chat_id}, failed with {e}, pass...')
            continue

        if not chat_id:
            continue

        if chat_id not in allowed_chat_ids:
            await bot_contributor_chat_storage.set(user_id, chat_id, token)
        allowed_chat_ids.add(chat_id)
    # Store contributor token as well.
    await token_api_request_manager.add_token(token, str(user_id))
    return list(allowed_chat_ids)


async def _send_summary(message: types.Message, chat_ids: list[int], success: bool = True) -> types.Message:
    text = (
        f'Your token **** was set for the chats, that bot have parsed'
        f' (where bot has been added, and chat ids resolved successfully):\n\n'
        f"{','.join(map(str, chat_ids))}.\n\n"
        f'Now you could use ChatGPT PhD assistant with the next triggers: {CommandEnum.show_openai_triggers.tg_command}'
        if success
        else 'Token has not set for the provided chat. Something went wrong. '
             'Submit an issue or even pull request: https://github.com/AlcibiadesCleinias/telegram-phd-bot'
    )
    return await message.answer(text=text, reply_markup=ReplyKeyboardRemove())


@dp.message(AiTokenStates.chat_ids, private_chat_filter)
@cache_message_decorator
async def process_chat_ids(message: types.Message, state: FSMContext, bot: Bot, *args, **kwargs):
    logger.info('[process_chat_ids] Start recording audio...')
    async with ChatActionSender.record_voice(bot=bot, chat_id=message.chat.id):
        data = await state.get_data()
        chat_ids_remembered = await _remember_chat_ids(
            message.from_user.id, message.text, data.get('openai_token'), bot,
        )
        data['chat_ids'] = chat_ids_remembered
        await state.clear()
        return await _send_summary(message=message, chat_ids=chat_ids_remembered, success=True)
