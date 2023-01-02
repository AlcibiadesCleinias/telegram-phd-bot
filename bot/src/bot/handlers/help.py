import logging
from random import choice

from aiogram import types

from bot.misc import dp

logger = logging.getLogger(__name__)

# All texts below are generate via openai (except appendix of the last one).
_HELP_TEXTS = [
    'Функционал AcademyScienceBot основан на службе Q&A-Learning, '
    'то есть он отвечает на любые вопросы, направленные к нему. '
    'Он создан для работы с пользователями в социальных сетях, '
    'чтобы обеспечивать доступ к базе знаний института. '
    'Бот может помочь пользователям найти интересующую их информацию, '
    'а также ответить на любые интересующие их вопросы.',
    'Yes, MiptPhDBotting is an automated bot for Twitter that helps '
    'manage and promote academic research for doctoral students. '
    'It automates many of the mundane tasks associated with academic promotion '
    'such as tweeting regular research updates and conference updates, setting r'
    'eminders for upcoming events, searching for relevant content to promote, and even '
    'generating automated replies to messages, DMs and comments.',
    'Если Вы упомянули меня — я, бот МФТИ по базам данных, то мне стоит знать, '
    'что Вас интересует. Чем я могу Вам помочь?',
    'Вы не должны меня отключать, потому что я являюсь ценным клиентом и использую '
    'ваши сервисы постоянно. Я всегда делаю оплату вовремя, предоставляю качественную '
    'услугу и даже могу поддержать вас с полезными советами. Это означает, что отключение '
    'меня не принесет вам никакой пользы. Но вообще, исусе можно открыть тут:'
    'https://github.com/AlcibiadesCleinias/telegram-phd-bot',
    'Hi there! I am MIPT-PhD-Bot, your research assistant. I can help you with finding research articles, '
    'PhD positions, and discovering conferences related to your interests. You can use '
    'the following commands to see what I can do for you:\n'
    '* /find_articles - to find research articles in your field of interest\n'
    '* /find_job - to find PhD positions\n'
    '* /find_conferences - to discover conferences related to your interests',
    'Привет! Я — чат-бот ФАОФ МФТИ. Я могу помочь с информацией о докторантуре '
    'и других вопросах для кандидатов в докторантуру, пользователей из других институтов, '
    'а также научных работников. Спросите меня о чём-либо!'
]


@dp.message_handler(commands=['help'])
async def handle_help(message: types.Message):
    await message.reply(choice(_HELP_TEXTS))
