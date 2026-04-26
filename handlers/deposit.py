# handlers/deposit.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import time
import asyncio

from database.db import db
from database.queries import UserQueries, DepositQueries
from database.models import Bank
from services.ton_service import ton_service
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from config import config

router = Router()

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment = State()

@router.callback_query(F.data == "advertiser_deposit")
async def advertiser_deposit_start(callback: CallbackQuery, state: FSMContext):
    """Начать пополнение для рекламодателя"""
    await state.update_data(is_bank_deposit=False)
    await deposit_start(callback, state)

@router.callback_query(F.data == "admin_bank_deposit")
async def admin_bank_deposit_start(callback: CallbackQuery, state: FSMContext):
    """Начать пополнение банка для админа"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔️ Access denied", show_alert=True)
        return
    
    await state.update_data(is_bank_deposit=True)
    await deposit_start(callback, state)

async def deposit_start(callback: CallbackQuery, state: FSMContext):
    """Общий старт пополнения"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        data = await state.get_data()
        is_bank = data.get('is_bank_deposit', False)
        
        await state.set_state(DepositStates.waiting_for_amount)
        
        text = f"<b>Deposit to {'Bank' if is_bank else 'Your Balance'}</b>\n\n"
        text += f"Enter amount in TON (minimum {config.MIN_DEPOSIT} TON):"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text('back', lang), 
                    callback_data="admin_bank" if is_bank else "advertiser"
                )]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in deposit_start: {e}")
        await callback.answer("Error", show_alert=True)

