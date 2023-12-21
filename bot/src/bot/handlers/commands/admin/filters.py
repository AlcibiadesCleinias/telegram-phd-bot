from aiogram import F

from config.settings import settings

from_superadmin_filter = F.chat.func(lambda chat: chat.id in settings.TG_SUPERADMIN_IDS)
