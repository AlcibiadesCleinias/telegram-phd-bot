from typing import Optional, List

from pydantic import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = 'INFO'

    TG_BOT_TOKEN: str
    # TODO: deprecate, use from bot if needed.
    TG_BOT_USERNAME: str = 'foo'
    TG_BOT_SKIP_UPDATES: bool = True

    TG_BOT_PHD_WORK_TASK_CRON: str = '0 0 * * *'
    TG_PHD_WORK_STICKER_ID: str = 'CAACAgIAAx0CVNcIDQACCuZgL5xCvCo0DEWdMrU7Kh5KGDjLpAACMQAD2GoWEJWGojH6my_MHgQ'
    TG_PHD_WORK_EXCLUDE_CHATS: Optional[List[str]]
    PRIORITY_CHATS: Optional[List[str]]

    OPENAI_TOKEN: str = 'foo'

    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379

    class Config:
        case_sensitive = True


settings = Settings()
