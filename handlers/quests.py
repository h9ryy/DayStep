import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database.db import (
    assign_today_quest,
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
    quest_title = html.escape(str(result.get("quest_title", "")))
    freezes = result.get("freezes", 1)

    congrats_text = (
        f"🎉 <b>Отличная работа! Квест выполнен!</b>\n\n"
        f"✅ Задание: <i>{quest_title}</i>\n"
        f"🔥 Твой текущий стрик: <b>{streak} {streak_word} подряд!</b>\n"
        f"❄️ Запас заморозок: <b>{freezes} шт.</b>\n"
        f"🏆 Всего выполнено квестов: <b>{result['total_completed']}</b>\n"
    )

    # Добавляем поздравление с новыми открытыми достижениями
    newly_unlocked = result.get("newly_unlocked", [])
    if newly_unlocked:
        congrats_text += "\n" + "—" * 22 + "\n"
        for ach in newly_unlocked:
            ach_title = html.escape(ach["title"])
            ach_desc = html.escape(ach["description"])
            reward = ach.get("reward_freezes", 0)
            reward_str = f" <i>(Награда: +{reward} ❄️ заморозка!)</i>" if reward > 0 else ""
            congrats_text += f"🎖 <b>НОВОЕ ДОСТИЖЕНИЕ: {ach_title}!</b>{reward_str}\n<i>{ach_desc}</i>\n\n"

    congrats_text += "Увидимся завтра утром с новым заданием! 🚀"

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
        f"🔄 <b>Квест успешно заменен!</b>\n\n{quest_text}",
        reply_markup=keyboard
    )
    await callback.answer("Квест заменен на новый!")
