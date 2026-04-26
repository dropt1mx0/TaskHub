# handlers/wheel.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from loguru import logger

from database.db import db
from services.wheel_service import WheelService
from services.user_service import UserService
from database.queries import UserQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.helpers import format_number
from config import config

router = Router()

@router.callback_query(F.data == "wheel")
async def show_wheel(callback: CallbackQuery, lang: str):
    """Показать колесо фортуны"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserService.get_user(session, user_id)
            if not user:
                await callback.answer("Ошибка!")
                return
            
            # Проверяем доступность бесплатного вращения
            can_spin, hours, minutes = await WheelService.can_spin_free(session, user_id)
            
            # Формируем текст на выбранном языке
            text = f"<b>{get_text('wheel_title', lang)}</b>\n\n"
            text += get_text('balance', lang, 
                           balance=format_number(user.balance)) + "\n\n"
            
            if can_spin:
                text += get_text('free_spin_available', lang)
            else:
                text += get_text('next_free_in', lang, hours=hours, minutes=minutes)
            
            # Создаем клавиатуру
            keyboard = InlineKeyboards.wheel_actions(can_spin, lang)
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in wheel: {e}")
        await callback.answer("Ошибка")

@router.callback_query(F.data == "spin_free")
async def spin_free(callback: CallbackQuery, lang: str):
    """Бесплатное вращение"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            # Проверяем, можно ли крутить
            can_spin, hours, minutes = await WheelService.can_spin_free(session, user_id)
            
            if not can_spin:
                await callback.answer(
                    f"Следующее бесплатное через {hours}ч {minutes}м",
                    show_alert=True
                )
                return
            
            # Крутим
            success, reward, error = await WheelService.spin(session, user_id, is_free=True)
            
            if success:
                logger.info(f"User {user_id} won {reward} USDT in free spin")
                
                # Начисляем сразу на баланс
                await UserQueries.update_balance(session, user_id, reward, hold=False)
                
                text = get_text('spin_result', lang, reward=format_number(reward))
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text('back', lang),
                        callback_data='back_to_main'
                    )]
                ])
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                await callback.answer(error or "Ошибка", show_alert=True)
    except Exception as e:
        logger.error(f"Error in spin_free: {e}")
        await callback.answer("Ошибка")

@router.callback_query(F.data == "spin_paid")
async def spin_paid(callback: CallbackQuery, lang: str):
    """Платное вращение"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            # Крутим
            success, reward, error = await WheelService.spin(session, user_id, is_free=False)
            
            if success:
                logger.info(f"User {user_id} won {reward} USDT in paid spin")
                
                # Начисляем сразу на баланс
                await UserQueries.update_balance(session, user_id, reward, hold=False)
                
                text = get_text('spin_result', lang, reward=format_number(reward))
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text('back', lang),
                        callback_data='back_to_main'
                    )]
                ])
                
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                await callback.answer(error or "Ошибка", show_alert=True)
    except Exception as e:
        logger.error(f"Error in spin_paid: {e}")
        await callback.answer("Ошибка")