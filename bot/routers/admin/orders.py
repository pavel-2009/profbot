"""Роутер для получения списка заказов и управления ими (для администраторов)"""

from aiogram import Router, F
from aiogram.types import Message

from bot.middlewares.admin import AdminMiddleware
from bot.dependencies import get_shop_service


router = Router()
router.message.middleware(AdminMiddleware())

# Дописать обработчики для управления заказами
