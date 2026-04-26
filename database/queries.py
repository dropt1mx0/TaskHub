# database/queries.py
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from .models import (
    User, Task, CompletedTask, WheelSpin, 
    Withdrawal, Referral, AdminSetting, Deposit, Bank, 
    AntiCheatLog, DailyStats, Captcha, SubscriptionCheck
)
from loguru import logger
from config import config

class UserQueries:
    @staticmethod
    async def get_or_create(
        session: AsyncSession, 
        user_id: int, 
        **kwargs
    ) -> User:
        """Получить или создать пользователя"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Проверяем, пришел ли пользователь по реферальной ссылке
            referrer_id = kwargs.get('referrer_id')
            is_premium = kwargs.get('is_premium', False)
            
            user = User(
                user_id=user_id,
                username=kwargs.get('username'),
                first_name=kwargs.get('first_name'),
                last_name=kwargs.get('last_name'),
                is_premium=is_premium,
                language=kwargs.get('language', 'ru'),
                referrer_id=referrer_id
            )
            session.add(user)
            await session.flush()
            
            # Если есть реферер, обрабатываем реферальный бонус
            if referrer_id and referrer_id != user_id:
                await ReferralQueries.create_referral(
                    session, user_id, referrer_id, is_premium
                )
            
            await session.commit()
            logger.info(f"Новый пользователь создан: {user_id}")
        else:
            # Обновляем информацию при каждом входе
            user.username = kwargs.get('username', user.username)
            user.first_name = kwargs.get('first_name', user.first_name)
            user.last_name = kwargs.get('last_name', user.last_name)
            user.is_premium = kwargs.get('is_premium', user.is_premium)
            user.last_activity = datetime.now()
            
            # Обновляем streak
            await UserQueries.update_streak(session, user_id)
            
            await session.commit()
        
        return user
    
    @staticmethod
    async def update_streak(session: AsyncSession, user_id: int) -> int:
        """Обновить streak заходов"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            now = datetime.now()
            if user.last_login:
                # Если последний вход был вчера
                if (now.date() - user.last_login.date()).days == 1:
                    user.login_streak += 1
                # Если прошло больше дня
                elif (now.date() - user.last_login.date()).days > 1:
                    user.login_streak = 1
                # Если сегодня уже заходил - ничего не меняем
            else:
                user.login_streak = 1
            
            user.last_login = now
            await session.commit()
            return user.login_streak
        
        return 0
    
    @staticmethod
    async def update_balance(
        session: AsyncSession, 
        user_id: int, 
        amount: float, 
        hold: bool = False,
        task_completed: bool = False
    ) -> bool:
        """Обновить баланс пользователя"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            if hold:
                user.on_hold += amount
            else:
                user.balance += amount
            
            if amount > 0:
                user.total_earned += amount
            
            if task_completed:
                user.tasks_completed += 1
            
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_users(session: AsyncSession) -> List[User]:
        """Получить всех пользователей"""
        result = await session.execute(select(User))
        return result.scalars().all()
    
    @staticmethod
    async def get_users_count(session: AsyncSession) -> int:
        """Получить количество пользователей"""
        result = await session.execute(select(func.count(User.user_id)))
        return result.scalar() or 0
    
    @staticmethod
    async def get_new_users_count(session: AsyncSession, hours: int = 24) -> int:
        """Получить количество новых пользователей за последние N часов"""
        cutoff = datetime.now() - timedelta(hours=hours)
        result = await session.execute(
            select(func.count(User.user_id)).where(User.created_at >= cutoff)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def set_language(session: AsyncSession, user_id: int, language: str) -> bool:
        """Установить язык пользователя"""
        result = await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(language=language)
        )
        await session.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def set_wallet(session: AsyncSession, user_id: int, wallet: str) -> bool:
        """Установить адрес кошелька"""
        result = await session.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(wallet_address=wallet)
        )
        await session.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def reset_daily_tasks(session: AsyncSession, user_id: int) -> bool:
        """Сбросить дневные лимиты пользователя"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            now = datetime.now()
            if user.last_daily_reset and user.last_daily_reset.date() < now.date():
                user.daily_tasks = 0
                user.last_daily_reset = now
                await session.commit()
                return True
        
        return False
    
    @staticmethod
    async def increment_daily_tasks(session: AsyncSession, user_id: int) -> bool:
        """Увеличить счетчик дневных заданий"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            now = datetime.now()
            if not user.last_daily_reset or user.last_daily_reset.date() < now.date():
                user.daily_tasks = 1
                user.last_daily_reset = now
            else:
                user.daily_tasks += 1
            
            user.last_task_time = now
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def check_daily_limit(session: AsyncSession, user_id: int, limit: int = 50) -> bool:
        """Проверить дневной лимит заданий"""
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            now = datetime.now()
            if user.last_daily_reset and user.last_daily_reset.date() == now.date():
                return user.daily_tasks < limit
        
        return True

class TaskQueries:
    @staticmethod
    async def create_task(
        session: AsyncSession,
        title: str,
        description: str,
        reward: float,
        created_by: int,
        channel_url: str = None,
        channel_id: int = None,
        channel_username: str = None,
        task_type: str = 'channel_subscription'
    ) -> Task:
        """Создать новое задание"""
        task = Task(
            title=title,
            description=description,
            reward=reward,
            task_type=task_type,
            channel_url=channel_url,
            channel_id=channel_id,
            channel_username=channel_username,
            created_by=created_by,
            is_active=True
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        return task
    
    @staticmethod
    async def get_available_tasks(
        session: AsyncSession, 
        user_id: int
    ) -> List[Task]:
        """Получить доступные задания для пользователя"""
        # Получаем активные задания, которые пользователь еще не выполнял
        result = await session.execute(
            select(Task)
            .where(
                Task.is_active == True,
                Task.id.not_in(
                    select(CompletedTask.task_id).where(CompletedTask.user_id == user_id)
                )
            )
            .order_by(Task.created_at.desc())
        )
        
        return result.scalars().all()
    
    @staticmethod
    async def get_task_by_id(session: AsyncSession, task_id: int) -> Optional[Task]:
        """Получить задание по ID"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def complete_task(
        session: AsyncSession, 
        user_id: int, 
        task_id: int
    ) -> Optional[float]:
        """Отметить задание как выполненное"""
        # Проверяем, не выполнял ли пользователь это задание
        result = await session.execute(
            select(CompletedTask).where(
                CompletedTask.user_id == user_id,
                CompletedTask.task_id == task_id
            )
        )
        if result.scalar_one_or_none():
            return None
        
        # Получаем задание
        result = await session.execute(
            select(Task).where(Task.id == task_id, Task.is_active == True)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        # Создаем запись о выполнении
        completed = CompletedTask(
            user_id=user_id,
            task_id=task_id,
            reward_earned=task.reward
        )
        session.add(completed)
        
        # Обновляем статистику задания
        task.total_completions += 1
        
        # Если достигнут лимит, деактивируем задание
        if task.max_completions > 0 and task.total_completions >= task.max_completions:
            task.is_active = False
        
        await session.commit()
        return task.reward
    
    @staticmethod
    async def get_all_tasks(session: AsyncSession, active_only: bool = False) -> List[Task]:
        """Получить все задания"""
        query = select(Task)
        if active_only:
            query = query.where(Task.is_active == True)
        query = query.order_by(Task.created_at.desc())
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_tasks_by_creator(session: AsyncSession, creator_id: int) -> List[Task]:
        """Получить задания созданные пользователем"""
        result = await session.execute(
            select(Task)
            .where(Task.created_by == creator_id)
            .order_by(Task.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def toggle_task_status(session: AsyncSession, task_id: int) -> bool:
        """Переключить статус задания (активно/неактивно)"""
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if task:
            task.is_active = not task.is_active
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def delete_task(session: AsyncSession, task_id: int) -> bool:
        """Удалить задание"""
        result = await session.execute(
            delete(Task).where(Task.id == task_id)
        )
        await session.commit()
        return result.rowcount > 0
    
    @staticmethod
    async def get_completed_tasks(session: AsyncSession, user_id: int) -> List[CompletedTask]:
        """Получить выполненные задания пользователя"""
        result = await session.execute(
            select(CompletedTask)
            .where(CompletedTask.user_id == user_id)
            .order_by(CompletedTask.completed_at.desc())
        )
        return result.scalars().all()

class CompletedTaskQueries:
    @staticmethod
    async def get_user_completions(
        session: AsyncSession, 
        user_id: int,
        limit: int = 50
    ) -> List[CompletedTask]:
        """Получить историю выполненных заданий пользователя"""
        result = await session.execute(
            select(CompletedTask)
            .where(CompletedTask.user_id == user_id)
            .order_by(CompletedTask.completed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_task_completions(
        session: AsyncSession,
        task_id: int,
        limit: int = 50
    ) -> List[CompletedTask]:
        """Получить список выполнивших задание"""
        result = await session.execute(
            select(CompletedTask)
            .where(CompletedTask.task_id == task_id)
            .order_by(CompletedTask.completed_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_total_completions(session: AsyncSession) -> int:
        """Получить общее количество выполненных заданий"""
        result = await session.execute(select(func.count(CompletedTask.id)))
        return result.scalar() or 0

class ReferralQueries:
    @staticmethod
    async def create_referral(
        session: AsyncSession,
        user_id: int,
        referrer_id: int,
        is_premium: bool
    ) -> bool:
        """Создать реферальную связь"""
        if user_id == referrer_id:
            return False
        
        # Проверяем, не был ли уже зарегистрирован реферал
        result = await session.execute(
            select(Referral).where(
                Referral.user_id == user_id,
                Referral.referrer_id == referrer_id
            )
        )
        if result.scalar_one_or_none():
            return False
        
        # Создаем запись о реферале
        referral = Referral(
            user_id=user_id,
            referrer_id=referrer_id,
            is_premium=is_premium
        )
        session.add(referral)
        
        # Начисляем бонус рефереру
        bonus = config.REFERRAL_BONUS_PREMIUM if is_premium else config.REFERRAL_BONUS_REGULAR
        
        result = await session.execute(
            select(User).where(User.user_id == referrer_id)
        )
        referrer = result.scalar_one_or_none()
        
        if referrer:
            referrer.referral_earnings_direct += bonus
            referrer.on_hold += bonus
            referrer.referral_count += 1
            
            # Отмечаем бонус как выплаченный
            referral.bonus_paid = True
        
        await session.commit()
        return True
    
    @staticmethod
    async def update_referral_progress(
        session: AsyncSession,
        user_id: int,
        task_reward: float
    ):
        """Обновить прогресс реферала (после выполнения задания)"""
        # Находим, кто пригласил этого пользователя
        result = await session.execute(
            select(Referral).where(Referral.user_id == user_id)
        )
        referral = result.scalar_one_or_none()
        
        if not referral:
            return
        
        # Увеличиваем счетчик выполненных заданий
        referral.tasks_completed += 1
        
        # Если реферал выполнил достаточно заданий, активируем пассивный доход
        if referral.tasks_completed >= config.REFERRAL_PASSIVE_START and not referral.passive_active:
            referral.passive_active = True
        
        # Если пассивный доход активен, начисляем процент рефереру
        if referral.passive_active:
            passive_amount = task_reward * config.REFERRAL_PASSIVE_PERCENT
            
            # Начисляем рефереру
            result = await session.execute(
                select(User).where(User.user_id == referral.referrer_id)
            )
            referrer = result.scalar_one_or_none()
            
            if referrer:
                referrer.referral_earnings_passive += passive_amount
                referrer.on_hold += passive_amount
            
            # Сохраняем сумму в реферальной записи
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
                'created_at': referral.created_at.strftime('%d.%m.%Y')
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
                User.referral_count,
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

class WheelQueries:
    @staticmethod
    async def add_spin(
        session: AsyncSession,
        user_id: int,
        reward: float,
        is_free: bool = True
    ) -> WheelSpin:
        """Добавить запись о вращении"""
        spin = WheelSpin(
            user_id=user_id,
            reward=reward,
            is_free=is_free
        )
        session.add(spin)
        await session.commit()
        await session.refresh(spin)
        return spin
    
    @staticmethod
    async def get_last_free_spin(
        session: AsyncSession,
        user_id: int
    ) -> Optional[WheelSpin]:
        """Получить последнее бесплатное вращение"""
        result = await session.execute(
            select(WheelSpin)
            .where(
                WheelSpin.user_id == user_id,
                WheelSpin.is_free == True
            )
            .order_by(WheelSpin.spin_time.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_spins_count(
        session: AsyncSession,
        user_id: int,
        is_free: bool = None
    ) -> int:
        """Получить количество вращений"""
        query = select(func.count(WheelSpin.id)).where(WheelSpin.user_id == user_id)
        if is_free is not None:
            query = query.where(WheelSpin.is_free == is_free)
        
        result = await session.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def get_total_spins(session: AsyncSession) -> int:
        """Получить общее количество вращений"""
        result = await session.execute(select(func.count(WheelSpin.id)))
        return result.scalar() or 0

class WithdrawalQueries:
    @staticmethod
    async def create_withdrawal(
        session: AsyncSession,
        user_id: int,
        amount: float,
        withdrawal_type: str,
        wallet_address: str
    ) -> Withdrawal:
        """Создать заявку на вывод"""
        withdrawal = Withdrawal(
            user_id=user_id,
            amount=amount,
            withdrawal_type=withdrawal_type,
            wallet_address=wallet_address,
            status='pending'
        )
        session.add(withdrawal)
        await session.commit()
        await session.refresh(withdrawal)
        return withdrawal
    
    @staticmethod
    async def get_user_withdrawals(
        session: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[Withdrawal]:
        """Получить историю выводов пользователя"""
        result = await session.execute(
            select(Withdrawal)
            .where(Withdrawal.user_id == user_id)
            .order_by(Withdrawal.requested_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_pending_withdrawals(session: AsyncSession) -> List[Withdrawal]:
        """Получить все ожидающие выплаты"""
        result = await session.execute(
            select(Withdrawal)
            .where(Withdrawal.status == 'pending')
            .order_by(Withdrawal.requested_at.asc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_withdrawal_status(
        session: AsyncSession,
        withdrawal_id: int,
        status: str,
        processed_by: int = None,
        tx_hash: str = None
    ) -> bool:
        """Обновить статус выплаты"""
        result = await session.execute(
            select(Withdrawal).where(Withdrawal.id == withdrawal_id)
        )
        withdrawal = result.scalar_one_or_none()
        
        if withdrawal:
            withdrawal.status = status
            withdrawal.processed_at = datetime.now()
            if processed_by:
                withdrawal.processed_by = processed_by
            if tx_hash:
                withdrawal.tx_hash = tx_hash
            
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def get_total_withdrawn(session: AsyncSession) -> float:
        """Получить общую сумму выплат"""
        result = await session.execute(
            select(func.sum(Withdrawal.amount))
            .where(Withdrawal.status == 'completed')
        )
        return result.scalar() or 0.0

class DepositQueries:
    @staticmethod
    async def create_deposit(
        session: AsyncSession,
        user_id: int,
        amount: float,
        currency: str,
        comment: str
    ) -> Deposit:
        """Создать запись о депозите"""
        deposit = Deposit(
            user_id=user_id,
            amount=amount,
            currency=currency,
            comment=comment,
            status='pending'
        )
        session.add(deposit)
        await session.commit()
        await session.refresh(deposit)
        return deposit
    
    @staticmethod
    async def get_deposit_by_comment(session: AsyncSession, comment: str) -> Optional[Deposit]:
        """Получить депозит по комментарию"""
        result = await session.execute(
            select(Deposit).where(Deposit.comment == comment)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_deposit_status(
        session: AsyncSession,
        deposit_id: int,
        status: str,
        tx_hash: str = None
    ) -> bool:
        """Обновить статус депозита"""
        result = await session.execute(
            select(Deposit).where(Deposit.id == deposit_id)
        )
        deposit = result.scalar_one_or_none()
        
        if deposit:
            deposit.status = status
            deposit.completed_at = datetime.now()
            if tx_hash:
                deposit.tx_hash = tx_hash
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def get_pending_deposits(session: AsyncSession) -> List[Deposit]:
        """Получить все ожидающие депозиты"""
        result = await session.execute(
            select(Deposit).where(Deposit.status == 'pending')
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_user_deposits(
        session: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[Deposit]:
        """Получить историю депозитов пользователя"""
        result = await session.execute(
            select(Deposit)
            .where(Deposit.user_id == user_id)
            .order_by(Deposit.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

class CaptchaQueries:
    @staticmethod
    async def get_or_create(session: AsyncSession, user_id: int) -> Captcha:
        """Получить или создать запись капчи для пользователя"""
        result = await session.execute(
            select(Captcha).where(Captcha.user_id == user_id)
        )
        captcha = result.scalar_one_or_none()
        
        if not captcha:
            captcha = Captcha(
                user_id=user_id,
                task_visits=0,
                captcha_passed=True
            )
            session.add(captcha)
            await session.commit()
            await session.refresh(captcha)
        
        return captcha
    
    @staticmethod
    async def increment_task_visits(session: AsyncSession, user_id: int) -> int:
        """Увеличить счетчик посещений раздела заданий"""
        captcha = await CaptchaQueries.get_or_create(session, user_id)
        captcha.task_visits += 1
        captcha.captcha_passed = False
        await session.commit()
        return captcha.task_visits
    
    @staticmethod
    async def check_captcha_needed(session: AsyncSession, user_id: int) -> bool:
        """
        Проверить, нужна ли капча пользователю
        Возвращает True, если нужна капча
        """
        captcha = await CaptchaQueries.get_or_create(session, user_id)
        
        # Если пользователь уже прошел капчу при текущем визите, не показываем
        if captcha.captcha_passed:
            return False
        
        # Проверяем, кратно ли 5 количество посещений
        if captcha.task_visits % 5 == 0 and captcha.task_visits > 0:
            return True
        
        return False
    
    @staticmethod
    async def mark_captcha_passed(session: AsyncSession, user_id: int):
        """Отметить, что пользователь прошел капчу"""
        captcha = await CaptchaQueries.get_or_create(session, user_id)
        captcha.captcha_passed = True
        captcha.last_captcha_time = datetime.now()
        await session.commit()
    
    @staticmethod
    async def reset_captcha(session: AsyncSession, user_id: int):
        """Сбросить статус капчи (при неудачной попытке)"""
        captcha = await CaptchaQueries.get_or_create(session, user_id)
        captcha.captcha_passed = False
        await session.commit()

class SubscriptionQueries:
    @staticmethod
    async def create_subscription(
        session: AsyncSession,
        user_id: int,
        task_id: int,
        channel_username: str
    ) -> SubscriptionCheck:
        """Создать запись об отслеживании подписки"""
        subscription = SubscriptionCheck(
            user_id=user_id,
            task_id=task_id,
            channel_username=channel_username,
            subscribed_at=datetime.now(),
            is_active=True
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        return subscription
    
    @staticmethod
    async def get_active_subscription(
        session: AsyncSession,
        user_id: int,
        task_id: int
    ) -> Optional[SubscriptionCheck]:
        """Получить активную подписку"""
        result = await session.execute(
            select(SubscriptionCheck)
            .where(
                SubscriptionCheck.user_id == user_id,
                SubscriptionCheck.task_id == task_id,
                SubscriptionCheck.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_subscription(
        session: AsyncSession,
        user_id: int,
        task_id: int
    ) -> Optional[SubscriptionCheck]:
        """Получить запись о подписке"""
        result = await session.execute(
            select(SubscriptionCheck)
            .where(
                SubscriptionCheck.user_id == user_id,
                SubscriptionCheck.task_id == task_id
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_active_subscriptions(session: AsyncSession) -> List[SubscriptionCheck]:
        """Получить все активные подписки"""
        result = await session.execute(
            select(SubscriptionCheck)
            .where(SubscriptionCheck.is_active == True)
        )
        return result.scalars().all()
    
    @staticmethod
    async def deactivate_subscription(session: AsyncSession, user_id: int, task_id: int) -> bool:
        """Деактивировать подписку"""
        result = await session.execute(
            update(SubscriptionCheck)
            .where(
                SubscriptionCheck.user_id == user_id,
                SubscriptionCheck.task_id == task_id
            )
            .values(is_active=False)
        )
        await session.commit()
        return result.rowcount > 0

class AdminQueries:
    @staticmethod
    async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
        """Получить настройку"""
        result = await session.execute(
            select(AdminSetting).where(AdminSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None
    
    @staticmethod
    async def set_setting(session: AsyncSession, key: str, value: str, description: str = None) -> bool:
        """Установить настройку"""
        result = await session.execute(
            select(AdminSetting).where(AdminSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = AdminSetting(
                key=key,
                value=value,
                description=description
            )
            session.add(setting)
        
        await session.commit()
        return True
    
    @staticmethod
    async def get_stats(session: AsyncSession) -> Dict:
        """Получить полную статистику для админа"""
        # Количество пользователей
        users_count = await UserQueries.get_users_count(session)
        
        # Новые пользователи за 24 часа
        new_users = await UserQueries.get_new_users_count(session, 24)
        
        # Премиум пользователи
        result = await session.execute(
            select(func.count(User.user_id)).where(User.is_premium == True)
        )
        premium_users = result.scalar() or 0
        
        # Количество заданий
        tasks = await TaskQueries.get_all_tasks(session)
        tasks_count = len(tasks)
        
        # Выполненные задания
        completions = await CompletedTaskQueries.get_total_completions(session)
        
        # Общая сумма выплат
        total_withdrawn = await WithdrawalQueries.get_total_withdrawn(session)
        
        # Количество вращений
        total_spins = await WheelQueries.get_total_spins(session)
        
        # Ожидающие выплаты
        pending_withdrawals = len(await WithdrawalQueries.get_pending_withdrawals(session))
        
        # Ожидающие депозиты
        pending_deposits = len(await DepositQueries.get_pending_deposits(session))
        
        # Баланс банка
        from database.models import Bank
        bank_balance = await Bank.get_balance(session)
        
        return {
            'total_users': users_count,
            'new_users_24h': new_users,
            'premium_users': premium_users,
            'tasks_count': tasks_count,
            'completions': completions,
            'total_withdrawals': round(total_withdrawn, 3),
            'total_spins': total_spins,
            'pending_withdrawals': pending_withdrawals,
            'pending_deposits': pending_deposits,
            'bank_balance': round(bank_balance, 3)
        }