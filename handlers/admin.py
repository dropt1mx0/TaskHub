# handlers/admin.py
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import asyncio
import time

from database.db import db
from database.queries import UserQueries, TaskQueries, WithdrawalQueries, DepositQueries, AdminQueries
from database.models import Bank
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from config import config
from services.ton_service import ton_service

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

class AdminTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_reward = State()
    waiting_for_channel = State()
    waiting_for_confirmation = State()

class AdminDepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment = State()

class AdminManagementStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_confirm_remove = State()

def admin_required(func):
    """Декоратор для проверки прав админа"""
    async def wrapper(callback: CallbackQuery, *args, **kwargs):
        if callback.from_user.id not in config.ADMIN_IDS:
            await callback.answer("⛔️ Access denied", show_alert=True)
            return
        
        # Получаем количество параметров функции
        import inspect
        sig = inspect.signature(func)
        num_params = len(sig.parameters)
        
        # В зависимости от количества параметров вызываем по-разному
        if num_params == 1:
            return await func(callback)
        elif num_params == 2:
            # Проверяем, есть ли state в kwargs
            if 'state' in kwargs:
                return await func(callback, kwargs['state'])
            else:
                return await func(callback, None)
        else:
            return await func(callback)
    return wrapper

def owner_required(func):
    """Декоратор для проверки прав владельца"""
    async def wrapper(callback: CallbackQuery, *args, **kwargs):
        if callback.from_user.id != config.OWNER_ID:
            await callback.answer("⛔️ Только владелец бота может выполнить это действие", show_alert=True)
            return
        return await func(callback, *args, **kwargs)
    return wrapper

@router.message(Command("administrator"))
async def cmd_administrator(message: Message):
    """Заглушка для команды /administrator"""
    await message.answer("❌ Unknown command. Use /admin for admin panel.")

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    user_id = message.from_user.id
    
    if user_id not in config.ADMIN_IDS:
        await message.answer("⛔️ Access denied")
        return
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await message.answer(
            f"<b>{get_text('admin_panel', lang)}</b>\n\nChoose action:",
            reply_markup=InlineKeyboards.admin_panel(lang),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        await message.answer("Error loading admin panel")

@router.callback_query(F.data == "admin_stats")
@admin_required
async def admin_stats(callback: CallbackQuery):
    """Статистика бота"""
    try:
        async with await db.get_session() as session:
            stats = await AdminQueries.get_stats(session)
            
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
            
            text = f"<b>📊 {get_text('admin_stats', lang)}</b>\n\n"
            text += f"👥 {get_text('total_users', lang)}: {stats['total_users']}\n"
            text += f"🆕 {get_text('new_users_24h', lang)}: {stats['new_users_24h']}\n"
            text += f"⭐️ {get_text('premium_users', lang)}: {stats['premium_users']}\n"
            text += f"✅ {get_text('tasks_completed', lang)}: {stats['completions']}\n"
            text += f"💰 {get_text('total_withdrawn', lang)}: {stats['total_withdrawals']} USDT\n"
            text += f"⏳ {get_text('pending_withdrawals', lang)}: {stats['pending_withdrawals']}\n"
            text += f"⏳ Pending deposits: {stats['pending_deposits']}\n"
            text += f"🏦 {get_text('bank_balance', lang, balance=stats['bank_balance'])}\n"
            text += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_back"
                )]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await callback.answer("Error loading statistics", show_alert=True)

