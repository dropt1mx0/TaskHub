# handlers/leaders.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from database.db import db
from services.user_service import UserService
from keyboards.inline import InlineKeyboards
from utils.translations import get_text

router = Router()

@router.callback_query(F.data == "leaders")
async def show_leaders(callback: CallbackQuery, lang: str):
    """Показать таблицу лидеров"""
    try:
        async with await db.get_session() as session:
            leaders = await UserService.get_leaderboard(session, days=7)
            
            # Формируем текст на выбранном языке
            text = f"<b>{get_text('leaders_title', lang)}</b>\n\n"
            text += f"{get_text('leaders_prizes', lang)}\n\n"
            
            if leaders:
                for i, leader in enumerate(leaders, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    text += f"{medal} {leader['name']} — {leader['amount']} USDT\n"
            else:
                text += get_text('leaders_empty', lang)
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in leaders: {e}")
        await callback.answer("Error loading leaderboard")