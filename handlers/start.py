from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

from database.db import get_or_create_user, assign_today_quest, get_today_quest
from keyboards.reply import get_main_menu
from keyboards.inline import get_quest_keyboard
from services.formatters import format_quest_message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    await get_or_create_user(user_id, username, first_name)
    quest = await assign_today_quest(user_id)

    welcome_text = (
        f"👋 **Привет, {first_name or 'друг'}! Добро пожаловать в Daystep!**\n\n"
        "Каждое утро в **09:00** я буду присылать тебе одно небольшое случайное задание на день: "
        "пробежать дистанцию, приготовить интересное блюдо, почитать или сделать доброе дело.\n\n"
        "Твоя задача — выполнить его в течение дня и нажать кнопку **«✅ Выполнил!»**.\n"
        "Каждый выполненный день растит твой **стрик 🔥**!\n\n"
        "Не будем ждать утра — вот твой квест на сегодня 👇"
    )

    await message.answer(welcome_text, reply_markup=get_main_menu())

    quest_text = format_quest_message(quest)
    keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
    await message.answer(quest_text, reply_markup=keyboard)


@router.message(F.text == "ℹ️ О боте")
@router.message(Command("help"))
async def cmd_about(message: Message):
    about_text = (
        "ℹ️ **О проекте Daystep**\n\n"
        "🎯 **Идея:** Маленькие ежедневные шаги меняют качество жизни.\n\n"
        "⏰ **Расписание:**\n"
        "• 09:00 — Новый квест на день\n"
        "• 20:00 — Вечернее напоминание (если квест еще не закрыт)\n"
        "• 23:59 — Подведение итогов дня\n\n"
        "🔥 **Стрик:** Каждый закрытый день добавляет +1 к серии. Если пропустить день, стрик сгорает!\n"
        "🔄 **Замена:** 1 раз в день можно заменить выпавший квест, если он совсем не подходит."
    )
    await message.answer(about_text)
