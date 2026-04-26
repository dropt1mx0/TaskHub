# handlers/admin_tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from datetime import datetime

from database.db import db
from database.queries import TaskQueries, UserQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.validators import validate_channel_link
from config import config

router = Router()

class AdminTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_reward = State()
    waiting_for_channel = State()
    waiting_for_confirmation = State()
    waiting_for_delete_reason = State()  # Новое состояние для причины удаления

def admin_required(func):
    async def wrapper(callback, *args, **kwargs):
        if callback.from_user.id not in config.ADMIN_IDS:
            await callback.answer("⛔️ Access denied", show_alert=True)
            return
        return await func(callback, *args, **kwargs)
    return wrapper

@router.callback_query(F.data == "admin_tasks")
@admin_required
async def admin_show_tasks(callback: CallbackQuery):
    """Показать список всех заданий"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
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
                    text += f"   👤 {get_text('created_by', lang)}: {task.created_by}\n"
                    text += f"   ➖➖➖➖➖➖\n"
        
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
                text += f"#{task.id}: {task.title} (by {task.created_by})\n"
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑 Delete #{task.id}",
                        callback_data=f"admin_delete_task_reason_{task.id}"
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

@router.callback_query(F.data.startswith("admin_delete_task_reason_"))
@admin_required
async def admin_delete_task_reason(callback: CallbackQuery, state: FSMContext):
    """Запросить причину удаления"""
    task_id = int(callback.data.split('_')[4])
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
            
            task = await TaskQueries.get_task_by_id(session, task_id)
            
            if not task:
                await callback.answer("Task not found", show_alert=True)
                return
            
            await state.update_data(task_id=task_id, task_title=task.title, creator_id=task.created_by)
            await state.set_state(AdminTaskStates.waiting_for_delete_reason)
            
            await callback.message.edit_text(
                f"📝 Enter reason for deleting task #{task_id}:\n\n"
                f"This reason will be sent to the task creator.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Cancel", callback_data="admin_tasks")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in admin_delete_task_reason: {e}")
        await callback.answer("Error", show_alert=True)

@router.message(AdminTaskStates.waiting_for_delete_reason)
@admin_required
async def admin_process_delete_reason(message: Message, state: FSMContext):
    """Обработка причины удаления и удаление задания"""
    data = await state.get_data()
    task_id = data.get('task_id')
    task_title = data.get('task_title')
    creator_id = data.get('creator_id')
    reason = message.text
    admin_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            # Удаляем задание
            success = await TaskQueries.delete_task(session, task_id)
            
            if success:
                logger.info(f"Admin {admin_id} deleted task #{task_id}")
                
                # Отправляем уведомление создателю
                try:
                    creator_text = f"❌ <b>Your task has been deleted</b>\n\n"
                    creator_text += f"Task: {task_title} (#{task_id})\n"
                    creator_text += f"Reason: {reason}\n\n"
                    creator_text += f"If you have questions, please contact support."
                    
                    await message.bot.send_message(
                        creator_id,
                        creator_text,
                        parse_mode='HTML'
                    )
                    logger.info(f"Notification sent to task creator {creator_id}")
                except Exception as e:
                    logger.error(f"Failed to notify task creator {creator_id}: {e}")
                
                await message.answer(
                    f"✅ Task #{task_id} deleted successfully.\n"
                    f"Notification sent to user {creator_id}.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Back to tasks", callback_data="admin_tasks")]
                    ])
                )
            else:
                await message.answer(
                    "❌ Failed to delete task.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Back", callback_data="admin_tasks")]
                    ])
                )
    except Exception as e:
        logger.error(f"Error in admin_process_delete_reason: {e}")
        await message.answer("Error deleting task")
    
    await state.clear()

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

# handlers/admin_tasks.py - обновляем функцию проверки награды

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
            # Проверяем минимальную награду (теперь 0.001)
            if reward < config.MIN_TASK_REWARD:
                await message.answer(
                    f"❌ Invalid reward. Minimum: {config.MIN_TASK_REWARD} USDT",
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