@router.callback_query(F.data == "admin_back")
@admin_required
async def admin_back(callback: CallbackQuery):
    """Возврат в админ панель"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        await callback.message.edit_text(
            f"<b>{get_text('admin_panel', lang)}</b>\n\nChoose action:",
            reply_markup=InlineKeyboards.admin_panel(lang),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin_back: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_broadcast")
@admin_required
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        await state.set_state(BroadcastStates.waiting_for_message)
        
        await callback.message.edit_text(
            get_text('enter_broadcast', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_back"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_broadcast_start: {e}")
        await callback.answer("Error", show_alert=True)

@router.message(BroadcastStates.waiting_for_message)
async def admin_broadcast_preview(message: Message, state: FSMContext):
    """Предпросмотр рассылки"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔️ Access denied")
        await state.clear()
        return
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, message.from_user.id)
            lang = user.language if user else 'en'
        
        await state.update_data(text=message.text)
        await state.set_state(BroadcastStates.waiting_for_confirmation)
        
        async with await db.get_session() as session:
            from sqlalchemy import select, func
            from database.models import User
            users_count = (await session.execute(select(func.count(User.user_id)))).scalar() or 0
        
        await message.answer(
            get_text('broadcast_preview', lang, text=message.text, count=users_count),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Confirm", callback_data="broadcast_confirm"),
                    InlineKeyboardButton(text="❌ Cancel", callback_data="broadcast_cancel")
                ]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in broadcast preview: {e}")
        await message.answer("Error creating broadcast")

@router.callback_query(F.data == "broadcast_confirm")
@admin_required
async def admin_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение рассылки"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        data = await state.get_data()
        text = data.get('text', '')
        
        await callback.message.edit_text("⏳ " + get_text('loading', lang))
        
        async with await db.get_session() as session:
            from sqlalchemy import select
            from database.models import User
            users = (await session.execute(select(User.user_id))).scalars().all()
        
        success = 0
        failed = 0
        
        for uid in users:
            try:
                await callback.bot.send_message(uid, text, parse_mode='HTML')
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send to {uid}: {e}")
            await asyncio.sleep(0.05)
        
        await callback.message.edit_text(
            get_text('broadcast_sent', lang, success=success, failed=failed),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_back"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in broadcast confirm: {e}")
        await callback.answer("Error", show_alert=True)
    
    await state.clear()

@router.callback_query(F.data == "broadcast_cancel")
@admin_required
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        await state.clear()
        await callback.message.edit_text(
            get_text('broadcast_cancelled', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_back"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in broadcast cancel: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_withdrawals")
@admin_required
async def admin_withdrawals(callback: CallbackQuery):
    """Просмотр ожидающих выплат"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
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
        logger.error(f"Error in admin_withdrawals: {e}")
        await callback.answer("Error loading withdrawals", show_alert=True)

@router.callback_query(F.data.startswith("admin_process_withdrawal_"))
@admin_required
async def admin_process_withdrawal(callback: CallbackQuery):
    """Обработка конкретной выплаты"""
    withdrawal_id = int(callback.data.split('_')[3])
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
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
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            withdrawal = next((w for w in withdrawals if w.id == withdrawal_id), None)
            
            if not withdrawal:
                await callback.answer("Withdrawal not found", show_alert=True)
                return
            
            bank_balance = await Bank.get_balance(session)
            if bank_balance < withdrawal.amount:
                await callback.answer("❌ Insufficient funds in bank", show_alert=True)
                return
            
            await WithdrawalQueries.update_withdrawal_status(
                session, withdrawal_id, 'completed', processed_by=admin_id
            )
            await Bank.withdraw_funds(session, withdrawal.amount, f"Withdrawal #{withdrawal_id}")
            
            logger.info(f"Withdrawal {withdrawal_id} approved by admin {admin_id}")
            await callback.answer("✅ Withdrawal approved", show_alert=False)
            await admin_withdrawals(callback)
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
            withdrawals = await WithdrawalQueries.get_pending_withdrawals(session)
            withdrawal = next((w for w in withdrawals if w.id == withdrawal_id), None)
            
            if not withdrawal:
                await callback.answer("Withdrawal not found", show_alert=True)
                return
            
            await UserQueries.update_balance(session, withdrawal.user_id, withdrawal.amount, hold=False)
            await WithdrawalQueries.update_withdrawal_status(session, withdrawal_id, 'failed', processed_by=admin_id)
            
            logger.info(f"Withdrawal {withdrawal_id} rejected by admin {admin_id}")
            await callback.answer("❌ Withdrawal rejected", show_alert=False)
            await admin_withdrawals(callback)
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_tasks")
@admin_required
async def admin_show_tasks(callback: CallbackQuery):
    """Показать список всех заданий"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
            
            tasks = await TaskQueries.get_all_tasks(session)
            
            if not tasks:
                text = get_text('no_tasks', lang)
            else:
                text = f"<b>{get_text('admin_tasks', lang)}</b>\n\n"
                for task in tasks[:10]:
                    status = "✅" if task.is_active else "❌"
                    text += f"{status} #{task.id}: {task.title}\n"
                    text += f"   💰 {task.reward} USDT | {get_text('tasks_completed', lang)}: {task.total_completions}\n"
                    text += f"   👤 {get_text('created_by', lang)}: {task.created_by}"
                    if config.is_admin(task.created_by):
                        text += " ⭐"
                    text += f"\n   ➖➖➖➖➖➖\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="➕ " + get_text('create_task', lang), 
                callback_data="admin_create_task"
            )],
            [InlineKeyboardButton(
                text="🗑 Delete task", 
                callback_data="admin_delete_task_select"
            )],
            [InlineKeyboardButton(
                text="◀️ " + get_text('back', lang), 
                callback_data="admin_back"
            )]
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin_show_tasks: {e}")
        await callback.answer("Error loading tasks", show_alert=True)

