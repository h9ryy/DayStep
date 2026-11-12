from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import get_leaderboard, get_or_create_user
from services.formatters import format_leaderboard_message

router = Router()


@router.message(F.text == "🏆 Топ игроков")
@router.message(Command("top"))
@router.message(Command("leaderboard"))
async def show_leaderboard(message: Message):
    user_id = message.from_user.id
    # Гарантируем, что пользователь есть в базе данных
    await get_or_create_user(user_id, message.from_user.username, message.from_user.first_name)

    all_users = await get_leaderboard(limit=100)
    text = format_leaderboard_message(all_users, user_id, top_n=10)
    await message.answer(text)
