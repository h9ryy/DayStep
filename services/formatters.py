import html
from typing import Dict, Any


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


def format_profile_message(user: Dict[str, Any]) -> str:
    streak = user.get("current_streak", 0)
    max_streak = user.get("max_streak", 0)
    total = user.get("total_completed", 0)
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
        f"👤 <b>Профиль {name}</b>\n\n"
        f"🔥 <b>Текущий стрик:</b> {streak} дн.\n"
        f"⭐ <b>Рекордный стрик:</b> {max_streak} дн.\n"
        f"🎯 <b>Всего квестов выполнено:</b> {total}\n"
        f"🎖 <b>Ранг:</b> {level_title}\n\n"
        f"💡 <i>Совет: Не пропускай дни, чтобы стрик не сгорел!</i>"
    )
