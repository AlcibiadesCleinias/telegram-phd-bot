import logging

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.filters import private_chat_filter
from bot.handlers.commands.ai.base_contributor_token import BaseTokenContributor
from bot.handlers.commands.commands import CommandEnum
from bot.misc import bot_ai_contributor_chat_storage, openai_token_api_request_manager, dp, bot_chat_discussion_mode_storage
from bot.utils import cache_message_decorator, remember_chat_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)

class OpenAITokenContributorStates(StatesGroup):
    token = State()
    chat_ids = State()


class OpenAITokenContributor(BaseTokenContributor):
    """OpenAI token contribution handler implementation."""
    
    def __init__(self):
        super().__init__(
            telegram_states=OpenAITokenContributorStates,
            token_storage=bot_ai_contributor_chat_storage,
            token_api_request_manager=openai_token_api_request_manager,
            bot_chat_discussion_mode_storage=bot_chat_discussion_mode_storage,
            command_name=CommandEnum.add_openai_token.name,
            service_name="ChatGPT",
            service_url="https://platform.openai.com/api-keys",
            trial_info="On fresh register you could get 3-10 trial USD",
        )

    async def is_valid_token(self, token: str) -> bool:
        """Validate OpenAI token format."""
        # OpenAI tokens are either 51 characters long (old format)
        # or 164 characters long (new format starting with sk-...)
        logger.info(f'TODO: [is_valid_token openai] token: {token}')
        return (len(token) in [51, 164] or token.startswith('sk-')) and len(token) < 1000

    async def store_token(self, user_id: int, chat_id: int, token: str):
        """Store OpenAI token for the given user and chat."""
        await self.token_storage.set_openai_token(user_id, chat_id, token)


openai_token_contributor = OpenAITokenContributor()


@dp.message(Command(CommandEnum.add_openai_token.name), private_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def start_add_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await openai_token_contributor.start_token_contribution(message, state)


@dp.message(OpenAITokenContributorStates.token, openai_token_contributor.IsNotValidTokenCase(openai_token_contributor.is_valid_token), private_chat_filter)
@cache_message_decorator
async def process_wrong_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await openai_token_contributor.process_wrong_token(message, state)


@dp.message(OpenAITokenContributorStates.token, private_chat_filter)
@cache_message_decorator
async def process_openai_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await openai_token_contributor.process_token(message, state)


@dp.message(OpenAITokenContributorStates.chat_ids, private_chat_filter)
@cache_message_decorator
async def process_chat_ids(message: types.Message, state: FSMContext, bot, *args, **kwargs):
    return await openai_token_contributor.process_chat_ids(message, state)
