import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
DEFAULT_QUEST_HOUR = int(os.getenv("DEFAULT_QUEST_HOUR", "9"))
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "20"))
DB_PATH = BASE_DIR / "daystep.db"
