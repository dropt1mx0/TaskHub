# services/user_service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Referral, CompletedTask, WheelSpin, Withdrawal
from database.queries import UserQueries
from config import config
from utils.helpers import format_number

class UserService:
    @staticmethod
    async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
        """Получить пользователя"""
        return await UserQueries.get_user(session, user_id)
    
    @staticmethod
    async def update_balance(
        session: AsyncSession, 
        user_id: int, 
        amount: float,
        hold: bool = False,
        task_completed: bool = False
    ) -> bool:
        """Обновить баланс пользователя"""
        return await UserQueries.update_balance(session, user_id, amount, hold, task_completed)
    
    @staticmethod
    async def get_leaderboard(session: AsyncSession, days: int = 7) -> List[Dict]:
        """Получить таблицу лидеров за период"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Получаем топ пользователей по заработку за период
        result = await session.execute(
            select(
                User.user_id,
                User.username,
                User.first_name,
                func.sum(CompletedTask.reward_earned).label('total_earned')
            )
            .join(CompletedTask, User.user_id == CompletedTask.user_id)
            .where(CompletedTask.completed_at >= cutoff_date)
            .group_by(User.user_id)
            .order_by(func.sum(CompletedTask.reward_earned).desc())
            .limit(10)
        )
        
        leaders = []
        for row in result:
            name = row.username or row.first_name or f"User_{row.user_id}"
            leaders.append({
                'user_id': row.user_id,
                'name': name,
                'amount': round(row.total_earned or 0, 3)
            })
        
        return leaders
    
    @staticmethod
    async def get_stats(session: AsyncSession) -> Dict:
        """Получить общую статистику (для админа)"""
        # Общее количество пользователей
        result = await session.execute(select(func.count(User.user_id)))
        total_users = result.scalar()
        
        # Новые пользователи за 24 часа
        cutoff = datetime.now() - timedelta(days=1)
        result = await session.execute(
            select(func.count(User.user_id)).where(User.created_at >= cutoff)
        )
        new_users = result.scalar()
        
        # Общая сумма выплат
        result = await session.execute(
            select(func.sum(Withdrawal.amount)).where(Withdrawal.status == 'completed')
        )
        total_withdrawals = result.scalar() or 0
        
        # Количество заданий
        result = await session.execute(select(func.count()).select_from(CompletedTask))
        total_completions = result.scalar()
        
        return {
            'total_users': total_users,
            'new_users_24h': new_users,
            'total_withdrawals': round(total_withdrawals, 3),
            'total_completions': total_completions
        }