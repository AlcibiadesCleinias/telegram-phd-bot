import logging

from aiogram import types, html, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestChat
from aiogram.types.keyboard_button_request_user import KeyboardButtonRequestUser
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
        f'To proceed - firstly, {hbold("post your OpenAI token/key below")}.\n'
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
    chat_id_with_current_user = str(message.from_user.id)

    return await message.answer(
        f'Now specify comma separated **chat id**...\n\n'
        f'Note, to get {html.bold("Chat Id")} you could use the bot command in the target chat: '
        f'{CommandEnum.show_chat_id.tg_command}\n\n'
        f'Example below is where 2 {html.bold("Chat Ids")} specified (**the first one is this private chat id**):\n'
        f"{html.code(f'{chat_id_with_current_user},-999someRandomChatID888')}.\n\n"
        f'Now, {html.bold("specify chat ids")} by yourself or use via suggested buttons from the screen.',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=chat_id_with_current_user),
                    KeyboardButton(
                        text='Share group chat',
                        request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=False),
                    ),
                    KeyboardButton(
                        text='Share channel',
                        request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=True),
                    ),
                    KeyboardButton(
                        text='Share user chat',
                        request_user=KeyboardButtonRequestUser(request_id=3, user_is_bot=False),
                    ),
                    BUTTON_CANCEL,
                ]
            ],
            resize_keyboard=True,
        ),
    )


async def _parse_and_remember_chat_ids(user_id: int, unparsed_ids: str, token: str, bot: Bot) -> list[int]:
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

        # Store chat_id and token for that user.
        if chat_id not in allowed_chat_ids:
            await bot_contributor_chat_storage.set(user_id, chat_id, token)
        allowed_chat_ids.add(chat_id)
    # Store contributor token as well to use in token_api_request_manager for priority chats.
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
    # Just a fake for 2 sec.
    async with ChatActionSender.record_voice(bot=bot, chat_id=message.chat.id, initial_sleep=2):
        data = await state.get_data()
        # Parse if info shared through internal tg methods.
        if message.user_shared:
            shared_ids = str(message.user_shared.user_id)
        elif message.chat_shared:
            shared_ids = str(message.chat_shared.chat_id)
        else:
            shared_ids = message.text
        # Parse and remember chat id`s.
        chat_ids_remembered = await _parse_and_remember_chat_ids(
            message.from_user.id, shared_ids, data.get('openai_token'), bot,
        )
        data['chat_ids'] = chat_ids_remembered
        await state.clear()
        return await _send_summary(message=message, chat_ids=chat_ids_remembered, success=True)
