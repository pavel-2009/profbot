"""Роутер для обработки команд к главному меню."""

from aiogram import F, Router, types
from aiogram.filters import Command

from bot.keyboards.keyboards import main_menu_keyboard


router = Router()


@router.message(F.text == "📚 Главная")
@router.message(Command("main"))
async def main_menu(message: types.Message) -> None:
    """Обработчик команды /main."""
    await message.answer(
        "📚 Добро пожаловать в главное меню! Выберите раздел, который вас интересует.",
        reply_markup=main_menu_keyboard,
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_command(message: types.Message) -> None:
    """Показать список доступных команд."""
    await message.answer(
        "❓ Команды:\n"
        "/start — регистрация\n"
        "/profile — профиль\n"
        "/shop — магазин\n"
        "/referral — рефералка\n"
        "/help — помощь",
        reply_markup=main_menu_keyboard,
    )
