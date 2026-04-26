# services/referral_service.py
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Referral, CompletedTask
from config import config
from utils.helpers import calculate_passive_income

class ReferralService:
    @staticmethod
    async def process_referral_bonus(
        session: AsyncSession,
        user_id: int,
        task_reward: float
    ):
        """Обработать бонусы для реферера после выполнения задания"""
        # Находим, кто пригласил этого пользователя
        result = await session.execute(
            select(Referral).where(Referral.user_id == user_id)
        )
        referral = result.scalar_one_or_none()
        
        if not referral:
            return
        
        # Увеличиваем счетчик выполненных заданий
        referral.tasks_completed += 1
        await session.flush()
        
        # Проверяем, активировался ли пассивный доход
        if referral.tasks_completed >= config.REFERRAL_PASSIVE_START and not referral.passive_active:
            referral.passive_active = True
            await session.flush()
        
        # Получаем реферера
        result = await session.execute(
            select(User).where(User.user_id == referral.referrer_id)
        )
        referrer = result.scalar_one_or_none()
        
        if not referrer:
            return
        
        # Если пассивный доход активен, начисляем проценты
        if referral.passive_active:
            passive_amount = calculate_passive_income(task_reward)
            
            referrer.referral_earnings_passive += passive_amount
            referrer.on_hold += passive_amount
            referral.passive_earnings += passive_amount
        
        await session.commit()
    
    @staticmethod
    async def get_referral_stats(
        session: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить статистику реферальной программы"""
        # Количество рефералов
        result = await session.execute(
            select(func.count(Referral.id))
            .where(Referral.referrer_id == user_id)
        )
        count = result.scalar() or 0
        
        # Сумма прямых бонусов
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        direct = user.referral_earnings_direct if user else 0
        passive = user.referral_earnings_passive if user else 0
        on_hold = user.on_hold if user else 0
        
        # Список рефералов с их статистикой
        result = await session.execute(
            select(Referral, User)
            .join(User, Referral.user_id == User.user_id)
            .where(Referral.referrer_id == user_id)
            .order_by(Referral.created_at.desc())
            .limit(10)
        )
        
        referrals_list = []
        for referral, ref_user in result:
            referrals_list.append({
                'user_id': referral.user_id,
                'username': ref_user.username or ref_user.first_name or f"User_{ref_user.user_id}",
                'is_premium': referral.is_premium,
                'tasks_completed': referral.tasks_completed,
                'passive_earnings': round(referral.passive_earnings, 3),
                'created_at': referral.created_at
            })
        
        return {
            'count': count,
            'direct': round(direct, 3),
            'passive': round(passive, 3),
            'on_hold': round(on_hold, 3),
            'referrals': referrals_list
        }
    
    @staticmethod
    async def get_top_referrers(session: AsyncSession, limit: int = 10) -> List[Dict]:
        """Получить топ рефереров"""
        result = await session.execute(
            select(
                User.user_id,
                User.username,
                User.first_name,
                (User.referral_earnings_direct + User.referral_earnings_passive).label('total_earned')
            )
            .where(User.referral_count > 0)
            .order_by((User.referral_earnings_direct + User.referral_earnings_passive).desc())
            .limit(limit)
        )
        
        leaders = []
        for row in result:
            name = row.username or row.first_name or f"User_{row.user_id}"
            leaders.append({
                'name': name,
                'earned': round(row.total_earned, 3),
                'count': row.referral_count
            })
        
        return leaders