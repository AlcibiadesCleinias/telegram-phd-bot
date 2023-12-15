from enum import Enum
from functools import reduce


class CommandABC(Enum):
    @property
    def tg_command(self):
        return '/' + self.name

    @classmethod
    def get_all_commands_json(cls):
        """For the await bot.set_my_commands(...).
        "commands": [
            {
              "command": "start",
              "description": "Start using bot"
            },...
        ]
        """
        return [{'command': i.name, 'description': i.value} for i in cls]

    @classmethod
    def pretty_print_all(cls) -> str:
        command_to_description = [f'{i.tg_command}: {i.value}\n' for i in cls]
        return reduce(lambda text, x: text + x, command_to_description)


class CommandEnum(CommandABC):
    help = 'Show the bot help message.'
    add_openai_token = (
        'Submit your OpenAI token/key and specify chats to run your own Phd ChatGPT assistant for those chats.'
    )
    cancel = 'Cancel whatever you do.'
    show_chat_id = 'With help of PhD degree it shows current chat id.'
    show_openai_triggers = 'Get info about openAI triggers.'
    show_admin_commands = 'Get all admin commands list.'


class CommandAdminEnum(CommandABC):
    show_chat_stats = 'Show stats of using in chats.'
    show_openai_token_stats = 'Show stats of added OpenAI tokens.'
