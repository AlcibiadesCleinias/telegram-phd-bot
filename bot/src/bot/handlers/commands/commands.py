from enum import Enum


class CommandEnum(Enum):
    """For the await bot.set_my_commands(...).
    "commands": [
        {
          "command": "start",
          "description": "Start using bot"
        },...
    ]
    """
    help = 'Show the bot help message.'
    add_openai_token = 'Submit your openAI token to the specified chats to run assistant for the chats.'
    cancel = 'Cancel whatever you do.'
    show_chat_id = 'With help of PhD degree it shows current chat id.'
    show_openai_triggers = 'Get info about openAI triggers.'

    @property
    def tg_command(self):
        return '/' + self.name

    @classmethod
    def get_all_commands_json(cls):
        return [{'command': i.name, 'description': i.value} for i in cls]
