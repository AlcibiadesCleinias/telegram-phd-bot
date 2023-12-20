import logging

from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot.handlers.commands.commands import CommandEnum
from bot.misc import dp
from bot.utils import remember_chat_handler_decorator

logger = logging.getLogger(__name__)


@dp.message(Command(CommandEnum.cancel.name))
@dp.message(F.text.casefold() == CommandEnum.cancel.name)
@remember_chat_handler_decorator
async def cancel_handler(message: types.Message, state: FSMContext, *args, **kwargs):
    """
    Allow user to cancel any action.
    """
    await message.answer(
        'Cancelled.',
        reply_markup=ReplyKeyboardRemove(),
    )
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.clear()
