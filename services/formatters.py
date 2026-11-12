import html
from typing import Dict, Any, List


def format_quest_message(quest: Dict[str, Any], is_morning: bool = False) -> str:
    status_icon = "⏳ В процессе" if quest["status"] == "pending" else "✅ Выполнен"
    header = "🌅 <b>Доброе утро! Твой квест на сегодня:</b>\n\n" if is_morning else "🎯 <b>Квест на сегодня:</b>\n\n"

    category = html.escape(str(quest.get("category", "")))
    title = html.escape(str(quest.get("title", "")))
    description = html.escape(str(quest.get("description", "")))

    text = (
        f"{header}"
        f"🏷 <b>Категория:</b> {category}\n"
        f"📌 <b>Задание:</b> <b>{title}</b>\n\n"
        f"📝 {description}\n\n"
        f"📊 <b>Статус:</b> {status_icon}\n"
        f"⏳ Срок выполнения: до 23:59"
    )
    return text


def format_profile_message(user: Dict[str, Any], unlocked_achievements_count: int = 0, total_achievements_count: int = 8) -> str:
    streak = user.get("current_streak", 0)
    max_streak = user.get("max_streak", 0)
    total = user.get("total_completed", 0)
    freezes = user.get("freezes", 1)
    raw_name = user.get("first_name") or "Герой"
    name = html.escape(str(raw_name))

    if streak == 0:
        level_title = "Новичок 🌱"
    elif streak < 3:
        level_title = "Набирающий обороты ⚡️"
    elif streak < 7:
        level_title = "Уверенный практик 🔥"
    elif streak < 14:
        level_title = "Мастер дисциплины 🏆"
    elif streak < 30:
        level_title = "Неудержимый ⚡️👑"
    else:
        level_title = "Легенда Daystep 🌟"

    return (
        f"👤 <b>Профиль игрока {name}</b>\n\n"
        f"🔥 <b>Текущий стрик:</b> {streak} дн.\n"
        f"⭐ <b>Рекордный стрик:</b> {max_streak} дн.\n"
        f"❄️ <b>Запас заморозок:</b> {freezes} шт.\n"
        f"🎯 <b>Всего квестов:</b> {total}\n"
        f"🎖 <b>Достижений открыто:</b> {unlocked_achievements_count} из {total_achievements_count}\n"
        f"👑 <b>Ранг:</b> {level_title}\n\n"
        f"💡 <i>Заморозка автоматически спасет стрик при пропуске дня!</i>"
    )


def format_achievements_message(achievements: List[Dict[str, Any]]) -> str:
    if not achievements:
        return "🎖 <b>Список достижений пуст.</b>"

    unlocked_count = sum(1 for a in achievements if a.get("is_unlocked"))
    total_count = len(achievements)

    lines = [
        f"🎖 <b>Твои достижения ({unlocked_count}/{total_count}):</b>\n"
    ]

    for a in achievements:
        title = html.escape(a["title"])
        desc = html.escape(a["description"])
        reward = a.get("reward_freezes", 0)
        reward_text = f" <i>(+{reward} ❄️)</i>" if reward > 0 else ""

        if a.get("is_unlocked"):
            lines.append(f"✅ <b>{title}</b>{reward_text}\n   └ {desc}\n")
        else:
            curr = a.get("current_val", 0)
            target = a.get("target", 1)
            lines.append(f"🔒 <b>{title}</b> <i>({curr}/{target})</i>{reward_text}\n   └ {desc}\n")

    return "\n".join(lines)


def format_leaderboard_message(all_users: list, current_user_id: int, top_n: int = 10) -> str:
    if not all_users:
        return "🏆 <b>Лидерборд пуст!</b>\n\nСтаньте первым, выполнив квест сегодня!"

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ участников по стрикам:</b>\n"]

    user_rank = None
    user_streak = 0

    for idx, u in enumerate(all_users, start=1):
        if u["user_id"] == current_user_id:
            user_rank = idx
            user_streak = u["active_streak"]

        if idx <= top_n:
            prefix = medals[idx - 1] if idx <= 3 else f"<b>{idx}.</b>"
            raw_name = u["first_name"] or u["username"] or f"Игрок #{u['user_id']}"
            safe_name = html.escape(str(raw_name))
            streak = u["active_streak"]
            total = u["total_completed"]
            lines.append(f"{prefix} {safe_name} — <b>{streak} дн.</b> 🔥 <i>(всего: {total})</i>")

    lines.append("\n" + "—" * 22)
    if user_rank:
        if user_rank <= top_n:
            lines.append(f"⭐️ Ты на <b>#{user_rank} месте</b>! Отличный результат!")
        else:
            lines.append(f"👤 Твое место: <b>#{user_rank}</b> (стрик: {user_streak} дн.)\nПродолжай выполнять квесты, чтобы ворваться в топ!")
    else:
        lines.append("💡 Выполни квест сегодня, чтобы появиться в рейтинге!")

    return "\n".join(lines)
