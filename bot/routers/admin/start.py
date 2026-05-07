"""Роутер для стартовой команды админов."""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.keyboards.keyboards import admin_menu_keyboard
from bot.middlewares.admin import AdminMiddleware


router = Router()
router.message.middleware(AdminMiddleware())


@router.message(Command("admin"))
async def admin_start(message: Message):
    await message.answer("Добро пожаловать в административное меню!", reply_markup=admin_menu_keyboard)
