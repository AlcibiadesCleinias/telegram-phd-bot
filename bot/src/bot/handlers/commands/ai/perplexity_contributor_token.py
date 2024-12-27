import logging

from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.filters import private_chat_filter
from bot.handlers.commands.ai.base_contributor_token import BaseTokenContributor
from bot.handlers.commands.commands import CommandEnum
from bot.misc import perplexity_token_api_request_manager, dp, bot_ai_contributor_chat_storage, bot_chat_discussion_mode_storage
from bot.utils import cache_message_decorator, remember_chat_handler_decorator
from config.settings import settings

logger = logging.getLogger(__name__)

class PerplexityTokenContributorStates(StatesGroup):
    token = State()
    chat_ids = State()


class PerplexityTokenContributor(BaseTokenContributor):
    """Perplexity token contribution handler implementation."""
    
    def __init__(self):
        super().__init__(
            telegram_states=PerplexityTokenContributorStates,
            token_storage=bot_ai_contributor_chat_storage,
            token_api_request_manager=perplexity_token_api_request_manager,
            bot_chat_discussion_mode_storage=bot_chat_discussion_mode_storage,
            command_name=CommandEnum.add_perplexity_token.name,
            service_name="Perplexity",
            service_url="https://docs.perplexity.ai/guides/getting-started",
            trial_info=settings.PERPLEXITY_REFERAL_NOTES or "",
        )

    async def is_valid_token(self, token: str) -> bool:
        """Validate Perplexity token format."""
        # Perplexity tokens start with 'pplx-' and are 53 characters long

        logger.info(f'TODO: [is_valid_token perplexity] token: {token}')
        return (token.startswith('pplx-') and len(token) == 53) and len(token) < 1000

    async def store_token(self, user_id: int, chat_id: int, token: str):
        """Store Perplexity token for the given user and chat."""
        await self.token_storage.set_perplexity_token(user_id, chat_id, token)


perplexity_token_contributor = PerplexityTokenContributor()


@dp.message(Command(CommandEnum.add_perplexity_token.name), private_chat_filter)
@remember_chat_handler_decorator
@cache_message_decorator
async def start_add_perplexity_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await perplexity_token_contributor.start_token_contribution(message, state)


@dp.message(PerplexityTokenContributorStates.token, perplexity_token_contributor.IsNotValidTokenCase(perplexity_token_contributor.is_valid_token), private_chat_filter)
@cache_message_decorator
async def process_wrong_perplexity_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await perplexity_token_contributor.process_wrong_token(message, state)


@dp.message(PerplexityTokenContributorStates.token, private_chat_filter)
@cache_message_decorator
async def process_perplexity_token(message: types.Message, state: FSMContext, *args, **kwargs):
    return await perplexity_token_contributor.process_token(message, state)


@dp.message(PerplexityTokenContributorStates.chat_ids, private_chat_filter)
@cache_message_decorator
async def process_chat_ids(message: types.Message, state: FSMContext, bot, *args, **kwargs):
    return await perplexity_token_contributor.process_chat_ids(message, state) 