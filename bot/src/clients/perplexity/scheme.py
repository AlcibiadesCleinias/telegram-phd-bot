from enum import Enum
from typing import List

from pydantic import BaseModel, RootModel


class PerplexityRole(Enum):
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'


class PerplexityChatMessageOut(BaseModel):
    role: PerplexityRole
    content: str


class PerplexityChatChoiceOut(BaseModel):
    message: PerplexityChatMessageOut


class PerplexityChatChoicesOut(BaseModel):
    choices: list[PerplexityChatChoiceOut]
    citations: list[str]


class PerplexityChatMessageIn(BaseModel):
    role: str
    content: str


class PerplexityChatMessagesIn(RootModel):
    root: List[PerplexityChatMessageIn]
