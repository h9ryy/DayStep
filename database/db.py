import aiosqlite
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
import random

from config import DB_PATH
from database.initial_quests import INITIAL_QUESTS
from database.initial_achievements import INITIAL_ACHIEVEMENTS


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
                freezes INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Миграция: добавляем колонку freezes, если таблица была создана ранее без нее
        try:
            await db.execute("ALTER TABLE users ADD COLUMN freezes INTEGER DEFAULT 1")
            await db.commit()
        except Exception:
            pass

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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                code TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                icon TEXT,
                reward_freezes INTEGER DEFAULT 0,
                type TEXT,
                category TEXT,
                target INTEGER
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_code TEXT,
                unlocked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(achievement_code) REFERENCES achievements(code),
                UNIQUE(user_id, achievement_code)
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

        # Заполняем достижения, если таблица пуста
        async with db.execute("SELECT COUNT(*) FROM achievements") as cursor:
            ach_count = (await cursor.fetchone())[0]
            if ach_count == 0:
                for a in INITIAL_ACHIEVEMENTS:
                    await db.execute(
                        """INSERT INTO achievements (code, title, description, icon, reward_freezes, type, category, target)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (a["code"], a["title"], a["description"], a["icon"], a["reward_freezes"], a["type"], a.get("category"), a["target"])
                    )
                await db.commit()


def calculate_active_streak(user: Dict[str, Any], today_str: Optional[str] = None) -> int:
    """Возвращает актуальный стрик с учетом пропусков."""
    if not today_str:
        today_str = date.today().isoformat()

    last_date = user.get("last_completed_date")
    if not last_date:
        return 0

    today = date.fromisoformat(today_str)
    yesterday_str = (today - timedelta(days=1)).isoformat()

    # Стрик активен, только если квест выполнен сегодня или вчера (или вчера был заморожен)
    if last_date == today_str or last_date == yesterday_str:
        return user.get("current_streak", 0)
    return 0


async def get_or_create_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                user_dict = dict(user)
                user_dict["current_streak"] = calculate_active_streak(user_dict)
                return user_dict

        now_str = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO users (user_id, username, first_name, created_at, freezes)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, username or "", first_name or "Друг", now_str)
        )
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            user_dict = dict(user)
            user_dict["current_streak"] = calculate_active_streak(user_dict)
            return user_dict


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return None
            user_dict = dict(user)
            user_dict["current_streak"] = calculate_active_streak(user_dict)
            return user_dict


async def get_all_active_users() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def check_and_use_freeze_if_missed(user_id: int, today_str: Optional[str] = None) -> bool:
    """Если вчера пользователь пропустил квест, но у него есть заморозка — применяем её."""
    if not today_str:
        today_str = date.today().isoformat()

    today = date.fromisoformat(today_str)
    yesterday_str = (today - timedelta(days=1)).isoformat()
    day_before_yesterday_str = (today - timedelta(days=2)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return False

        last_date = user["last_completed_date"]
        freezes = user["freezes"]
        streak = user["current_streak"]

        # Если стрик больше 0 и последний выполненный день был позавчера (вчера пропустили)
        if streak > 0 and last_date == day_before_yesterday_str and freezes > 0:
            # Списываем 1 заморозку и продвигаем дату на вчерашний день (стрик спасен)
            await db.execute(
                """UPDATE users 
                   SET freezes = freezes - 1, last_completed_date = ? 
                   WHERE user_id = ?""",
                (yesterday_str, user_id)
            )
            await db.commit()
            return True

    return False


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
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
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


async def check_and_unlock_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Проверяет условия и открывает новые достижения, начисляя награды."""
    newly_unlocked = []

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Загружаем данные пользователя
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                return []
            user_dict = dict(user)

        # Загружаем уже открытые коды достижений
        async with db.execute("SELECT achievement_code FROM user_achievements WHERE user_id = ?", (user_id,)) as cursor:
            unlocked_codes = set(row[0] for row in await cursor.fetchall())

        # Загружаем все доступные достижения
        async with db.execute("SELECT * FROM achievements") as cursor:
            all_achievements = [dict(row) for row in await cursor.fetchall()]

        # Считаем количество выполненных квестов по категориям
        category_counts_query = """
            SELECT q.category, COUNT(*) as cnt
            FROM user_quests uq
            JOIN quests q ON uq.quest_id = q.id
            WHERE uq.user_id = ? AND uq.status = 'completed'
            GROUP BY q.category
        """
        async with db.execute(category_counts_query, (user_id,)) as cursor:
            cat_rows = await cursor.fetchall()
            cat_counts = {row["category"]: row["cnt"] for row in cat_rows}

        current_streak = user_dict["current_streak"]
        total_completed = user_dict["total_completed"]

        now_str = datetime.now().isoformat()

        for ach in all_achievements:
            code = ach["code"]
            if code in unlocked_codes:
                continue

            unlocked = False
            a_type = ach["type"]
            target = ach["target"]

            if a_type == "total" and total_completed >= target:
                unlocked = True
            elif a_type == "streak" and current_streak >= target:
                unlocked = True
            elif a_type == "category":
                req_cat = ach["category"]
                if cat_counts.get(req_cat, 0) >= target:
                    unlocked = True

            if unlocked:
                await db.execute(
                    """INSERT INTO user_achievements (user_id, achievement_code, unlocked_at)
                       VALUES (?, ?, ?)""",
                    (user_id, code, now_str)
                )

                reward_freezes = ach["reward_freezes"]
                if reward_freezes > 0:
                    await db.execute(
                        "UPDATE users SET freezes = freezes + ? WHERE user_id = ?",
                        (reward_freezes, user_id)
                    )

                newly_unlocked.append(ach)

        await db.commit()

    return newly_unlocked


async def get_user_achievements_progress(user_id: int) -> List[Dict[str, Any]]:
    """Возвращает список всех достижений с актуальным прогрессом пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        user = await get_user(user_id)
        if not user:
            return []

        async with db.execute("SELECT * FROM achievements ORDER BY target ASC") as cursor:
            all_ach = [dict(r) for r in await cursor.fetchall()]

        async with db.execute("SELECT achievement_code, unlocked_at FROM user_achievements WHERE user_id = ?", (user_id,)) as cursor:
            unlocked_dict = {row["achievement_code"]: row["unlocked_at"] for row in await cursor.fetchall()}

        category_counts_query = """
            SELECT q.category, COUNT(*) as cnt
            FROM user_quests uq
            JOIN quests q ON uq.quest_id = q.id
            WHERE uq.user_id = ? AND uq.status = 'completed'
            GROUP BY q.category
        """
        async with db.execute(category_counts_query, (user_id,)) as cursor:
            cat_counts = {row["category"]: row["cnt"] for row in await cursor.fetchall()}

        result = []
        for ach in all_ach:
            code = ach["code"]
            is_unlocked = code in unlocked_dict

            # Вычисляем текущий прогресс
            a_type = ach["type"]
            target = ach["target"]
            if a_type == "total":
                current_val = user["total_completed"]
            elif a_type == "streak":
                current_val = user["current_streak"]
            elif a_type == "category":
                current_val = cat_counts.get(ach["category"], 0)
            else:
                current_val = 0

            ach_info = dict(ach)
            ach_info["is_unlocked"] = is_unlocked
            ach_info["unlocked_at"] = unlocked_dict.get(code)
            ach_info["current_val"] = min(current_val, target)
            result.append(ach_info)

        return result


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
        yesterday_str = (today - timedelta(days=1)).isoformat()

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

    # Проверяем новые достижения
    newly_unlocked = await check_and_unlock_achievements(user_id)
    refreshed_user = await get_user(user_id)

    return {
        "success": True,
        "new_streak": new_streak,
        "max_streak": new_max_streak,
        "total_completed": new_total,
        "freezes": refreshed_user.get("freezes", 1) if refreshed_user else 1,
        "quest_title": current_quest["title"],
        "newly_unlocked": newly_unlocked
    }


async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    today_str = date.today().isoformat()
    today = date.fromisoformat(today_str)
    yesterday_str = (today - timedelta(days=1)).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT user_id, username, first_name, max_streak, total_completed, last_completed_date, freezes,
                   CASE 
                       WHEN last_completed_date IN (?, ?) THEN current_streak 
                       ELSE 0 
                   END AS active_streak
            FROM users
            WHERE is_active = 1
            ORDER BY active_streak DESC, total_completed DESC, max_streak DESC
        """
        async with db.execute(query, (today_str, yesterday_str)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
