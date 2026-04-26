# services/wheel_service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, WheelSpin
from config import config
from utils.helpers import spin_wheel, get_time_until

class WheelService:
    @staticmethod
    async def can_spin_free(session: AsyncSession, user_id: int) -> Tuple[bool, Optional[int], Optional[int]]:
        """Проверить, может ли пользователь крутить бесплатно"""
        # Получаем последнее бесплатное вращение
        result = await session.execute(
            select(WheelSpin)
            .where(
                and_(
                    WheelSpin.user_id == user_id,
                    WheelSpin.is_free == True
                )
            )
            .order_by(WheelSpin.spin_time.desc())
            .limit(1)
        )
        last_spin = result.scalar_one_or_none()
        
        if not last_spin:
            # Никогда не крутил - можно
            return True, 0, 0
        
        # Проверяем, прошло ли 12 часов
        next_spin_time = last_spin.spin_time + timedelta(hours=config.WHEEL_COOLDOWN_HOURS)
        now = datetime.now()
        
        if now >= next_spin_time:
            return True, 0, 0
        else:
            hours, minutes = get_time_until(next_spin_time)
            return False, hours, minutes
    
    @staticmethod
    async def spin(
        session: AsyncSession, 
        user_id: int, 
        is_free: bool = True
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Выполнить вращение"""
        # Получаем пользователя
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False, None, "Пользователь не найден"
        
        # Если платное вращение, проверяем баланс
        if not is_free:
            if user.balance < config.WHEEL_PAID_COST:
                return False, None, "Недостаточно средств"
            
            # Списываем средства
            user.balance -= config.WHEEL_PAID_COST
        
        # Крутим колесо
        reward = spin_wheel()
        
        # Сохраняем вращение
        spin = WheelSpin(
            user_id=user_id,
            reward=reward,
            is_free=is_free
        )
        session.add(spin)
        
        await session.commit()
        
        return True, reward, None
    
    @staticmethod
    async def get_spin_history(
        session: AsyncSession, 
        user_id: int, 
        limit: int = 10
    ) -> list:
        """Получить историю вращений"""
        result = await session.execute(
            select(WheelSpin)
            .where(WheelSpin.user_id == user_id)
            .order_by(WheelSpin.spin_time.desc())
            .limit(limit)
        )
        return result.scalars().all()