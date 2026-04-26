# handlers/referrals.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from database.db import db
from database.queries import UserQueries, ReferralQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.helpers import generate_referral_link
from config import config

router = Router()

@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery, lang: str):
    """Показать реферальную программу"""
    user_id = callback.from_user.id
    
    try:
        # Получаем username бота
        bot_username = (await callback.bot.get_me()).username
        
        async with await db.get_session() as session:
            # Получаем статистику
            stats = await ReferralQueries.get_referral_stats(session, user_id)
            
            # Генерируем ссылку
            link = generate_referral_link(bot_username, user_id)
            
            # Формируем текст
            text = f"<b>{get_text('referral_title', lang)}</b>\n\n"
            text += f"{get_text('your_link', lang, link=link)}\n\n"
            text += get_text('referral_stats', lang,
                            count=stats['count'],
                            total=stats['direct'] + stats['passive'],
                            hold=stats['on_hold'])
            text += get_text('referral_bonuses', lang)
            
            # Если есть рефералы, показываем последних
            if stats['referrals']:
                text += "\n\nRecent referrals:\n"
                for ref in stats['referrals'][:5]:
                    premium = "⭐" if ref['is_premium'] else "👤"
                    text += f"{premium} {ref['username']} - {ref['tasks_completed']} tasks\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in referrals: {e}")
        await callback.answer("Error loading referral program")