@router.callback_query(F.data == "admin_delete_task_select")
@admin_required
async def admin_delete_task_select(callback: CallbackQuery):
    """Выбрать задание для удаления"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            tasks = await TaskQueries.get_all_tasks(session)
            
            if not tasks:
                await callback.message.edit_text(
                    "No tasks to delete.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Back", callback_data="admin_tasks")]
                    ])
                )
                return
            
            text = "<b>Select task to delete:</b>\n\n"
            keyboard = []
            
            for task in tasks[:10]:
                text += f"#{task.id}: {task.title} (by {task.created_by})"
                if config.is_admin(task.created_by):
                    text += " ⭐"
                text += "\n"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑 Delete #{task.id}",
                        callback_data=f"admin_delete_task_{task.id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(text="◀️ Back", callback_data="admin_tasks")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in admin_delete_task_select: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data.startswith("admin_delete_task_"))
@admin_required
async def admin_delete_task(callback: CallbackQuery):
    """Удалить задание"""
    task_id = int(callback.data.split('_')[3])
    admin_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, admin_id)
            lang = user.language if user else 'en'
            
            task = await TaskQueries.get_task_by_id(session, task_id)
            
            if not task:
                await callback.answer("Task not found", show_alert=True)
                return
            
            # Удаляем задание
            success = await TaskQueries.delete_task(session, task_id)
            
            if success:
                logger.info(f"Admin {admin_id} deleted task #{task_id}")
                
                await callback.message.edit_text(
                    f"✅ Task #{task_id} deleted successfully.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Back to tasks", callback_data="admin_tasks")]
                    ])
                )
            else:
                await callback.message.edit_text(
                    "❌ Failed to delete task.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Back", callback_data="admin_tasks")]
                    ])
                )
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_create_task")
@admin_required
async def admin_create_task_start(callback: CallbackQuery, state: FSMContext):
    """Начать создание задания"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.set_state(AdminTaskStates.waiting_for_title)
        
        await callback.message.edit_text(
            get_text('enter_task_title', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_tasks"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_create_task_start: {e}")
        await callback.answer("Error", show_alert=True)

@router.message(AdminTaskStates.waiting_for_title)
@admin_required
async def admin_process_task_title(message: Message, state: FSMContext):
    """Обработка названия задания"""
    user_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.update_data(title=message.text)
        await state.set_state(AdminTaskStates.waiting_for_description)
        
        await message.answer(
            get_text('enter_task_desc', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_tasks"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_process_task_title: {e}")
        await message.answer("Error")

@router.message(AdminTaskStates.waiting_for_description)
@admin_required
async def admin_process_task_description(message: Message, state: FSMContext):
    """Обработка описания задания"""
    user_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.update_data(description=message.text)
        await state.set_state(AdminTaskStates.waiting_for_reward)
        
        await message.answer(
            get_text('enter_task_reward', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_tasks"
                )]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_process_task_description: {e}")
        await message.answer("Error")

@router.message(AdminTaskStates.waiting_for_reward)
@admin_required
async def admin_process_task_reward(message: Message, state: FSMContext):
    """Обработка награды за задание"""
    user_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        try:
            reward = float(message.text.replace(',', '.'))
            if reward < 0.1:
                await message.answer(
                    get_text('invalid_reward', lang),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="◀️ " + get_text('back', lang), 
                            callback_data="admin_tasks"
                        )]
                    ])
                )
                return
            
            await state.update_data(reward=reward)
            await state.set_state(AdminTaskStates.waiting_for_channel)
            
            await message.answer(
                get_text('enter_channel', lang),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ " + get_text('back', lang), 
                        callback_data="admin_tasks"
                    )]
                ])
            )
        except ValueError:
            await message.answer(
                get_text('invalid_reward', lang),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ " + get_text('back', lang), 
                        callback_data="admin_tasks"
                    )]
                ])
            )
    except Exception as e:
        logger.error(f"Error in admin_process_task_reward: {e}")
        await message.answer("Error")

