from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database.db import (
    assign_today_quest,
    get_today_quest,
    reroll_today_quest,
    complete_today_quest
)
from keyboards.inline import get_quest_keyboard
from services.formatters import format_quest_message

router = Router()


@router.message(F.text == "🎯 Квест дня")
@router.message(Command("quest"))
async def show_today_quest(message: Message):
    user_id = message.from_user.id
    quest = await assign_today_quest(user_id)

    quest_text = format_quest_message(quest)
    keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
    await message.answer(quest_text, reply_markup=keyboard)


@router.callback_query(F.data == "quest:done")
async def handle_quest_done(callback: CallbackQuery):
    user_id = callback.from_user.id
    result = await complete_today_quest(user_id)

    if not result.get("success"):
        await callback.answer(result.get("error", "Ошибка при выполнении"), show_alert=True)
        return

    streak = result["new_streak"]
    streak_word = "день" if streak % 10 == 1 and streak % 100 != 11 else ("дня" if 2 <= streak % 10 <= 4 and (streak % 100 < 10 or streak % 100 >= 20) else "дней")

    congrats_text = (
        f"🎉 **Отличная работа! Квест выполнен!**\n\n"
        f"✅ Задание: *{result['quest_title']}*\n"
        f"🔥 Твой текущий стрик: **{streak} {streak_word} подряд!**\n"
        f"🏆 Всего выполнено квестов: **{result['total_completed']}**\n\n"
        f"Увидимся завтра утром с новым заданием! 🚀"
    )

    await callback.message.edit_text(congrats_text)
    await callback.answer("Красавчик! Задание засчитано 🔥")


@router.callback_query(F.data == "quest:reroll")
async def handle_quest_reroll(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_quest = await reroll_today_quest(user_id)

    if not new_quest:
        await callback.answer("Ты уже заменял квест сегодня или он уже выполнен!", show_alert=True)
        return

    quest_text = format_quest_message(new_quest)
    keyboard = get_quest_keyboard(new_quest["status"], new_quest.get("reroll_count", 0))

    await callback.message.edit_text(
        f"🔄 **Квест успешно заменен!**\n\n{quest_text}",
        reply_markup=keyboard
    )
    await callback.answer("Квест заменен на новый!")
