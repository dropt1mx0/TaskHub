# handlers/wallet.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger

from database.db import db
from services.payment_service import PaymentService
from database.queries import UserQueries, WithdrawalQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.validators import validate_amount
from utils.helpers import format_number
from config import config

router = Router()

class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_wallet = State()

@router.callback_query(F.data == "withdraw")
async def show_withdraw_menu(callback: CallbackQuery, lang: str):
    """Показать меню вывода"""
    await callback.message.edit_text(
        get_text('withdraw_title', lang),
        reply_markup=InlineKeyboards.withdraw_methods(lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("withdraw_"))
async def choose_withdraw_method(callback: CallbackQuery, state: FSMContext, lang: str):
    """Выбор метода вывода"""
    method = callback.data.split('_')[1]  # usdt или ton
    
    await state.update_data(method=method)
    await state.set_state(WithdrawalStates.waiting_for_amount)
    
    currency = "USDT" if method == 'usdt' else "TON"
    
    # Разные минимальные суммы для разных валют
    min_amount = config.MIN_WITHDRAWAL
    
    await callback.message.edit_text(
        get_text('enter_amount', lang, min=min_amount, currency=currency),
        reply_markup=InlineKeyboards.back_button('withdraw', lang),
        parse_mode='HTML'
    )

@router.message(WithdrawalStates.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext, lang: str):
    """Обработка суммы вывода"""
    data = await state.get_data()
    method = data['method']
    currency = "USDT" if method == 'usdt' else "TON"
    
    # Валидация суммы
    is_valid, amount, error = validate_amount(message.text, config.MIN_WITHDRAWAL)
    
    if not is_valid:
        error_text = error or get_text('invalid_amount', lang, min=config.MIN_WITHDRAWAL)
        await message.answer(
            error_text,
            reply_markup=InlineKeyboards.back_button('withdraw', lang)
        )
        return
    
    # Проверяем баланс
    async with await db.get_session() as session:
        user = await UserQueries.get_user(session, message.from_user.id)
        if user.balance < amount:
            await message.answer(
                get_text('insufficient_balance', lang, balance=format_number(user.balance)),
                reply_markup=InlineKeyboards.back_button('withdraw', lang)
            )
            return
    
    await state.update_data(amount=amount)
    await state.set_state(WithdrawalStates.waiting_for_wallet)
    
    # Запрашиваем адрес кошелька в зависимости от валюты
    if method == 'ton':
        text = get_text('enter_wallet_ton', lang)
    else:
        text = get_text('enter_wallet_usdt', lang)
    
    # Добавляем информацию о комиссии
    if method == 'ton':
        text += f"\n\n⚠️ Network fee: ~{config.TON_NETWORK_FEE} TON will be deducted"
    
    await message.answer(
        text,
        reply_markup=InlineKeyboards.back_button('withdraw', lang)
    )

@router.message(WithdrawalStates.waiting_for_wallet)
async def process_wallet(message: Message, state: FSMContext, lang: str):
    """Обработка адреса кошелька"""
    data = await state.get_data()
    wallet = message.text.strip()
    
    # Создаем заявку
    async with await db.get_session() as session:
        success, withdrawal, error = await PaymentService.create_withdrawal(
            session,
            message.from_user.id,
            data['amount'],
            data['method'],
            wallet
        )
        
        if success:
            logger.info(f"Withdrawal created: User {message.from_user.id}, Amount {data['amount']} {data['method'].upper()}")
            
            currency = "USDT" if data['method'] == 'usdt' else "TON"
            
            text = get_text('withdrawal_created', lang,
                           amount=format_number(data['amount']),
                           currency=currency,
                           wallet=wallet)
            
            # Добавляем информацию о комиссии для TON
            if data['method'] == 'ton':
                text += f"\n\n⚠️ Network fee of ~{config.TON_NETWORK_FEE} TON will be deducted from the amount upon sending."
            
            text += "\n\n⏳ " + get_text('withdrawal_pending', lang)
            
            await message.answer(
                text,
                reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                parse_mode='HTML'
            )
            await state.clear()
        else:
            await message.answer(
                f"❌ {error}",
                reply_markup=InlineKeyboards.back_button('withdraw', lang)
            )

@router.callback_query(F.data == "withdrawal_history")
async def show_withdrawal_history(callback: CallbackQuery, lang: str):
    """Показать историю выводов"""
    user_id = callback.from_user.id
    
    async with await db.get_session() as session:
        history = await PaymentService.get_withdrawal_history(session, user_id)
        
        if not history:
            text = get_text('no_withdrawals', lang)
        else:
            text = get_text('withdrawal_history', lang) + "\n\n"
            for w in history:
                status_emoji = "✅" if w['status'] == 'completed' else "⏳" if w['status'] == 'pending' else "❌"
                text += f"{status_emoji} #{w['id']}: {w['amount']} {w['currency']} - {w['date']}\n"
                text += f"   📝 {w['wallet']}\n"
                if w.get('tx_hash'):
                    text += f"   🔗 {w['tx_hash'][:10]}...\n"
                text += "➖➖➖➖➖➖\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboards.back_and_home('withdraw', lang),
            parse_mode='HTML'
        )