@router.message(AdminTaskStates.waiting_for_channel)
@admin_required
async def admin_process_task_channel(message: Message, state: FSMContext):
    """Обработка ссылки на канал"""
    user_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        from utils.validators import validate_channel_link
        is_valid, username, error = validate_channel_link(message.text)
        
        if not is_valid:
            await message.answer(
                error or get_text('invalid_channel', lang),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ " + get_text('back', lang), 
                        callback_data="admin_tasks"
                    )]
                ])
            )
            return
        
        data = await state.get_data()
        
        text = get_text('task_preview', lang,
                       title=data['title'],
                       reward=data['reward'],
                       channel=f"@{username}")
        
        # Добавляем пометку для админов
        if config.is_admin(user_id):
            text += "\n\n⭐ Задание создается бесплатно (админ)"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Confirm", callback_data="admin_confirm_task"),
                InlineKeyboardButton(text="❌ Cancel", callback_data="admin_cancel_task")
            ]
        ])
        
        await state.update_data(channel_username=username, channel_url=f"https://t.me/{username}")
        await state.set_state(AdminTaskStates.waiting_for_confirmation)
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin_process_task_channel: {e}")
        await message.answer("Error")

@router.callback_query(F.data == "admin_confirm_task")
@admin_required
async def admin_confirm_task_creation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания задания"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            task = await TaskQueries.create_task(
                session,
                title=data['title'],
                description=data['description'],
                reward=data['reward'],
                created_by=user_id,
                channel_url=data.get('channel_url'),
                channel_username=data.get('channel_username'),
                task_type='channel_subscription'
            )
            
            logger.info(f"Admin {user_id} created task #{task.id}")
            
            await callback.message.edit_text(
                get_text('task_created', lang),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ " + get_text('back', lang), 
                        callback_data="admin_tasks"
                    )]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await callback.answer("Error creating task", show_alert=True)
    
    await state.clear()

@router.callback_query(F.data == "admin_cancel_task")
@admin_required
async def admin_cancel_task_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания задания"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.clear()
        await callback.message.edit_text(
            get_text('task_cancelled', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ " + get_text('back', lang), 
                    callback_data="admin_tasks"
                )]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin_cancel_task: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_bank")
