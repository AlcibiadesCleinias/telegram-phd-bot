import asyncio

import aioredis
from aiogram import Bot, Dispatcher
from aiogram.utils.executor import Executor

from clients.openai.client import OpenAIClient
from config.settings import settings

# in code below it uses asyncio lock inside when creates connection pool
from utils.redis_storage import BotChatsStorage

redis = aioredis.from_url(f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}', db=0, decode_responses=True)
# storage = RedisStorage2(**REDIS_SETTINGS) if REDIS_SETTINGS else MemoryStorage()
loop = asyncio.get_event_loop()

bot = Bot(token=settings.TG_BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)  # , storage=storage)
executor = Executor(dp, skip_updates=settings.TG_BOT_SKIP_UPDATES)

bot_chats_storage = BotChatsStorage(bot.id, redis, settings.PRIORITY_CHATS)

openai_client = OpenAIClient(settings.OPENAI_TOKEN)
