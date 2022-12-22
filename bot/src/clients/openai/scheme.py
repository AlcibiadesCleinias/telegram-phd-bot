from pydantic import BaseModel


class OpenAIChoices(BaseModel):
    text: str


class OpenAICompletion(BaseModel):
    choices: list[OpenAIChoices]