@router.message(DepositStates.waiting_for_amount)
async def deposit_process_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения"""
    user_id = message.from_user.id
    data = await state.get_data()
    is_bank = data.get('is_bank_deposit', False)
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        try:
            amount = float(message.text.replace(',', '.'))
            if amount < config.MIN_DEPOSIT:
                await message.answer(
                    f"Minimum amount is {config.MIN_DEPOSIT} TON",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=get_text('back', lang), 
                            callback_data="admin_bank" if is_bank else "advertiser"
                        )]
                    ])
                )
                return
            
            # Создаем запись о депозите
            async with await db.get_session() as session:
                comment = ton_service.generate_comment(user_id, int(time.time()))
                deposit = await DepositQueries.create_deposit(
                    session, user_id, amount, 'ton', comment
                )
                
                # Получаем кошелек для этого пользователя
                wallet_address = ton_service.get_wallet_for_user(user_id)
                
                # Генерируем ссылку для оплаты
                payment_link = await ton_service.generate_payment_link(amount, comment, wallet_address)
                qr_url = await ton_service.generate_qr_code(amount, comment, wallet_address)
                
                await state.update_data(
                    deposit_id=deposit.id,
                    amount=amount,
                    comment=comment,
                    payment_link=payment_link,
                    qr_url=qr_url,
                    wallet_address=wallet_address,
                    is_bank=is_bank
                )
                
                text = f"<b>Deposit #{deposit.id}</b>\n\n"
                text += f"Amount: {amount} TON\n"
                text += f"Destination: {'Bank' if is_bank else 'Your Balance'}\n"
                text += f"Status: Pending\n\n"
                text += f"<b>❗️❗️❗️ ВАЖНО ❗️❗️❗️</b>\n\n"
                text += f"<b>Обязательно укажите этот комментарий при переводе:</b>\n"
                text += f"<code>❗️ {comment} ❗️</code>\n\n"
                text += f"<b>Без этого комментария деньги не зачислятся автоматически!</b>\n\n"
                text += f"<b>Payment details:</b>\n"
                text += f"Wallet: <code>{wallet_address}</code>\n"
                text += f"Comment: <code>{comment}</code>\n\n"
                text += f"<a href='{payment_link}'>Click to pay in TON wallet</a>\n\n"
                text += f"<a href='{qr_url}'>View QR Code</a>\n\n"
                text += f"After payment, click 'I've paid' to verify."
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="I've paid", callback_data="deposit_check")],
                    [InlineKeyboardButton(text="Cancel", callback_data="deposit_cancel")]
                ])
                
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                
                await state.set_state(DepositStates.waiting_for_payment)
                
        except ValueError:
            await message.answer(
                "Invalid amount. Please enter a number.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text('back', lang), 
                        callback_data="admin_bank" if is_bank else "advertiser"
                    )]
                ])
            )
    except Exception as e:
        logger.error(f"Error in deposit_process_amount: {e}")
        await message.answer("Error processing deposit")

@router.callback_query(F.data == "deposit_check")
async def deposit_check(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    deposit_id = data.get('deposit_id')
    expected_amount = data.get('amount')
    comment = data.get('comment')
    is_bank = data.get('is_bank', False)
    wallet_address = data.get('wallet_address')
    
    if not all([deposit_id, expected_amount, comment]):
        await callback.answer("No active deposit found", show_alert=True)
        return
    
    try:
        await callback.message.edit_text("Checking payment status...")
        
        # Проверяем транзакцию на всех кошельках
        success, received_amount, tx_hash = await ton_service.check_transaction(comment, expected_amount)
        
        if success:
            async with await db.get_session() as session:
                user = await UserQueries.get_user(session, user_id)
                lang = user.language if user else 'en'
                
                # Обновляем статус депозита
                await DepositQueries.update_deposit_status(session, deposit_id, 'completed', tx_hash)
                
                if is_bank:
                    # Пополняем банк
                    await Bank.add_funds(session, expected_amount, f"Deposit #{deposit_id}")
                    new_balance = await Bank.get_balance(session)
                    
                    text = f"<b>Bank deposit completed!</b>\n\n"
                    text += f"Amount: {expected_amount} TON\n"
                    text += f"New bank balance: {new_balance} USDT\n"
                    text += f"Tx: <code>{tx_hash}</code>\n\n"
                    text += f"Funds have been added to the bank."
                    
                    await callback.message.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=get_text('back', lang), 
                                callback_data="admin_bank"
                            )]
                        ]),
                        parse_mode='HTML'
                    )
                else:
                    # Пополняем баланс пользователя
                    await UserQueries.update_balance(session, user_id, expected_amount, hold=False)
                    user = await UserQueries.get_user(session, user_id)
                    
                    text = f"<b>Deposit completed!</b>\n\n"
                    text += f"Amount: {expected_amount} TON added to your balance\n"
                    text += f"New balance: {user.balance} USDT\n"
                    text += f"Tx: <code>{tx_hash}</code>"
                    
                    await callback.message.edit_text(
                        text,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(
                                text=get_text('back', lang), 
                                callback_data="advertiser"
                            )]
                        ]),
                        parse_mode='HTML'
                    )
                
                logger.info(f"Deposit {deposit_id} completed for user {user_id}")
                await state.clear()
        else:
            async with await db.get_session() as session:
                user = await UserQueries.get_user(session, user_id)
                lang = user.language if user else 'en'
            
            await callback.message.edit_text(
                f"<b>Deposit #{deposit_id}</b>\n\n"
                f"Amount: {expected_amount} TON\n"
                f"Status: Still pending\n\n"
                f"<b>❗️❗️❗️ ВАЖНО ❗️❗️❗️</b>\n\n"
                f"<b>Проверьте что вы указали правильный комментарий:</b>\n"
                f"<code>❗️ {comment} ❗️</code>\n\n"
                f"<b>Без этого комментария платеж не будет обнаружен!</b>\n\n"
                f"<b>Payment details:</b>\n"
                f"Wallet: <code>{wallet_address}</code>\n"
                f"Comment: <code>{comment}</code>\n\n"
                f"Payment not detected yet. Please make sure you:\n"
                f"1. Sent exact amount ({expected_amount} TON)\n"
                f"2. Included correct comment (see above)\n"
                f"3. Transaction is confirmed on the blockchain\n\n"
                f"Click 'I've paid' again after sending.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="I've paid", callback_data="deposit_check")],
                    [InlineKeyboardButton(text="Cancel", callback_data="deposit_cancel")]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in deposit_check: {e}")
        await callback.answer("Error checking payment", show_alert=True)

@router.callback_query(F.data == "deposit_cancel")
async def deposit_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена депозита"""
    data = await state.get_data()
    is_bank = data.get('is_bank_deposit', False)
    deposit_id = data.get('deposit_id')
    
    try:
        if deposit_id:
            async with await db.get_session() as session:
                await DepositQueries.update_deposit_status(session, deposit_id, 'failed')
        
        await state.clear()
        
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        if is_bank:
            from handlers.admin import admin_show_bank
            await admin_show_bank(callback)
        else:
            from handlers.advertiser import show_advertiser_panel
            await show_advertiser_panel(callback, lang)
    except Exception as e:
        logger.error(f"Error in deposit_cancel: {e}")
        await callback.answer("Error", show_alert=True)