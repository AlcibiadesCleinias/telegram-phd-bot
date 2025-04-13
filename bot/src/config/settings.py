from typing import Optional, List

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = 'INFO'

    TG_BOT_TOKEN: str = 'foo'
    # TODO: deprecate, use from bot if needed.
    TG_BOT_USERNAME: str = 'foo'
    TG_BOT_CACHE_TTL: int = 60 * 10
    TG_BOT_MAX_TEXT_SYMBOLS: int = 4095  # Instead of 4096.

    TG_BOT_PHD_WORK_TASK_CRON: str = '0 0 * * *'
    TG_PHD_WORK_STICKER_ID: str = 'CAACAgIAAx0CVNcIDQACCuZgL5xCvCo0DEWdMrU7Kh5KGDjLpAACMQAD2GoWEJWGojH6my_MHgQ'
    TG_PHD_WORK_EXCLUDE_CHATS: Optional[List[int]]
    PRIORITY_CHATS: Optional[List[int]]

    TG_SUPERADMIN_IDS: List[int]

    OPENAI_TOKEN: str = 'foo'
    OPENAI_DIALOG_CONTEXT_MAX_DEPTH: int = 2
    OPENAI_REFERAL_NOTES: Optional[str]

    PERPLEXITY_TOKEN: str = 'foo'
    PERPLEXITY_DIALOG_CONTEXT_MAX_DEPTH: int = 2
    PERPLEXITY_OPENAI_MODEL: str = 'llama-3.1-sonar-small-128k-online'
    PERPLEXITY_REFERAL_NOTES: Optional[str]
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379

    FERNET_KEY: bytes = b'FqkTMgwtDBM2yiKLCebObslxRBr-WuUiJoXWmCWgOgg='

    # To log errors directly to telegram.
    TG_ERROR_LOGGING_CHAT_ID: Optional[int] = None  # Chat ID for error logging
    TG_ERROR_LOGGING_BOT_TOKEN: Optional[str] = None

    @property
    def OPENAI_CHAT_BOT_GOAL(self) -> str:
        return (f'You are a helpful assistant in a Telegram chat. '
                f'When users mention you using @{self.TG_BOT_USERNAME}, they are addressing you directly. '
                f'You should provide helpful and informative responses.')
    
    @property
    def PERPLEXITY_CHAT_BOT_GOAL(self) -> str:
        return (f'You are a helpful assistant in a Telegram chat. '
                f'When users mention you using @{self.TG_BOT_USERNAME}, they are addressing you directly. '
                f'You should provide helpful and informative responses.')

    class Config:
        case_sensitive = True


settings = Settings()