@admin_required
async def admin_show_bank(callback: CallbackQuery):
    """Показать баланс банка"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
            
            bank_balance = await Bank.get_balance(session)
            
            # Получаем все кошельки (только для админов)
            all_wallets = ton_service.get_all_wallets()
            wallets_text = "\n".join([f"• <code>{addr}</code>" for addr in all_wallets])
            
            # Получаем историю операций
            from sqlalchemy import select, desc
            from database.models import Withdrawal, Deposit
            
            text = f"<b>🏦 Bank Management</b>\n\n"
            text += f"Current balance: {bank_balance:.3f} USDT\n\n"
            text += f"<b>All wallets (for monitoring):</b>\n{wallets_text}\n\n"
            
            # Последние депозиты
            deposits = await session.execute(
                select(Deposit)
                .where(Deposit.status == 'completed')
                .order_by(desc(Deposit.completed_at))
                .limit(3)
            )
            recent_deposits = deposits.scalars().all()
            
            text += f"<b>Recent deposits:</b>\n"
            if recent_deposits:
                for d in recent_deposits:
                    text += f"✅ #{d.id}: +{d.amount} TON - {d.completed_at.strftime('%d.%m')}\n"
            else:
                text += "No recent deposits\n"
            
            # Последние выводы
            withdrawals = await session.execute(
                select(Withdrawal)
                .where(Withdrawal.status.in_(['completed', 'failed']))
                .order_by(desc(Withdrawal.processed_at))
                .limit(3)
            )
            recent_withdrawals = withdrawals.scalars().all()
            
            text += f"\n<b>Recent withdrawals:</b>\n"
            if recent_withdrawals:
                for w in recent_withdrawals:
                    status = "✅" if w.status == 'completed' else "❌"
                    text += f"{status} #{w.id}: -{w.amount} USDT - {w.processed_at.strftime('%d.%m')}\n"
            else:
                text += "No recent withdrawals\n"
            
            # Кнопка для пополнения банка
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💰 Deposit to bank (TON)", 
                    callback_data="admin_bank_deposit"
                )],
                [InlineKeyboardButton(
                    text="◀️ Back", 
                    callback_data="admin_back"
                )]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error showing bank: {e}")
        await callback.answer("Error", show_alert=True)

@router.callback_query(F.data == "admin_bank_deposit")
@admin_required
async def admin_bank_deposit_start(callback: CallbackQuery, state: FSMContext):
    """Начать пополнение банка"""
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
        
        await state.set_state(AdminDepositStates.waiting_for_amount)
        
        text = f"<b>Deposit to Bank</b>\n\n"
        text += f"Enter amount in TON (minimum {config.MIN_DEPOSIT} TON):\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="◀️ Back", 
                    callback_data="admin_bank"
                )]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in admin_bank_deposit_start: {e}")
        await callback.answer("Error", show_alert=True)

@router.message(AdminDepositStates.waiting_for_amount)
@admin_required
async def admin_bank_deposit_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения банка"""
    user_id = message.from_user.id
    
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
                            text="◀️ Back", 
                            callback_data="admin_bank"
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
                
                # Получаем кошелек для этого пользователя (админа)
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
                    wallet_address=wallet_address
                )
                
                text = f"<b>Bank Deposit #{deposit.id}</b>\n\n"
                text += f"Amount: {amount} TON\n"
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
                    [InlineKeyboardButton(text="I've paid", callback_data="admin_bank_deposit_check")],
                    [InlineKeyboardButton(text="Cancel", callback_data="admin_bank_deposit_cancel")]
                ])
                
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                
                await state.set_state(AdminDepositStates.waiting_for_payment)
                
        except ValueError:
            await message.answer(
                "Invalid amount. Please enter a number.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="◀️ Back", 
                        callback_data="admin_bank"
                    )]
                ])
            )
    except Exception as e:
        logger.error(f"Error in admin_bank_deposit_amount: {e}")
        await message.answer("Error processing deposit")

