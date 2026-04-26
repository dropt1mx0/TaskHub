# handlers/admin_withdrawals.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
from datetime import datetime

from database.db import db
from database.queries import WithdrawalQueries, UserQueries
from database.models import Bank
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from config import config

router = Router()

def admin_required(func):
    """Декоратор для проверки прав админа"""
    async def wrapper(callback, *args, **kwargs):
        if callback.from_user.id not in config.ADMIN_IDS:
            await callback.answer("⛔️ Access denied", show_alert=True)
            return
        return await func(callback, *args, **kwargs)
    return wrapper

@router.callback_query(F.data == "admin_withdrawals")
@admin_required
async def admin_show_withdrawals(callback: CallbackQuery):
    """Показать список ожидающих выплат"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            bank_balance = await Bank.get_balance(session)
            
            if not withdrawals:
                await callback.message.edit_text(
                    f"{get_text('no_pending', lang)}\n\n{get_text('bank_balance', lang, balance=bank_balance)}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="◀️ " + get_text('back', lang), 
                            callback_data="admin_back"
                        )]
                    ]),
                    parse_mode='HTML'
                )
                return
            
            text = f"<b>{get_text('pending_withdrawals', lang)}</b>\n\n"
            text += f"{get_text('bank_balance', lang, balance=bank_balance)}\n\n"
            
            keyboard = []
            for w in withdrawals[:5]:
                user_info = await UserQueries.get_user(session, w.user_id)
                username = user_info.username or f"User_{w.user_id}"
                
                text += f"#{w.id}: {username}\n"
                text += f"💰 {w.amount} {w.withdrawal_type.upper()}\n"
                text += f"📝 {w.wallet_address[:10]}...\n"
                text += f"🕐 {w.requested_at.strftime('%d.%m %H:%M')}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"Process #{w.id} - {w.amount} USDT",
                        callback_data=f"admin_process_withdrawal_{w.id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(
                text="◀️ " + get_text('back', lang), 
                callback_data="admin_back"
            )])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in admin_show_withdrawals: {e}")
        await callback.answer("Error loading withdrawals", show_alert=True)

@router.callback_query(F.data.startswith("admin_process_withdrawal_"))
@admin_required
async def admin_process_withdrawal(callback: CallbackQuery):
    """Обработка конкретной выплаты"""
    withdrawal_id = int(callback.data.split('_')[3])
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            withdrawal = next((w for w in withdrawals if w.id == withdrawal_id), None)
            
            if not withdrawal:
                await callback.answer("Withdrawal not found", show_alert=True)
                return
            
            user_info = await UserQueries.get_user(session, withdrawal.user_id)
            bank_balance = await Bank.get_balance(session)
            
            text = f"<b>Withdrawal #{withdrawal.id}</b>\n\n"
            text += f"👤 User: @{user_info.username or user_info.user_id}\n"
            text += f"💰 Amount: {withdrawal.amount} {withdrawal.withdrawal_type.upper()}\n"
            text += f"📝 Wallet: <code>{withdrawal.wallet_address}</code>\n"
            text += f"🕐 Requested: {withdrawal.requested_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            text += f"{get_text('bank_balance', lang, balance=bank_balance)}\n"
            
            if bank_balance < withdrawal.amount:
                text += "\n⚠️ <b>Insufficient funds in bank!</b>"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ " + get_text('approve', lang),
                        callback_data=f"admin_approve_{withdrawal.id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ " + get_text('reject', lang),
                        callback_data=f"admin_reject_{withdrawal.id}"
                    )
                ],
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_withdrawals"
                )]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data.startswith("admin_approve_"))
@admin_required
async def admin_approve_withdrawal(callback: CallbackQuery):
    """Подтвердить выплату"""
    withdrawal_id = int(callback.data.split('_')[2])
    admin_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            admin_user = await UserQueries.get_user(session, admin_id)
            lang = admin_user.language if admin_user else 'en'
            
            # Получаем выплату
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            withdrawal = next((w for w in withdrawals if w.id == withdrawal_id), None)
            
            if not withdrawal:
                await callback.answer("Withdrawal not found", show_alert=True)
                return
            
            # Проверяем баланс банка
            bank_balance = await Bank.get_balance(session)
            if bank_balance < withdrawal.amount:
                await callback.answer("❌ Insufficient funds in bank", show_alert=True)
                return
            
            # Обновляем статус
            await WithdrawalQueries.update_withdrawal_status(
                session, withdrawal_id, 'completed', processed_by=admin_id
            )
            
            # Списываем из банка
            await Bank.withdraw_funds(session, withdrawal.amount, f"Withdrawal #{withdrawal_id}")
            
            logger.info(f"Withdrawal {withdrawal_id} approved by admin {admin_id}")
            
            await callback.answer("✅ Withdrawal approved", show_alert=False)
            
            # Возвращаемся к списку
            await admin_show_withdrawals(callback)
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data.startswith("admin_reject_"))
@admin_required
async def admin_reject_withdrawal(callback: CallbackQuery):
    """Отклонить выплату"""
    withdrawal_id = int(callback.data.split('_')[2])
    admin_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            admin_user = await UserQueries.get_user(session, admin_id)
            lang = admin_user.language if admin_user else 'en'
            
            # Получаем выплату
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            withdrawal = next((w for w in withdrawals if w.id == withdrawal_id), None)
            
            if not withdrawal:
                await callback.answer("Withdrawal not found", show_alert=True)
                return
            
            # Возвращаем средства пользователю
            await UserQueries.update_balance(
                session, withdrawal.user_id, withdrawal.amount, hold=False
            )
            
            # Обновляем статус
            await WithdrawalQueries.update_withdrawal_status(
                session, withdrawal_id, 'failed', processed_by=admin_id
            )
            
            logger.info(f"Withdrawal {withdrawal_id} rejected by admin {admin_id}")
            
            await callback.answer("❌ Withdrawal rejected", show_alert=False)
            
            # Возвращаемся к списку
            await admin_show_withdrawals(callback)
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await callback.answer("Error", show_alert=True)