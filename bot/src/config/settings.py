from typing import Optional, List

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = 'INFO'

    TG_BOT_TOKEN: str = 'foo'
    # TODO: deprecate, use from bot if needed.
    TG_BOT_USERNAME: str = 'foo'
    TG_BOT_CACHE_TTL: int = 60 * 10

    TG_BOT_PHD_WORK_TASK_CRON: str = '0 0 * * *'
    TG_PHD_WORK_STICKER_ID: str = 'CAACAgIAAx0CVNcIDQACCuZgL5xCvCo0DEWdMrU7Kh5KGDjLpAACMQAD2GoWEJWGojH6my_MHgQ'
    TG_PHD_WORK_EXCLUDE_CHATS: Optional[List[int]]
    PRIORITY_CHATS: Optional[List[int]]

    TG_SUPERADMIN_IDS: List[int]

    OPENAI_TOKEN: str = 'foo'
    OPENAI_DIALOG_CONTEXT_MAX_DEPTH: int = 2
    OPENAI_CHAT_BOT_GOAL: str = 'You are a helpful assistant.'

    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379

    class Config:
        case_sensitive = True


settings = Settings()
