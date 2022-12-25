import typing
from re import compile

from aiogram.dispatcher.filters import BoundFilter
from aiogram import types

from bot.misc import dp
from config.settings import settings

re_question_mark = compile(r'\?')
# TODO: to arg of a filter.
# TODO: deprecate use of the bot username
re_bot_mentioned = compile(r'@' + settings.TG_BOT_USERNAME)


def _is_replied_to_bot(message: types.Message):
    try:
        username = message.reply_to_message.from_user.username
    except AttributeError:
        return False
    return username == settings.TG_BOT_USERNAME


class IsForOpenaiResponseChatsFilter(BoundFilter):
    """True if rather
    - chat id in a list,
    - length > 100 symbols,
    - ends with ('...', '..', ':'),
    - with bot mentioned,
    - replied on a bot message,
    """
    key = 'for_openai_response_chats'

    def __init__(
            self,
            for_openai_response_chats: typing.Union[typing.Iterable, int],
    ):
        if isinstance(for_openai_response_chats, int):
            for_openai_response_chats = [for_openai_response_chats]
        # TODO: rehardhcore.
        self.chat_id = for_openai_response_chats
        self.on_endswith = ('...', '..', ':')
        self.on_max_length = 100

    async def check(self, message: types.Message):
        # Check for chat id.
        if int(message.chat.id) in self.chat_id:
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
        if re_bot_mentioned.search(text):
            return True

        return _is_replied_to_bot(message)


dp.filters_factory.bind(IsForOpenaiResponseChatsFilter)
