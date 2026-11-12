from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database.db import get_or_create_user, update_user_notify_hour
from keyboards.inline import get_time_settings_keyboard

router = Router()


@router.message(F.text == "⚙️ Настройки")
@router.message(Command("settings"))
async def show_settings(message: Message):
    user_id = message.from_user.id
    user = await get_or_create_user(user_id, message.from_user.username, message.from_user.first_name)
    current_hour = user.get("notify_hour", 9)

    text = (
        "⚙️ <b>Настройки времени квеста</b>\n\n"
        f"Текущее время получения задания: <b>{current_hour:02d}:00</b> (по МСК).\n\n"
        "В какое время тебе удобнее всего получать квест дня?\n"
        "Нажми на нужный час ниже 👇"
    )
    keyboard = get_time_settings_keyboard(current_hour)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("time:set:"))
async def handle_set_time(callback: CallbackQuery):
    user_id = callback.from_user.id
    hour = int(callback.data.split(":")[2])

    await update_user_notify_hour(user_id, hour)

    text = (
        "⚙️ <b>Настройки времени квеста</b>\n\n"
        f"✅ Время успешно обновлено! Теперь бот будет присылать квест в <b>{hour:02d}:00</b> (по МСК).\n\n"
        "Если захочешь изменить — просто нажми другой час ниже 👇"
    )
    keyboard = get_time_settings_keyboard(hour)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer(f"Сохранено: {hour:02d}:00")
