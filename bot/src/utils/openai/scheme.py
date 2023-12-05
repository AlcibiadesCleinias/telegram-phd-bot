from typing import List

from pydantic import BaseModel, RootModel


class OpenAIChoices(BaseModel):
    text: str


class OpenAICompletion(BaseModel):
    choices: list[OpenAIChoices]


class OpenAIChatMessage(BaseModel):
    role: str
    content: str


class OpenAIChatChoice(BaseModel):
    message: OpenAIChatMessage


class OpenAIChatChoices(BaseModel):
    choices: list[OpenAIChatChoice]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatMessages(RootModel):
    root: List[ChatMessage]
