# handlers/daily.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime
from loguru import logger

from database.db import db
from database.queries import UserQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.helpers import format_number
from config import config

router = Router()


@router.callback_query(F.data == "daily_bonus")
async def show_daily_bonus(callback: CallbackQuery, lang: str):
    """Показать ежедневный бонус"""
    user_id = callback.from_user.id

    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            if not user:
                await callback.answer("Пользователь не найден")
                return

            streak = user.login_streak or 0
            if streak == 0:
                streak = 1
            day_index = (streak - 1) % len(config.DAILY_REWARDS)
            rewards = config.DAILY_REWARDS

            now = datetime.now()
            already_claimed = False
            if user.last_daily_claim:
                already_claimed = user.last_daily_claim.date() == now.date()

            # Формируем текст с календарем дней
            text = f"🎁 <b>{get_text('daily_title', lang)}</b>\n\n"
            text += f"🔥 {get_text('daily_streak', lang)}: <b>{streak}</b> {_plural_days(streak)}\n\n"

            for i, r in enumerate(rewards):
                if i < day_index:
                    text += f"  ✅ День {i+1}: {r} USDT\n"
                elif i == day_index:
                    if already_claimed:
                        text += f"  ✅ День {i+1}: {r} USDT (получено)\n"
                    else:
                        text += f"  👉 <b>День {i+1}: {r} USDT</b>\n"
                else:
                    text += f"  ⬜ День {i+1}: {r} USDT\n"

            if already_claimed:
                text += f"\n✅ {get_text('daily_already_claimed', lang)}"
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text('back', lang),
                        callback_data='back_to_main'
                    )]
                ])
            else:
                text += f"\n💰 {get_text('daily_claim_prompt', lang, reward=rewards[day_index])}"
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"🎁 Забрать +{rewards[day_index]} USDT",
                        callback_data='daily_claim'
                    )],
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
    except Exception as e:
        logger.error(f"Error in daily bonus: {e}")
        await callback.answer("Ошибка")


@router.callback_query(F.data == "daily_claim")
async def claim_daily_bonus(callback: CallbackQuery, lang: str):
    """Забрать ежедневный бонус"""
    user_id = callback.from_user.id

    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            if not user:
                await callback.answer("Пользователь не найден")
                return

            now = datetime.now()
            if user.last_daily_claim and user.last_daily_claim.date() == now.date():
                await callback.answer(
                    get_text('daily_already_claimed', lang),
                    show_alert=True
                )
                return

            streak = user.login_streak or 0
            if streak == 0:
                streak = 1
            day_index = (streak - 1) % len(config.DAILY_REWARDS)
            reward = config.DAILY_REWARDS[day_index]

            # Начисляем
            user.balance += reward
            user.total_earned += reward
            user.last_daily_claim = now
            await session.commit()

            logger.info(f"User {user_id} claimed daily bonus: +{reward} USDT (day {day_index+1}, streak {streak})")

            text = (
                f"🎉 <b>{get_text('daily_claimed_success', lang)}</b>\n\n"
                f"💰 +{reward} USDT\n"
                f"🔥 {get_text('daily_streak', lang)}: {streak} {_plural_days(streak)}\n"
                f"💵 {get_text('balance', lang, balance=format_number(user.balance))}"
            )

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    except Exception as e:
        logger.error(f"Error claiming daily bonus: {e}")
        await callback.answer("Ошибка")


def _plural_days(n: int) -> str:
    """Склонение слова 'день'"""
    abs_n = abs(n) % 100
    last = abs_n % 10
    if abs_n > 10 and abs_n < 20:
        return "дней"
    if last > 1 and last < 5:
        return "дня"
    if last == 1:
        return "день"
    return "дней"
