from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import get_or_create_user, get_user_achievements_progress
from services.formatters import format_achievements_message

router = Router()


@router.message(F.text == "🎖 Достижения")
@router.message(Command("achievements"))
async def show_achievements(message: Message):
    user_id = message.from_user.id
    await get_or_create_user(user_id, message.from_user.username, message.from_user.first_name)

    achievements = await get_user_achievements_progress(user_id)
    text = format_achievements_message(achievements)
    await message.answer(text)
