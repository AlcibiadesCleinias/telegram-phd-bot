import logging

from aiogram import types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

from bot.misc import dp
from bot.utils import cache_message_decorator

logger = logging.getLogger(__name__)


class AiTokenStates(StatesGroup):
    sentToken = State()
    like_bots = State()
    language = State()


@dp.message_handler(
    commands=['add_openai_token'],
    help='You could provide your OpenAI token (key) and get chatGPT support from this bot to the preferred chats.'
         ' This token you could create here: https://platform.openai.com/api-keys',
)
@cache_message_decorator
async def add_token(message: types.Message):
    logger.info(f'User {message.from_user.username} want to save openai token...')
    await AiTokenStates.name.set()
    await message.answer(
        'Hi, the process consists of the next steps:\n\n'
        '1. You submit your OpenAI token (https://platform.openai.com/api-keys)\n'
        '2. You submit chat names where you have already add this bot',
        reply_markup=ReplyKeyboardRemove(),
    )
