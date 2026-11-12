import asyncio
import html
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosqlite

from config import TIMEZONE, REMINDER_HOUR, DB_PATH
from database.db import (
    get_users_by_notify_hour,
    get_all_active_users,
    assign_today_quest,
    get_today_quest,
    check_and_use_freeze_if_missed,
    get_user
)
from keyboards.inline import get_quest_keyboard
from services.formatters import format_quest_message

logger = logging.getLogger(__name__)


async def send_hourly_quests(bot: Bot):
    """Срабатывает каждый час и отправляет квесты тем, кто выбрал текущий час."""
    try:
        tz = ZoneInfo(TIMEZONE)
        now_hour = datetime.now(tz).hour
    except Exception:
        now_hour = datetime.now().hour

    logger.info(f"Running hourly quest broadcast for {now_hour:02d}:00...")
    user_ids = await get_users_by_notify_hour(now_hour)
    if not user_ids:
        logger.info(f"No users scheduled for {now_hour:02d}:00")
        return

    today_str = date.today().isoformat()

    for user_id in user_ids:
        try:
            # 1. Проверяем, не спас ли стрик режим заморозки
            was_frozen = await check_and_use_freeze_if_missed(user_id, today_str)
            if was_frozen:
                user = await get_user(user_id)
                rem = user.get("freezes", 0) if user else 0
                freeze_notice = (
                    "❄️ <b>Твой стрик спасён!</b>\n\n"
                    "Вчера ты не успел выполнить квест, но автоматически сработала заморозка.\n"
                    f"Твоя серия дней осталась цела! Оставшиеся заморозки: <b>{rem} шт.</b>\n\n"
                    "Не пропускай сегодняшнее задание 👇"
                )
                await bot.send_message(user_id, freeze_notice)
                await asyncio.sleep(0.05)

            # 2. Назначаем и отправляем квест дня
            quest = await assign_today_quest(user_id, today_str)
            quest_text = format_quest_message(quest, is_morning=True)
            keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
            await bot.send_message(user_id, quest_text, reply_markup=keyboard)

        except TelegramRetryAfter as e:
            logger.warning(f"Flood control exceeded. Sleeping for {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(user_id, quest_text, reply_markup=keyboard)
            except Exception as retry_err:
                logger.error(f"Failed to send on retry to user {user_id}: {retry_err}")
        except TelegramForbiddenError:
            logger.info(f"User {user_id} blocked the bot. Deactivating.")
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to send quest to user {user_id}: {e}")

        await asyncio.sleep(0.05)


async def send_evening_reminders(bot: Bot):
    logger.info("Starting evening reminders...")
    user_ids = await get_all_active_users()
    today_str = date.today().isoformat()

    for user_id in user_ids:
        try:
            quest = await get_today_quest(user_id, today_str)
            if quest and quest["status"] == "pending":
                escaped_title = html.escape(str(quest['title']))
                reminder_text = (
                    "⏰ <b>Вечернее напоминание от Daystep!</b>\n\n"
                    f"До конца дня осталось несколько часов, а твой квест еще не закрыт:\n"
                    f"📌 <b>{escaped_title}</b>\n\n"
                    f"Не дай своему огню погаснуть! Выполни задание и нажми кнопку ниже 👇"
                )
                keyboard = get_quest_keyboard(quest["status"], quest.get("reroll_count", 0))
                await bot.send_message(user_id, reminder_text, reply_markup=keyboard)
        except TelegramRetryAfter as e:
            logger.warning(f"Flood control exceeded in reminders. Sleeping for {e.retry_after}s.")
            await asyncio.sleep(e.retry_after)
        except TelegramForbiddenError:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to send reminder to user {user_id}: {e}")

        await asyncio.sleep(0.05)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Почасовая отправка квестов в :00 минут
    scheduler.add_job(
        send_hourly_quests,
        trigger=CronTrigger(minute=0, timezone=TIMEZONE),
        args=[bot],
        name="hourly_quests"
    )

    # Вечернее напоминание в REMINDER_HOUR:00
    scheduler.add_job(
        send_evening_reminders,
        trigger=CronTrigger(hour=REMINDER_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot],
        name="evening_reminders"
    )

    return scheduler
