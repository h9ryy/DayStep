from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="🎯 Квест дня"),
            KeyboardButton(text="🔥 Мой стрик"),
        ],
        [
            KeyboardButton(text="ℹ️ О боте")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
