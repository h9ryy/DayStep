from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_quest_keyboard(status: str = "pending", reroll_count: int = 0) -> InlineKeyboardMarkup:
    buttons = []
    if status == "pending":
        row1 = [InlineKeyboardButton(text="✅ Выполнил!", callback_data="quest:done")]
        buttons.append(row1)
        if reroll_count == 0:
            row2 = [InlineKeyboardButton(text="🔄 Заменить квест (1 раз)", callback_data="quest:reroll")]
            buttons.append(row2)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_settings_keyboard(current_hour: int = 9) -> InlineKeyboardMarkup:
    hours = [6, 7, 8, 9, 10, 11, 12, 13]
    buttons = []
    row = []

    for h in hours:
        text = f"{h:02d}:00 ✅" if h == current_hour else f"{h:02d}:00"
        row.append(InlineKeyboardButton(text=text, callback_data=f"time:set:{h}"))
        if len(row) == 4:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


SUGGESTION_CATEGORIES = [
    "🏃 Спорт",
    "🍳 Кулинария",
    "🧘 Осознанность",
    "📚 Развитие",
    "✨ Уют и окружение"
]


def get_category_select_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for idx, cat in enumerate(SUGGESTION_CATEGORIES):
        buttons.append([InlineKeyboardButton(text=cat, callback_data=f"sug_cat:{idx}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="sug_cat:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_moderation_keyboard(suggestion_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Одобрить (+1 ❄️)", callback_data=f"mod:app:{suggestion_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"mod:rej:{suggestion_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
