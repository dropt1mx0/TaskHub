# handlers/instructions.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from keyboards.inline import InlineKeyboards
from utils.translations import get_text

router = Router()

# Хранилище последних сообщений для каждого пользователя
last_messages = {}

@router.callback_query(F.data == "instructions")
async def show_instructions_menu(callback: CallbackQuery, lang: str):
    """Показать меню инструкций"""
    user_id = callback.from_user.id
    
    try:
        text = "📋 <b>Инструкция по использованию бота</b>\n\nВыберите интересующий вас раздел:"
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst")
        
        if text != last_text:
            last_messages[f"{user_id}_inst"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in instructions menu: {e}")
        await callback.answer("Error")

@router.callback_query(F.data == "inst_earn")
async def show_earn_instruction(callback: CallbackQuery, lang: str):
    """Показать инструкцию по заработку"""
    user_id = callback.from_user.id
    
    try:
        text = get_text('inst_earn_text', lang)
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst_earn")
        
        if text != last_text:
            last_messages[f"{user_id}_inst_earn"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in earn instruction: {e}")
        await callback.answer("Error")

@router.callback_query(F.data == "inst_withdraw")
async def show_withdraw_instruction(callback: CallbackQuery, lang: str):
    """Показать инструкцию по выводу"""
    user_id = callback.from_user.id
    
    try:
        text = get_text('inst_withdraw_text', lang)
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst_withdraw")
        
        if text != last_text:
            last_messages[f"{user_id}_inst_withdraw"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in withdraw instruction: {e}")
        await callback.answer("Error")

@router.callback_query(F.data == "inst_referrals")
async def show_referrals_instruction(callback: CallbackQuery, lang: str):
    """Показать инструкцию по рефералам"""
    user_id = callback.from_user.id
    
    try:
        text = get_text('inst_referrals_text', lang)
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst_referrals")
        
        if text != last_text:
            last_messages[f"{user_id}_inst_referrals"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in referrals instruction: {e}")
        await callback.answer("Error")

@router.callback_query(F.data == "inst_wheel")
async def show_wheel_instruction(callback: CallbackQuery, lang: str):
    """Показать инструкцию по колесу фортуны"""
    user_id = callback.from_user.id
    
    try:
        text = get_text('inst_wheel_text', lang)
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst_wheel")
        
        if text != last_text:
            last_messages[f"{user_id}_inst_wheel"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in wheel instruction: {e}")
        await callback.answer("Error")

@router.callback_query(F.data == "inst_advertiser")
async def show_advertiser_instruction(callback: CallbackQuery, lang: str):
    """Показать инструкцию для рекламодателей"""
    user_id = callback.from_user.id
    
    try:
        text = get_text('inst_advertiser_text', lang)
        keyboard = InlineKeyboards.instructions_menu(lang)
        
        # Проверяем, изменилось ли сообщение
        last_text = last_messages.get(f"{user_id}_inst_advertiser")
        
        if text != last_text:
            last_messages[f"{user_id}_inst_advertiser"] = text
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in advertiser instruction: {e}")
        await callback.answer("Error")