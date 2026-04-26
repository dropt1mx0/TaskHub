# handlers/profile.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from database.db import db
from database.queries import UserQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from services.task_service import TaskService
from utils.helpers import format_number
from config import config

router = Router()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показать профиль пользователя"""
    user_id = callback.from_user.id
    lang = 'ru'
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            
            if not user:
                await callback.answer("Пользователь не найден")
                return
            
            # Получаем статистику заданий
            task_stats = await TaskService.get_completed_tasks_stats(session, user_id)
            
            # Форматируем числа
            balance = format_number(user.balance)
            total_earned = format_number(user.total_earned)
            
            # Формируем текст профиля
            text = f"<b>{get_text('profile_title', lang)}</b>\n\n"
            text += get_text('profile_stats', lang,
                            balance=balance,
                            total_earned=total_earned,
                            tasks_completed=task_stats['count'],
                            streak=user.login_streak,
                            referrals=user.referral_count)
            
            if user.wallet_address:
                text += f"\n\nКошелек: <code>{user.wallet_address[:10]}...</code>"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboards.profile_menu(lang),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        await callback.answer("Ошибка загрузки профиля")