@router.callback_query(F.data == "admin_bank_deposit_check")
@admin_required
async def admin_bank_deposit_check(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа для банка"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    deposit_id = data.get('deposit_id')
    expected_amount = data.get('amount')
    comment = data.get('comment')
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
                            text="◀️ Back to bank", 
                            callback_data="admin_bank"
                        )]
                    ]),
                    parse_mode='HTML'
                )
                
                logger.info(f"Bank deposit {deposit_id} completed by admin {user_id}")
                await state.clear()
        else:
            async with await db.get_session() as session:
                user = await UserQueries.get_user(session, user_id)
                lang = user.language if user else 'en'
            
            await callback.message.edit_text(
                f"<b>Bank Deposit #{deposit_id}</b>\n\n"
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
                    [InlineKeyboardButton(text="I've paid", callback_data="admin_bank_deposit_check")],
                    [InlineKeyboardButton(text="Cancel", callback_data="admin_bank_deposit_cancel")]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in admin_bank_deposit_check: {e}")
        await callback.answer("Error checking payment", show_alert=True)

@router.callback_query(F.data == "admin_bank_deposit_cancel")
@admin_required
async def admin_bank_deposit_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена депозита банка"""
    deposit_id = (await state.get_data()).get('deposit_id')
    
    try:
        if deposit_id:
            async with await db.get_session() as session:
                await DepositQueries.update_deposit_status(session, deposit_id, 'failed')
        
        await state.clear()
        await admin_show_bank(callback)
    except Exception as e:
        logger.error(f"Error in admin_bank_deposit_cancel: {e}")
        await callback.answer("Error", show_alert=True)

# ============= УПРАВЛЕНИЕ АДМИНАМИ =============

@router.callback_query(F.data == "admin_management")
@admin_required
async def admin_management(callback: CallbackQuery):
    """Управление администраторами"""
    user_id = callback.from_user.id
    
    # Только владелец может управлять админами
    if not config.is_owner(user_id):
        await callback.answer("⛔️ Только владелец бота может управлять админами", show_alert=True)
        return
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            # Получаем список всех админов
            admin_ids = config.ADMIN_IDS
            admins_list = []
            
            for admin_id in admin_ids:
                admin_user = await UserQueries.get_user(session, admin_id)
                if admin_user:
                    username = admin_user.username or f"User_{admin_id}"
                    admins_list.append(f"• {admin_id} - @{username}")
                else:
                    admins_list.append(f"• {admin_id} - (не зарегистрирован)")
            
            text = f"<b>👥 Управление администраторами</b>\n\n"
            text += f"👑 Владелец: {config.OWNER_ID}\n\n"
            text += f"<b>Текущие администраторы:</b>\n"
            text += "\n".join(admins_list) if admins_list else "Нет администраторов"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add")],
                [InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in admin_management: {e}")
        await callback.answer("Ошибка", show_alert=True)

@router.callback_query(F.data == "admin_add")
@admin_required
async def admin_add_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление админа"""
    user_id = callback.from_user.id
    
    if not config.is_owner(user_id):
        await callback.answer("⛔️ Только владелец может добавлять админов", show_alert=True)
        return
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.set_state(AdminManagementStates.waiting_for_admin_id)
        
        await callback.message.edit_text(
            "📝 Введите ID пользователя, которого хотите сделать администратором:\n\n"
            "(Пользователь должен быть зарегистрирован в боте)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_management")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_add_start: {e}")
        await callback.answer("Ошибка", show_alert=True)

@router.message(AdminManagementStates.waiting_for_admin_id)
async def admin_add_process(message: Message, state: FSMContext):
    """Обработка добавления админа"""
    user_id = message.from_user.id
    
    if not config.is_owner(user_id):
        await message.answer("⛔️ Только владелец может добавлять админов")
        await state.clear()
        return
    
    try:
        new_admin_id = int(message.text.strip())
        
        # Проверяем, не является ли пользователь уже админом
        if new_admin_id in config.ADMIN_IDS:
            await message.answer(
                "❌ Этот пользователь уже является администратором",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_management")]
                ])
            )
            await state.clear()
            return
        
        # Проверяем, зарегистрирован ли пользователь в боте
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, new_admin_id)
            if not user:
                await message.answer(
                    "❌ Пользователь с таким ID не зарегистрирован в боте",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_management")]
                    ])
                )
                await state.clear()
                return
            
            # Добавляем в список админов
            config.ADMIN_IDS.append(new_admin_id)
            
            # Отправляем уведомление новому админу
            try:
                await message.bot.send_message(
                    new_admin_id,
                    "🎉 Поздравляем! Вы стали администратором бота TaskHub!\n"
                    "Теперь вы можете создавать задания бесплатно."
                )
            except:
                pass
            
            await message.answer(
                f"✅ Пользователь {new_admin_id} успешно добавлен в администраторы",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_management")]
                ])
            )
    except ValueError:
        await message.answer(
            "❌ Введите корректный числовой ID",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_management")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in admin_add_process: {e}")
        await message.answer("Ошибка при добавлении администратора")
    
    await state.clear()

