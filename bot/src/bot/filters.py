import logging
import typing
from re import compile

from aiogram.filters import Filter
from aiogram import types, F

from bot.consts import OPENAI_GENERAL_TRIGGERS, TEXT_LENGTH_TRIGGER
from bot.misc import bot_ai_contributor_chat_storage, bot_chat_discussion_mode_storage
from config.settings import settings

re_question_mark = compile(r'\?')
# TODO: to arg of a filter.
# TODO: deprecate use of the bot username
re_bot_mentioned = compile(r'@' + settings.TG_BOT_USERNAME.lower())

logger = logging.getLogger(__name__)

from_superadmin_filter = F.from_user.id.in_(settings.TG_SUPERADMIN_IDS)
from_prioritised_chats_filter = F.chat.func(lambda chat: chat.id in settings.PRIORITY_CHATS)


def _is_bot_mentioned(text):
    if not text:
        return False
    return re_bot_mentioned.search(text.lower())


def _is_replied_to_bot(message: types.Message):
    try:
        username = message.reply_to_message.from_user.username
    except AttributeError:
        return False
    return username == settings.TG_BOT_USERNAME


def _is_interacted_with_bot(message: types.Message) -> bool:
    return _is_bot_mentioned(message.text) or _is_replied_to_bot(message)


class IsForSuperadminIteractedWithBotFilter(Filter):
    """True only if superadmin iteracted with bot."""

    def __init__(self, is_superadmin_request_with_trigger: typing.Iterable):
        self.superadmin_ids = is_superadmin_request_with_trigger

    async def __call__(self, message: types.Message) -> bool:
        # Check for user id.
        if message.from_user and message.from_user.id not in self.superadmin_ids:
            return False

        # Check if bot mentioned or replied to bot.
        return _is_interacted_with_bot(message)


class IsChatGptTriggerABCFilter(Filter):
    __doc__ = OPENAI_GENERAL_TRIGGERS
    text_length_trigger = TEXT_LENGTH_TRIGGER

    def __init__(self, *args, **kwargs):
        self.on_endswith = ('...', '..', ':')

    async def __call__(self, message: types.Message):
        # Check if text exists.
        if not message.text:
            return False

        # Check for length.
        if len(message.text) > self.text_length_trigger:
            return True

        # Check for if on question_mark.
        text = message.text
        if re_question_mark.search(text):
            return True

        # Check if endswith.
        if self.on_endswith and text.endswith(self.on_endswith):
            return True

        return False


class IsChatGptTriggerInPriorityChatFilter(IsChatGptTriggerABCFilter):
    """True if rather
    - chat id in a list,
    - IsChatGptTriggerABCFilter
    """

    def __init__(
            self,
            is_for_openai_response_chats: typing.Union[typing.Iterable, int],
            *args,
            **kwargs
    ):
        if isinstance(is_for_openai_response_chats, int):
            is_for_openai_response_chats = [is_for_openai_response_chats]
        self.chat_id = is_for_openai_response_chats
        super().__init__(*args, **kwargs)

    async def __call__(self, message: types.Message):
        # Check for chat id.
        if int(message.chat.id) not in self.chat_id:
            return False
        
        is_direct_iteration_only = await bot_chat_discussion_mode_storage.get_is_direct_iteration_only(message.chat.id)
        if is_direct_iteration_only:
            return _is_interacted_with_bot(message)
        
        return await super().__call__(message) or _is_interacted_with_bot(message)


async def _is_chat_stored_by_contributor(message: types.Message) -> bool:
    if not message.from_user or not message.from_user.id:
        return False

    tokens = await bot_ai_contributor_chat_storage.get(
        message.from_user.id, message.chat.id,
    )
    if not tokens.openai_token and not tokens.perplexity_token:
        return False
    return True


class IsChatGPTTriggerInContributorChatFilter(IsChatGptTriggerABCFilter):
    """True when token was supplied and linked to the chat and message send from contributor 
    & GPT trigger was used (from IsChatGptTriggerABCFilter).

    Note, that possibly you want to use contributor token if it is exists.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def __call__(self, message: types.Message):
        if not await _is_chat_stored_by_contributor(message):
            return False
        
        is_direct_iteration_only = await bot_chat_discussion_mode_storage.get_is_mention_only_mode_by_contributor(message.chat.id, message.from_user.id)
        if is_direct_iteration_only:
            return _is_interacted_with_bot(message)
        return await super().__call__(message) or _is_interacted_with_bot(message)


class IsFromOpenAIContributorInAllowedChatFilter(Filter):
    """This particular filter should be combined with other filters. It should check only openai token."""
    async def __call__(self, message: types.Message):
        if not message.from_user or not message.from_user.id:
            return False

        tokens = await bot_ai_contributor_chat_storage.get(
            message.from_user.id, message.chat.id,
        )
        if not tokens.openai_token:
            return False
        return True
    

class IsFromContributorInAllowedChatFilter(Filter):
    """Check if message from contributor and in allowed chat (by himself so)."""
    async def __call__(self, message: types.Message):
        return (await _is_chat_stored_by_contributor(message))


private_chat_filter = F.chat.func(lambda chat: chat.type == 'private')
