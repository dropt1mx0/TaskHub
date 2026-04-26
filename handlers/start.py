# handlers/start.py
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from loguru import logger

from database.db import db
from database.queries import UserQueries, ReferralQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from config import config

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    logger.info(f"User {user_id} started the bot")
    
    try:
        # Парсим реферальную ссылку (deep link: /start ref_123456)
        referrer_id = None
        if command.args and command.args.startswith("ref_"):
            try:
                referrer_id = int(command.args[4:])
                if referrer_id == user_id:
                    referrer_id = None  # Нельзя пригласить самого себя
            except ValueError:
                referrer_id = None
        
        # Создаем или получаем пользователя
        async with await db.get_session() as session:
            user = await UserQueries.get_or_create(
                session,
                user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_premium=message.from_user.is_premium,
                language='ru'
            )
            
            # Обрабатываем реферальную ссылку (create_referral handles duplicates and bonuses)
            if referrer_id:
                try:
                    success = await ReferralQueries.create_referral(
                        session,
                        user_id=user_id,
                        referrer_id=referrer_id,
                        is_premium=message.from_user.is_premium or False
                    )
                    if success:
                        logger.info(f"Referral: {user_id} invited by {referrer_id}")
                except Exception as e:
                    logger.error(f"Error processing referral: {e}")
        
        # Приветственное сообщение (без баланса)
        welcome_text = get_text('welcome', 'ru', bot_name=config.BOT_NAME)
        
        await message.answer(
            welcome_text,
            reply_markup=InlineKeyboards.main_menu('ru'),
            parse_mode='HTML'
        )
        
        logger.success(f"Welcome message sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = 'ru'
        
        welcome_text = get_text('welcome', 'ru', bot_name=config.BOT_NAME)
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=InlineKeyboards.main_menu('ru'),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in back_to_main: {e}")
        await callback.answer("Ошибка")