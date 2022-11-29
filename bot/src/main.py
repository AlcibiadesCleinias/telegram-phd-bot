import argparse
import logging

from aiogram import Dispatcher

from bot.misc import executor
# note, that line below is very convenience and meaningful
from bot import handlers  # noqa
from config.settings import settings
from tasks.phd_work_notification import phd_work_notification_task

logging.basicConfig(
    format=u'%(levelname)-8s | %(asctime)s | %(message)s | %(filename)+13s',
    level=settings.LOG_LEVEL,
)
logger = logging.getLogger(__name__)


async def on_startup(dp: Dispatcher):
    logger.info('Starting the bot...')


async def on_shutdown(dp: Dispatcher):
    logger.info('Stopping the bot...')


def main(args):
    if args.phd_work_notification_run_once:
        return phd_work_notification_task.run_once()
    phd_work_notification_task.register()

    executor.on_startup(on_startup, polling=0)
    executor.on_shutdown(on_shutdown, polling=0)
    executor.start_polling()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phd-work-notification-run-once', action='store_true',
                        help='Define if you want to merely run once PhDWorkNotificationTask.')
    args, unparsed = parser.parse_known_args()
    if unparsed and len(unparsed) > 0:
        logger.warning('Unparsed arguments %s. Assert...', unparsed)
        assert False

    main(args)
