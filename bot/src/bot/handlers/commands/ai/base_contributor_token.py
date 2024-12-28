from abc import ABC, abstractmethod
import logging
from typing import Callable, Optional, Type

from aiogram import types, html
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestChat, KeyboardButtonRequestUser
from aiogram.utils.markdown import hitalic, hbold

from bot.filters import private_chat_filter
from bot.handlers.commands.commands import CommandEnum
from bot.consts import AIDiscussionMode
from utils.redis.discussion_mode_storage import BotChatAIDiscussionModeStorage
from utils.redis.redis_storage import BotAIContributorChatStorage
from utils.token_api_request_manager import TokenApiRequestManager
from bot.utils import cache_message_decorator, remember_chat_handler_decorator

logger = logging.getLogger(__name__)

BUTTON_CANCEL = KeyboardButton(text=CommandEnum.cancel.tg_command)


class BaseTokenContributor(ABC):
    """Base class for token contribution handlers."""
    
    def __init__(
        self,
        telegram_states: StatesGroup,
        token_storage: BotAIContributorChatStorage,
        token_api_request_manager: TokenApiRequestManager,
        bot_chat_discussion_mode_storage: BotChatAIDiscussionModeStorage,
        command_name: str,
        service_name: str,
        service_url: str,
        trial_info: str = "",
    ):
        self.bot_chat_discussion_mode_storage = bot_chat_discussion_mode_storage
        self.telegram_states = telegram_states
        self.token_storage = token_storage
        self.token_api_request_manager = token_api_request_manager
        self.command_name = command_name
        self.service_name = service_name
        self.service_url = service_url
        self.trial_info = trial_info

    @abstractmethod
    async def is_valid_token(self, token: str) -> bool:
        """Validate the token format and potentially test it."""
        pass

    @abstractmethod
    async def store_token(self, user_id: int, chat_id: int, token: str):
        """Store the token for the given user and chat."""
        pass

    async def get_token_instructions(self) -> str:
        """Get the instructions for token submission."""
        base_text = (
            f'Hi, to activate {self.service_name} assistant for your chats and messages you follow the process. '
            'It consists of the next steps:\n\n'
            f'1. [!you are here!] You submit below your {self.service_name} token from {self.service_url}\n'
        )
        
        if self.trial_info:
            base_text += f'{hitalic(self.trial_info)}\n\n'
            
        base_text += (
            f'2. You submit list of Chat ID`s to where {hbold("you have already added this bot.")}'
            ' Thus, you will activate the feature of the bot for the provided chats for yourself.\n\n'
            'n. You could revoke your token with TODO command on demand, or merely revoke from the {self.service_name} API settings.\n\n'
            f'To proceed: {hbold(f"post your {self.service_name} token/key below")}\n'
            f'To stop here: /cancel\n'
            f'To read more about: check <a href="https://github.com/AlcibiadesCleinias/telegram-phd-bot">source code</a>'
        )
        return base_text

    class IsNotValidTokenCase(Filter):
        def __init__(self, _is_token_valid_method_async: Callable[[str], bool]):
            self._is_token_valid_method_async = _is_token_valid_method_async

        async def __call__(self, message: types.Message):
            if not message.text:
                return True
            if message.text.lower() == 'cancel':
                return True
            if not await self._is_token_valid_method_async(message.text):
                return True
            return False

    async def start_token_contribution(self, message: types.Message, state: FSMContext):
        """Start the token contribution process."""
        logger.info(f'User {message.from_user.username} want to save {self.service_name} token...')
        await state.set_state(self.telegram_states.token)
        return await message.answer(
            await self.get_token_instructions(),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )

    async def process_wrong_token(self, message: types.Message, state: FSMContext):
        """Handle invalid token submission."""
        await state.clear()
        return await message.answer(
            text=f'You past wrong token, process cancelled. Probably try to start again.',
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text=f"/{self.command_name}"),
                        BUTTON_CANCEL,
                    ]
                ],
                resize_keyboard=True,
            ),
        )

    async def process_token(self, message: types.Message, state: FSMContext):
        """Process valid token submission."""
        if not await self.is_valid_token(message.text):
            return await self.process_wrong_token(message, state)

        await state.update_data(token=message.text)
        await state.set_state(self.telegram_states.chat_ids)
        chat_id_with_current_user = str(message.from_user.id)

        return await message.answer(
            f'Now specify comma separated **chat id**...\n\n'
            f'Note, to get {hbold("Chat Id")} you could use the bot command in the target chat: '
            f'{CommandEnum.show_chat_id.tg_command}\n\n'
            f'Example below is where 2 {hbold("Chat Ids")} specified (**the first one is this private chat id**):\n'
            f"{hbold(f'{chat_id_with_current_user},-999someRandomChatID888')}.\n\n"
            f'Now, {hbold("specify chat ids")} by yourself or use via suggested buttons from the screen.',
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text=chat_id_with_current_user),
                        KeyboardButton(
                            text='Choose group chat',
                            request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=False),
                        ),
                        KeyboardButton(
                            text='Choose channel',
                            request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=True),
                        ),
                        KeyboardButton(
                            text='Choose user chat',
                            request_user=KeyboardButtonRequestUser(request_id=3, user_is_bot=False),
                        ),
                        BUTTON_CANCEL,
                    ]
                ],
                resize_keyboard=True,
            ),
            parse_mode="HTML",
        )

    async def _parse_and_remember_chat_ids(self, user_id: int, unparsed_ids: str, token: str) -> list[int]:
        """Parse and store chat IDs."""
        if not unparsed_ids:
            return []
        chat_ids_parsed = unparsed_ids.strip().split(',')
        allowed_chat_ids = set()
        for chat_id in chat_ids_parsed:
            try:
                chat_id = int(chat_id)
            except Exception as e:
                logger.warning(f'[_parse_and_remember_chat_ids] {user_id} tried to save token for {chat_id}, failed with error: {e}, pass...')
                continue

            if not chat_id:
                continue

            if chat_id not in allowed_chat_ids:
                await self.store_token(user_id, chat_id, token)
            allowed_chat_ids.add(chat_id)

        # Store contributor token for priority chats.
        await self.token_api_request_manager.add_token(token, str(user_id))

        return list(allowed_chat_ids)

    async def process_chat_ids(self, message: types.Message, state: FSMContext):
        """Process chat IDs submission."""
        data = await state.get_data()
        
        # Parse if info shared through internal tg methods.
        if message.user_shared:
            shared_ids = str(message.user_shared.user_id)
        elif message.chat_shared:
            shared_ids = str(message.chat_shared.chat_id)
        else:
            shared_ids = message.text

        # Parse and remember chat id's.
        chat_ids_remembered = await self._parse_and_remember_chat_ids(
            message.from_user.id, shared_ids, data.get('token')
        )
        await state.clear()
        return await self._send_summary(message=message, chat_ids=chat_ids_remembered)

    async def _send_summary(self, message: types.Message, chat_ids: list[int], success: bool = True) -> types.Message:
        """Send summary of the token contribution process."""

        current_ai_discussion_mode = await self.bot_chat_discussion_mode_storage.get_discussion_mode_by_contributor(message.chat.id, message.from_user.id)
        is_mention_only_mode = await self.bot_chat_discussion_mode_storage.get_is_mention_only_mode_by_contributor(message.chat.id, message.from_user.id)

        current_ai_discussion_mode_str = f'\n\nCurrent AI discussion mode: {html.bold(current_ai_discussion_mode.get_mode_name() if current_ai_discussion_mode is not None else AIDiscussionMode.OPENAI.get_mode_name())}. To change {CommandEnum.switch_mention_only_mode.tg_command}'
        is_mention_only_mode_str = f'\nCurrent mention only mode: {html.bold("enabled" if is_mention_only_mode else "disabled")}. To change {CommandEnum.switch_mention_only_mode.tg_command}'
        text = (
            f'Your {self.service_name} token was set for the chats that bot have parsed'
            f' (where bot has been added, and chat ids resolved successfully):\n\n'
            f'{",".join(map(str, chat_ids))}.'
            f'{current_ai_discussion_mode_str}'
            f'{is_mention_only_mode_str}'
            if success
            else f'Token has not set for the provided chat. Something went wrong. '
                 'Submit an issue or even pull request: https://github.com/AlcibiadesCleinias/telegram-phd-bot'
        )
        return await message.answer(text=text, reply_markup=ReplyKeyboardRemove()) 