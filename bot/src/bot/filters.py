import typing
from re import compile

from aiogram.dispatcher.filters import BoundFilter
from aiogram import types

from bot.misc import dp
from config.settings import settings

re_question_mark = compile(r'\?')
# TODO: to arg of a filter.
# TODO: deprecate use of the bot username
re_bot_mentioned = compile(r'@' + settings.TG_BOT_USERNAME.lower())


def is_bot_mentioned(text):
    if not text:
        return False
    return re_bot_mentioned.search(text.lower())


def _is_replied_to_bot(message: types.Message):
    try:
        username = message.reply_to_message.from_user.username
    except AttributeError:
        return False
    return username == settings.TG_BOT_USERNAME


class IsForSuperadminRequestFilter(BoundFilter):
    """True only if superadmin requested with bot mentioning."""
    key = 'is_superadmin_request'

    def __init__(self, is_superadmin_request: typing.Iterable):
        self.superadmin_ids = is_superadmin_request

    async def check(self, message: types.Message):
        # Check for user id.
        if int(message.from_user.id) not in self.superadmin_ids:
            return False

        # Check if bot mentioned.
        return is_bot_mentioned(message.text)


class IsForOpenaiResponseChatsFilter(BoundFilter):
    """True if rather
    - chat id in a list,
    - text length > 350 symbols,
    - ends with ('...', '..', ':'),
    - with bot mentioned,
    - replied on a bot message,
    - text with question mark (?)
    """
    key = 'is_for_openai_response_chats'

    def __init__(
            self,
            is_for_openai_response_chats: typing.Union[typing.Iterable, int],
    ):
        if isinstance(is_for_openai_response_chats, int):
            is_for_openai_response_chats = [is_for_openai_response_chats]
        # TODO: rehardhcore.
        self.chat_id = is_for_openai_response_chats
        self.on_endswith = ('...', '..', ':')
        self.on_max_length = 350

    async def check(self, message: types.Message):
        # Check for chat id.
        if int(message.chat.id) not in self.chat_id:
            return False

        # Check for length.
        if self.on_max_length and len(message.text) > self.on_max_length:
            return True

        # Check for if on question_mark.
        text = message.text
        if re_question_mark.search(text):
            return True

        # Check if endswith
        if self.on_endswith and text.endswith(self.on_endswith):
            return True

        # Check if bot mentioned.
        if is_bot_mentioned(text):
            return True

        return _is_replied_to_bot(message)


dp.filters_factory.bind(IsForOpenaiResponseChatsFilter)
dp.filters_factory.bind(IsForSuperadminRequestFilter)
