# services/subscription_service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple
from loguru import logger
from database.db import db
from database.queries import UserQueries, TaskQueries, SubscriptionQueries
from config import config

class SubscriptionService:
    """Сервис для проверки и мониторинга подписок"""
    
    def __init__(self):
        # Минимальное время подписки (5 дней)
        self.min_subscription_days = 5
        # Максимальное количество предупреждений
        self.max_warnings = 3
        # Штраф за отписку
        self.penalty_amount = 0.5  # 0.5 USDT штрафа
    
    async def check_user_age(self, user_id: int) -> Tuple[bool, int]:
        """
        Проверяет, сколько дней пользователь в боте
        Возвращает (достаточно_ли_дней, количество_дней)
        """
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            if not user:
                return False, 0
            
            days_in_bot = (datetime.now() - user.created_at).days
            return days_in_bot >= self.min_subscription_days, days_in_bot
    
    async def start_subscription_tracking(self, user_id: int, task_id: int, channel_username: str) -> bool:
        """
        Начинает отслеживание подписки после выполнения задания
        """
        async with await db.get_session() as session:
            # Проверяем, не отслеживается ли уже
            existing = await SubscriptionQueries.get_active_subscription(session, user_id, task_id)
            if existing:
                return False
            
            # Создаем запись об отслеживании
            subscription = await SubscriptionQueries.create_subscription(
                session, user_id, task_id, channel_username
            )
            
            # Обновляем пользователя
            user = await UserQueries.get_user(session, user_id)
            user.subscription_start_time = datetime.now()
            user.subscription_task_id = task_id
            await session.commit()
            
            logger.info(f"Started tracking subscription for user {user_id} on task {task_id}")
            return True
    
    async def check_subscription_status(self, user_id: int, task_id: int, bot) -> Tuple[bool, Optional[str]]:
        """
        Проверяет статус подписки и возвращает (все_еще_подписан, сообщение)
        """
        async with await db.get_session() as session:
            subscription = await SubscriptionQueries.get_active_subscription(session, user_id, task_id)
            if not subscription:
                return False, "Subscription not found"
            
            # Проверяем подписку
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=f"@{subscription.channel_username}",
                    user_id=user_id
                )
                
                is_subscribed = chat_member.status in ['member', 'administrator', 'creator']
                
                # Обновляем время последней проверки
                subscription.last_checked = datetime.now()
                await session.commit()
                
                return is_subscribed, None
                
            except Exception as e:
                logger.error(f"Error checking subscription: {e}")
                return False, "Channel unavailable"
    
    async def apply_penalty(self, user_id: int, task_id: int) -> Tuple[bool, str, int]:
        """Применяет штраф за отписку - списывает полученную награду"""
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            subscription = await SubscriptionQueries.get_active_subscription(session, user_id, task_id)
            task = await TaskQueries.get_task_by_id(session, task_id)
            
            if not subscription or not task:
                return False, "Подписка или задание не найдены", user.warning_points if user else 0
            
            # Увеличиваем счетчик предупреждений
            subscription.warning_count += 1
            user.warning_points += 1
            user.last_warning_date = datetime.now()
            
            # Получаем сумму награды за задание
            reward_amount = task.reward
            penalty_msg = ""
            
            # Списываем с баланса (нет удержания)
            if user.balance >= reward_amount:
                user.balance -= reward_amount
                penalty_msg = f"Списано {reward_amount} USDT (возврат награды)"
            else:
                user.balance = 0
                penalty_msg = f"Недостаточно средств для возврата награды {reward_amount} USDT. Баланс обнулен."
            
            # Если достигнут лимит предупреждений - блокируем
            if user.warning_points >= self.max_warnings:
                user.is_blocked = True
                user.block_reason = "Многократная отписка от каналов"
                block_msg = " Аккаунт заблокирован!"
            else:
                block_msg = ""
            
            await session.commit()
            
            message = f"⚠️ Обнаружена отписка от канала! {penalty_msg}. Штрафные очки: {user.warning_points}/{self.max_warnings}{block_msg}"
            return True, message, user.warning_points
    
    async def complete_subscription_tracking(self, user_id: int, task_id: int) -> bool:
        """Завершает отслеживание подписки (после 5 дней)"""
        async with await db.get_session() as session:
            subscription = await SubscriptionQueries.get_active_subscription(session, user_id, task_id)
            if subscription:
                subscription.is_active = False
                await session.commit()
                logger.info(f"Completed subscription tracking for user {user_id} on task {task_id}")
                return True
            return False
    
    async def get_subscription_days(self, user_id: int, task_id: int) -> int:
        """Возвращает количество дней, прошедших с подписки"""
        async with await db.get_session() as session:
            subscription = await SubscriptionQueries.get_subscription(session, user_id, task_id)
            if subscription:
                days = (datetime.now() - subscription.subscribed_at).days
                return days
            return 0

# Создаем глобальный экземпляр
subscription_service = SubscriptionService()