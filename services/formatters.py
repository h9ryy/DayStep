from typing import Dict, Any


def format_quest_message(quest: Dict[str, Any], is_morning: bool = False) -> str:
    status_icon = "⏳ В процессе" if quest["status"] == "pending" else "✅ Выполнен"
    
    header = "🌅 **Доброе утро! Твой квест на сегодня:**\n\n" if is_morning else "🎯 **Квест на сегодня:**\n\n"
    
    text = (
        f"{header}"
        f"🏷 **Категория:** {quest['category']}\n"
        f"📌 **Задание:** **{quest['title']}**\n\n"
        f"📝 {quest['description']}\n\n"
        f"📊 **Статус:** {status_icon}\n"
        f"⏳ Срок выполнения: до 23:59"
    )
    return text


def format_profile_message(user: Dict[str, Any]) -> str:
    streak = user.get("current_streak", 0)
    max_streak = user.get("max_streak", 0)
    total = user.get("total_completed", 0)
    name = user.get("first_name", "Герой")

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
        f"👤 **Профиль {name}**\n\n"
        f"🔥 **Текущий стрик:** {streak} дн.\n"
        f"⭐ **Рекордный стрик:** {max_streak} дн.\n"
        f"🎯 **Всего квестов выполнено:** {total}\n"
        f"🎖 **Ранг:** {level_title}\n\n"
        f"💡 *Совет: Не пропускай дни, чтобы стрик не сгорел!*"
    )
