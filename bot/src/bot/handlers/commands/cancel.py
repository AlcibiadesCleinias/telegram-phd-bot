import logging

from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot.handlers.commands import consts
from bot.misc import dp

logger = logging.getLogger(__name__)


@dp.message(Command('cancel'))
@dp.message(F.text.casefold() == consts.CANCEL)
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action.
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    await state.clear()
    await message.answer(
        'Cancelled.',
        reply_markup=ReplyKeyboardRemove(),
    )
