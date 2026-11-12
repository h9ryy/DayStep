import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, quests, profile, leaderboard, achievements, settings, suggestions
from middlewares.throttling import ThrottlingMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("BOT_TOKEN не установлен! Пожалуйста, укажите токен в файле .env")
        print("\n[!] ОШИБКА: Пожалуйста, укажите валидный BOT_TOKEN в файле .env")
        return

    # Инициализация базы данных
    await init_db()
    logger.info("База данных успешно инициализирована.")

    # Инициализация бота с безопасным режимом HTML
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Защита от спама и частых нажатий (Throttling)
    throttling_middleware = ThrottlingMiddleware(rate_limit=0.8)
    dp.message.middleware(throttling_middleware)
    dp.callback_query.middleware(throttling_middleware)

    # Регистрация всех хэндлеров
    dp.include_router(start.router)
    dp.include_router(quests.router)
    dp.include_router(profile.router)
    dp.include_router(leaderboard.router)
    dp.include_router(achievements.router)
    dp.include_router(settings.router)
    dp.include_router(suggestions.router)

    # Настройка планировщика рассылок
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планировщик ежедневных квестов и напоминаний запущен.")

    logger.info("Бот Daystep успешно запущен и ожидает сообщений!")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
