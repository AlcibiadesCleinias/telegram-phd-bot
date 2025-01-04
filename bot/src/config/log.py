import logging
from typing import List, Optional

from python_telegram_logging import AsyncTelegramHandler, ParseMode

from config.settings import settings

class TelegramHTMLFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as HTML with custom emojis."""
        level_colors = {"DEBUG": "⚪️", "INFO": "🔵", "WARNING": "🟡", "ERROR": "🔴", "CRITICAL": "⛔️"}
        level_emoji = level_colors.get(record.levelname, "⚪️")
        timestamp = self.formatTime(record, datefmt=self.datefmt)

        message = super().format(record)

        html_message = (
            f"{level_emoji} <b>{record.levelname}</b> <b>Telegram PhD Bot</b>" f"\n[{timestamp}]\n" 
            f"<code>{record.name}</code>\n" f"{message}"
        )
        if record.exc_info:
            html_message += f"\n\n<pre>{self.formatException(record.exc_info)}</pre>"

        return html_message


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging with both console and Telegram handlers.
    
    Args:
        level: Optional logging level to override the one from settings
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level or settings.LOG_LEVEL)
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            fmt='%(levelname)-8s | %(asctime)s | %(message)s | %(filename)+13s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    root_logger.addHandler(console_handler)
    
    # Telegram handler for error reporting.
    if settings.TG_ERROR_LOGGING_BOT_TOKEN and settings.TG_ERROR_LOGGING_CHAT_ID:
        telegram_handler = AsyncTelegramHandler(
            token=settings.TG_ERROR_LOGGING_BOT_TOKEN,
            chat_id=settings.TG_ERROR_LOGGING_CHAT_ID,
            parse_mode=ParseMode.HTML,
            level=logging.ERROR,
        )
        
        formatter = TelegramHTMLFormatter(datefmt='%d-%m-%Y %H:%M:%S %Z')
        telegram_handler.setFormatter(formatter, )
        root_logger.addHandler(telegram_handler)

    # # Set specific levels for some chatty libraries
    # logging.getLogger('aiogram').setLevel(logging.WARNING)
    # logging.getLogger('aiohttp').setLevel(logging.WARNING) 