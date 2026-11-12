import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosqlite
from datetime import date

from config import TIMEZONE, DEFAULT_QUEST_HOUR, REMINDER_HOUR, DB_PATH
from database.db import get_all_active_users, assign_today_quest, get_today_quest
from keyboards.inline import get_quest_keyboard
from services.formatters import format_quest_message

logger = logging.getLogger(__name__)


async def send_daily_quests(bot: Bot):
    logger.info("Starting daily quest broadcast...")
    user_ids = await get_all_active_users()
    today_str = date.today().isoformat()

    for user_id in user_ids:
        try:
            quest = await assign_today_quest(user_id, today_str)
            quest_text = format_quest_message(quest, is_morning=True)
            keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
            await bot.send_message(user_id, quest_text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Failed to send daily quest to user {user_id}: {e}")
            if "bot was blocked by the user" in str(e).lower():
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
                    await db.commit()


async def send_evening_reminders(bot: Bot):
    logger.info("Starting evening reminders...")
    user_ids = await get_all_active_users()
    today_str = date.today().isoformat()

    for user_id in user_ids:
        try:
            quest = await get_today_quest(user_id, today_str)
            if quest and quest["status"] == "pending":
                reminder_text = (
                    "⏰ **Вечернее напоминание от Daystep!**\n\n"
                    f"До конца дня осталось несколько часов, а твой квест еще не закрыт:\n"
                    f"📌 **{quest['title']}**\n\n"
                    f"Не дай своему огню погаснуть! Выполни задание и нажми кнопку ниже 👇"
                )
                keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
                await bot.send_message(user_id, reminder_text, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Failed to send reminder to user {user_id}: {e}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Утренняя рассылка в DEFAULT_QUEST_HOUR:00
    scheduler.add_job(
        send_daily_quests,
        trigger=CronTrigger(hour=DEFAULT_QUEST_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot],
        name="daily_quests"
    )

    # Вечернее напоминание в REMINDER_HOUR:00
    scheduler.add_job(
        send_evening_reminders,
        trigger=CronTrigger(hour=REMINDER_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot],
        name="evening_reminders"
    )

    return scheduler
