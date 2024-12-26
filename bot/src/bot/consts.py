# TODO: relocate commands to here, kinda misc?
from enum import IntEnum

TEXT_LENGTH_TRIGGER = 350

OPENAI_GENERAL_TRIGGERS = f"""It triggered automatically for ChatGPT feature when one of the condition is fulfilled:
- text length > {TEXT_LENGTH_TRIGGER} symbols,
- ends with ('...', '..', ':'),
- with bot mentioned via @,
- replied on a bot message,
- text consists of question mark (?)
"""

class DiscussionMode(IntEnum):
    OPENAI = 1
    PERPLEXITY = 2