from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import get_user, get_or_create_user, get_user_achievements_progress
from services.formatters import format_profile_message

router = Router()


@router.message(F.text == "🔥 Мой стрик")
@router.message(Command("profile"))
@router.message(Command("streak"))
async def show_profile(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        user = await get_or_create_user(user_id, message.from_user.username, message.from_user.first_name)

    achievements = await get_user_achievements_progress(user_id)
    unlocked_count = sum(1 for a in achievements if a.get("is_unlocked"))
    total_count = len(achievements)

    profile_text = format_profile_message(user, unlocked_count, total_count)
    await message.answer(profile_text)
