"""Клавиатуры для бота."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# === Клавиатура для главного меню ===
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Главная"),
         KeyboardButton(text="🛒 Магазин"),
         KeyboardButton(text="👤 Профиль")
        ],
        [KeyboardButton(text="💰 Пополнить"),
         KeyboardButton(text="🏆 Рейтинг"),
         KeyboardButton(text="📊 Статистика")
        ],
        [KeyboardButton(text="🔗 Рефералка"),
         KeyboardButton(text="🎁 Бонус"),
         KeyboardButton(text="❓ Помощь")
        ],
    ]
)


# === Клавиатура для профиля пользователя ===
profile_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📋 Полная история транзакций", callback_data="transactions_history")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="view_stats")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="referral_link")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_menu")],
    ]
)


# === Клавиатура для административного меню ===
admin_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Управление пользователями")],
        [KeyboardButton(text="🛒 Управление товарами"), KeyboardButton(text="📊 Общая статистика")],
        [KeyboardButton(text="⚙️ Настройки бота"), KeyboardButton(text="📦 Заказы")]
    ]
)
