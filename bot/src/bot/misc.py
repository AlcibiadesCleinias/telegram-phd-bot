# Currently, this module is to initialize all general class objects used in bot.
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis
from utils.redis.discussion_mode_storage import BotChatAIDiscussionModeStorage
from fernet import Fernet

from clients.perplexity.client import PerplexityClient
from utils.crypto import Crypto
from clients.openai.client import OpenAIClient
from config.settings import settings

# In code below it uses asyncio lock inside when creates connection pool
from utils.redis.redis_storage import BotChatsStorage, BotChatMessagesCache, BotAIContributorChatStorage
from utils.token_api_request_manager import TokenApiRequestManager

fernet_engine = Fernet(settings.FERNET_KEY)
crypto = Crypto(fernet_engine)

redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
storage = RedisStorage(redis) if settings.REDIS_HOST else MemoryStorage()
loop = asyncio.get_event_loop()

bot = Bot(token=settings.TG_BOT_TOKEN, parse_mode='HTML')
dp = Dispatcher(storage=storage)

# To store all chats ever used by the bot.
bot_chats_storage = BotChatsStorage(bot.id, redis)
# To store messages and ACTIVE chats.
bot_chat_messages_cache = BotChatMessagesCache(bot.id, redis, settings.TG_BOT_CACHE_TTL)
bot_ai_contributor_chat_storage = BotAIContributorChatStorage(bot.id, redis, crypto)

bot_chat_discussion_mode_storage = BotChatAIDiscussionModeStorage(bot.id, redis)

openai_token_api_request_manager = TokenApiRequestManager(
    settings.OPENAI_TOKEN, redis, crypto, 'OpenAI',
)
openai_client_priority = OpenAIClient(token_api_request_manager=openai_token_api_request_manager)

perplexity_token_api_request_manager = TokenApiRequestManager(
    settings.PERPLEXITY_TOKEN, redis, crypto, 'Perplexity',
)
perplexity_client_priority = PerplexityClient(
    token_api_request_manager=perplexity_token_api_request_manager,
    openai_model=settings.PERPLEXITY_OPENAI_MODEL,
)
