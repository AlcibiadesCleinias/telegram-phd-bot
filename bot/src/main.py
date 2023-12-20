import argparse
import asyncio
import logging

from aiogram import Bot

# Note, that line below is very convenience and meaningful.
from bot import filters, handlers  # noqa
from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp, bot
from config.settings import settings
from tasks.phd_work_notification import phd_work_notification_task
# from bot.handlers.commands.openai_contributor_token import router as openai_contributor_token_router

logging.basicConfig(
    format=u'%(levelname)-8s | %(asctime)s | %(message)s | %(filename)+13s',
    level=settings.LOG_LEVEL,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, *args, **kwargs):
    logger.info(f'Starting the bot {(await bot.me()).username}...')
    res = await bot.set_my_commands(CommandEnum.get_all_commands_json())
    logger.info(f'Set bot commands with result: {res}')


async def on_shutdown(*args, **kwargs):
    logger.info('Stopping the bot...')


async def main(args):
    phd_work_notification_task.register()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    # dp.include_router(openai_contributor_token_router)
    ALL_DEFAULT_TG_UPDATES = [
        'update_id',
        'message',
        'edited_message',
        'channel_post',
        'edited_channel_post',
        'inline_query',
        'chosen_inline_result',
        'callback_query',
        'shipping_query',
        'pre_checkout_query',
        'poll',
        'poll_answer',
        'my_chat_member',
        'chat_member',
        'chat_join_request',
    ]
    ADDITIONAL_TG_UPDATES = ['chat_member']
    await dp.start_polling(bot, allowed_updates=ALL_DEFAULT_TG_UPDATES + ADDITIONAL_TG_UPDATES)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phd-work-notification-run-once', action='store_true',
                        help='Define if you want to merely run once PhDWorkNotificationTask.')
    args, unparsed = parser.parse_known_args()
    if unparsed and len(unparsed) > 0:
        logger.warning('Unparsed arguments %s. Assert...', unparsed)
        assert False

    if args.phd_work_notification_run_once:
        phd_work_notification_task.run_once()
    else:
        asyncio.run(main(args))
