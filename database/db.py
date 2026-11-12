import aiosqlite
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import random

from config import DB_PATH
from database.initial_quests import INITIAL_QUESTS


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT,
                current_streak INTEGER DEFAULT 0,
                max_streak INTEGER DEFAULT 0,
                last_completed_date TEXT,
                total_completed INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                title TEXT,
                description TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quest_id INTEGER,
                assigned_date TEXT,
                status TEXT DEFAULT 'pending',
                assigned_at TEXT,
                completed_at TEXT,
                reroll_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(quest_id) REFERENCES quests(id)
            )
        """)
        await db.commit()

        # Заполняем квесты, если таблица пуста
        async with db.execute("SELECT COUNT(*) FROM quests") as cursor:
            count = (await cursor.fetchone())[0]
            if count == 0:
                for q in INITIAL_QUESTS:
                    await db.execute(
                        "INSERT INTO quests (category, title, description) VALUES (?, ?, ?)",
                        (q["category"], q["title"], q["description"])
                    )
                await db.commit()


async def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                return dict(user)

        now_str = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO users (user_id, username, first_name, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, username or "", first_name or "Друг", now_str)
        )
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            return dict(user)


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            return dict(user) if user else None


async def get_all_active_users() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_today_quest(user_id: int, today_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not today_str:
        today_str = date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT uq.id as user_quest_id, uq.status, uq.assigned_date, uq.reroll_count,
                   q.id as quest_id, q.category, q.title, q.description
            FROM user_quests uq
            JOIN quests q ON uq.quest_id = q.id
            WHERE uq.user_id = ? AND uq.assigned_date = ?
            ORDER BY uq.id DESC
            LIMIT 1
        """
        async with db.execute(query, (user_id, today_str)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def assign_today_quest(user_id: int, today_str: Optional[str] = None) -> Dict[str, Any]:
    if not today_str:
        today_str = date.today().isoformat()

    existing = await get_today_quest(user_id, today_str)
    if existing:
        return existing

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Исключаем последние 7 квестов пользователя, чтобы задания не повторялись часто
        recent_ids_query = """
            SELECT quest_id FROM user_quests 
            WHERE user_id = ? 
            ORDER BY id DESC LIMIT 7
        """
        async with db.execute(recent_ids_query, (user_id,)) as cursor:
            recent_ids = [row[0] for row in await cursor.fetchall()]

        if recent_ids:
            placeholders = ",".join("?" * len(recent_ids))
            query = f"SELECT * FROM quests WHERE id NOT IN ({placeholders})"
            async with db.execute(query, recent_ids) as cursor:
                available = await cursor.fetchall()
        else:
            available = []

        if not available:
            async with db.execute("SELECT * FROM quests") as cursor:
                available = await cursor.fetchall()

        chosen_quest = random.choice(available)
        now_str = datetime.now().isoformat()

        await db.execute(
            """INSERT INTO user_quests (user_id, quest_id, assigned_date, status, assigned_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (user_id, chosen_quest["id"], today_str, now_str)
        )
        await db.commit()

    return await get_today_quest(user_id, today_str)


async def reroll_today_quest(user_id: int, today_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not today_str:
        today_str = date.today().isoformat()

    current = await get_today_quest(user_id, today_str)
    if not current or current["status"] != "pending":
        return None

    if current["reroll_count"] >= 1:
        return None  # Максимум 1 замена в день

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Выбираем новый квест, исключая текущий
        query = "SELECT * FROM quests WHERE id != ?"
        async with db.execute(query, (current["quest_id"],)) as cursor:
            available = await cursor.fetchall()

        if not available:
            return current

        new_quest = random.choice(available)

        await db.execute(
            """UPDATE user_quests 
               SET quest_id = ?, reroll_count = reroll_count + 1 
               WHERE id = ?""",
            (new_quest["id"], current["user_quest_id"])
        )
        await db.commit()

    return await get_today_quest(user_id, today_str)


async def complete_today_quest(user_id: int, today_str: Optional[str] = None) -> Dict[str, Any]:
    if not today_str:
        today_str = date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        user = await get_user(user_id)
        if not user:
            return {"success": False, "error": "Пользователь не найден"}

        current_quest = await get_today_quest(user_id, today_str)
        if not current_quest:
            return {"success": False, "error": "Квест на сегодня не найден"}

        if current_quest["status"] == "completed":
            return {"success": False, "error": "Квест уже был выполнен"}

        now_str = datetime.now().isoformat()
        await db.execute(
            """UPDATE user_quests 
               SET status = 'completed', completed_at = ? 
               WHERE id = ?""",
            (now_str, current_quest["user_quest_id"])
        )

        # Расчет стрика
        last_date_str = user["last_completed_date"]
        current_streak = user["current_streak"]

        today = date.fromisoformat(today_str)
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.isoformat()

        if last_date_str == yesterday_str:
            new_streak = current_streak + 1
        elif last_date_str == today_str:
            new_streak = current_streak
        else:
            new_streak = 1

        new_max_streak = max(user["max_streak"], new_streak)
        new_total = user["total_completed"] + 1

        await db.execute(
            """UPDATE users 
               SET current_streak = ?, max_streak = ?, last_completed_date = ?, total_completed = ?
               WHERE user_id = ?""",
            (new_streak, new_max_streak, today_str, new_total, user_id)
        )
        await db.commit()

        return {
            "success": True,
            "new_streak": new_streak,
            "max_streak": new_max_streak,
            "total_completed": new_total,
            "quest_title": current_quest["title"]
        }