@router.callback_query(F.data == "admin_remove")
@admin_required
async def admin_remove_start(callback: CallbackQuery):
    """Начать удаление админа"""
    user_id = callback.from_user.id
    
    if not config.is_owner(user_id):
        await callback.answer("⛔️ Только владелец может удалять админов", show_alert=True)
        return
    
    try:
        # Получаем список админов (кроме владельца)
        admins_to_remove = [aid for aid in config.ADMIN_IDS if aid != config.OWNER_ID]
        
        if not admins_to_remove:
            await callback.answer("Нет администраторов для удаления", show_alert=True)
            return
        
        keyboard = []
        async with await db.get_session() as session:
            for admin_id in admins_to_remove[:5]:  # Показываем первые 5
                admin_user = await UserQueries.get_user(session, admin_id)
                username = admin_user.username or f"User_{admin_id}" if admin_user else f"ID {admin_id}"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"❌ Удалить {username}",
                        callback_data=f"admin_remove_confirm_{admin_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_management")])
        
        await callback.message.edit_text(
            "Выберите администратора для удаления:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    except Exception as e:
        logger.error(f"Error in admin_remove_start: {e}")
        await callback.answer("Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("admin_remove_confirm_"))
@admin_required
async def admin_remove_confirm(callback: CallbackQuery):
    """Подтверждение удаления админа"""
    user_id = callback.from_user.id
    
    if not config.is_owner(user_id):
        await callback.answer("⛔️ Только владелец может удалять админов", show_alert=True)
        return
    
    try:
        admin_to_remove = int(callback.data.split('_')[3])
        
        # Не даем удалить самого себя (владельца)
        if admin_to_remove == config.OWNER_ID:
            await callback.answer("❌ Нельзя удалить владельца", show_alert=True)
            return
        
        if admin_to_remove in config.ADMIN_IDS:
            config.ADMIN_IDS.remove(admin_to_remove)
            
            # Отправляем уведомление бывшему админу
            try:
                await callback.bot.send_message(
                    admin_to_remove,
                    "⚠️ Вы были удалены из списка администраторов бота TaskHub."
                )
            except:
                pass
            
            await callback.answer("✅ Администратор удален", show_alert=False)
        else:
            await callback.answer("❌ Администратор не найден", show_alert=True)
        
        # Возвращаемся к управлению админами
        await admin_management(callback)
    except Exception as e:
        logger.error(f"Error in admin_remove_confirm: {e}")
        await callback.answer("Ошибка", show_alert=True)

# Экспортируем функцию для использования в других модулях
__all__ = ['admin_show_bank', 'router']