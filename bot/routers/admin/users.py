"""Роутер для получения списка пользователей и управления ими (для администраторов)"""

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from bot.middlewares.admin import AdminMiddleware
from bot.dependencies import get_user_service
from bot.core.db import async_session_factory
from bot.models.user import User
from bot.repositories.transaction_repository import TransactionRepository
from bot.models.transaction import Transaction


router = Router()
router.message.middleware(AdminMiddleware())
router.callback_query.middleware(AdminMiddleware())


@router.message(Command("users"))
@router.message(F.text == "👥 Управление пользователями")
async def get_users_list(message: Message) -> None:
    """Обрабатывает команду /users и отправляет администратору список пользователей."""
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        users: list[User] = await user_service.get_all_users()
    
    if not users:
        await message.answer("Нет зарегистрированных пользователей.")
        return
    
    response = "Список пользователей:\n\n"
    for user in users[:10]:  # Показываем только первых 10 пользователей
        response += f"ID: {user.telegram_id}, Username: @{user.username}, Balance: {user.balance}\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"show_user_{user.telegram_id}") for i, user in enumerate(users[:10], start=1)
        ],
        [
            InlineKeyboardButton(text="Показать всех", callback_data="show_all_users")
        ]
    ])
    
    await message.answer(response, reply_markup=keyboard)
    
    
@router.callback_query(F.data == "show_all_users")
async def show_all_users(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки "Показать всех"."""
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        users: list[User] = await user_service.get_all_users()
    
    if not users:
        await callback_query.message.answer("Нет зарегистрированных пользователей.")
        return
    
    response = "Список всех пользователей:\n\n"
    for user in users:
        response += f"ID: {user.telegram_id}, Username: @{user.username}, Balance: {user.balance}\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"show_user_{user.telegram_id}") for i, user in enumerate(users, start=1)
        ]
    ])
        
    await callback_query.message.answer(response, reply_markup=keyboard)
    

@router.callback_query(F.data.startswith("show_user_"))
async def show_user_details(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки с конкретным пользователем и показывает его детали."""
    
    telegram_id = int(callback_query.data.split("_")[-1])
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        user: User | None = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        await callback_query.message.answer("Пользователь не найден.")
        return
    
    response = (
        f"👤 <b>Карточка пользователя</b>\n\n"
        f"<b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Username:</b> @{user.username}\n"
        f"<b>Имя:</b> {user.first_name}\n"
        f"<b>Фамилия:</b> {user.last_name or 'N/A'}\n"
        f"<b>💰 Баланс:</b> {user.balance}\n"
        f"<b>Пригласил:</b> {user.invited_by or 'Нет'}\n"
        f"<b>Дата регистрации:</b> {user.registered_at.strftime('%d.%m.%Y %H:%M') if user.registered_at else 'N/A'}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Зачислить баланс", callback_data=f"credit_balance_{telegram_id}"),
        ],
        [
            InlineKeyboardButton(text="📊 История транзакций", callback_data=f"show_transactions_{telegram_id}"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_users_list"),
        ]
    ])
    
    await callback_query.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("credit_balance_"))
async def credit_balance_handler(callback_query: CallbackQuery) -> None:
    """Обрабатывает нажатие кнопки для зачисления баланса."""
    
    telegram_id = int(callback_query.data.split("_")[-1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="100", callback_data=f"set_credit_{telegram_id}_100"),
            InlineKeyboardButton(text="500", callback_data=f"set_credit_{telegram_id}_500"),
            InlineKeyboardButton(text="1000", callback_data=f"set_credit_{telegram_id}_1000"),
        ],
        [
            InlineKeyboardButton(text="5000", callback_data=f"set_credit_{telegram_id}_5000"),
            InlineKeyboardButton(text="10000", callback_data=f"set_credit_{telegram_id}_10000"),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data=f"show_user_{telegram_id}"),
        ]
    ])
    
    await callback_query.message.edit_text("Выберите сумму для зачисления:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("set_credit_"))
async def set_credit_amount(callback_query: CallbackQuery) -> None:
    """Зачисляет баланс пользователю."""
    
    parts = callback_query.data.split("_")
    telegram_id = int(parts[-2])
    amount = int(parts[-1])
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        user = await user_service.apply_balance_transaction(
            telegram_id=telegram_id,
            amount=amount,
            reason="Пополнение администратором"
        )
        
    if user:
        await callback_query.message.edit_text(
            f"✅ Баланс пользователя пополнен на {amount}\n"
            f"Новый баланс: {user.balance}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"show_user_{telegram_id}")]
            ])
        )
    else:
        await callback_query.message.answer("❌ Ошибка при пополнении баланса.")


@router.callback_query(F.data.startswith("show_transactions_"))
async def show_user_transactions(callback_query: CallbackQuery) -> None:
    """Показывает историю транзакций пользователя."""
    
    telegram_id = int(callback_query.data.split("_")[-1])
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        user = await user_service.get_user_by_telegram_id(telegram_id)
        
        if not user:
            await callback_query.message.answer("Пользователь не найден.")
            return
            
        transaction_repo = TransactionRepository(session)
        transactions: list[Transaction] = await transaction_repo.get_transactions_by_user_id(user.telegram_id)
    
    if not transactions:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"show_user_{telegram_id}")]
        ])
        await callback_query.message.edit_text(
            "📭 История транзакций пуста",
            reply_markup=keyboard
        )
        return
    
    response = f"📊 <b>История транзакций пользователя {user.username}</b>\n\n"
    
    for transaction in transactions[:20]:  # Показываем последние 20 транзакций
        date_str = transaction.created_at.strftime('%d.%m.%Y %H:%M') if transaction.created_at else 'N/A'
        status_emoji = "✅" if transaction.amount > 0 else "❌"
        response += (
            f"{status_emoji} <b>{transaction.amount:+d}</b> - {transaction.reason}\n"
            f"   <i>{date_str}</i>\n\n"
        )
    
    if len(transactions) > 20:
        response += f"<i>... и еще {len(transactions) - 20} транзакций</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"show_user_{telegram_id}")]
    ])
    
    await callback_query.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "back_to_users_list")
async def back_to_users_list(callback_query: CallbackQuery) -> None:
    """Возвращает назад к списку пользователей."""
    
    async with async_session_factory() as session:
        user_service = get_user_service(session)
        users: list[User] = await user_service.get_all_users()
    
    if not users:
        await callback_query.message.answer("Нет зарегистрированных пользователей.")
        return
    
    response = "Список пользователей:\n\n"
    for user in users[:10]:
        response += f"ID: {user.telegram_id}, Username: @{user.username}, Balance: {user.balance}\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=str(i), callback_data=f"show_user_{user.telegram_id}") for i, user in enumerate(users[:10], start=1)
        ],
        [
            InlineKeyboardButton(text="Показать всех", callback_data="show_all_users")
        ]
    ])
    
    await callback_query.message.edit_text(response, reply_markup=keyboard)
