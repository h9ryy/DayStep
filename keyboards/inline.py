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
