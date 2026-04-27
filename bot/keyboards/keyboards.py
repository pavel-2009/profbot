"""Клавиатуры для бота."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# === Клавиатура для главного меню ===
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Главная"),
         KeyboardButton(text="🛒 Магазин"),
         KeyboardButton(text="👤 Профиль")
        ],
        [KeyboardButton(text="💰 Пополнитья"),
         KeyboardButton(text="🏆 Рейтинг"),
         KeyboardButton(text="📊 Статистика")
        ],
        [KeyboardButton(text="🔗 Рефералка"),
         KeyboardButton(text="🎁 Бонус"),
         KeyboardButton(text="❓ Помощь")
        ],
    ]