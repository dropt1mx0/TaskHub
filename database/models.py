# database/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, BigInteger, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language = Column(String(10), default='en')
    is_premium = Column(Boolean, default=False)
    
    # Баланс и статистика
    balance = Column(Float, default=0.0)
    on_hold = Column(Float, default=0.0)
    total_earned = Column(Float, default=0.0)
    tasks_completed = Column(Integer, default=0)
    login_streak = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    
    # Реферальная система
    referrer_id = Column(BigInteger, nullable=True, index=True)
    referral_count = Column(Integer, default=0)
    referral_earnings_direct = Column(Float, default=0.0)
    referral_earnings_passive = Column(Float, default=0.0)
    
    # Античит и безопасность
    last_task_time = Column(DateTime, nullable=True)
    daily_tasks = Column(Integer, default=0)
    last_daily_reset = Column(DateTime, nullable=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(255), nullable=True)
    suspicious_count = Column(Integer, default=0)
    
    # НОВЫЕ ПОЛЯ ДЛЯ ПРОВЕРКИ ПОДПИСОК
    warning_points = Column(Integer, default=0)  # Штрафные очки (от 1 до 3)
    last_warning_date = Column(DateTime, nullable=True)  # Дата последнего предупреждения
    account_created_date = Column(DateTime, default=func.now())  # Дата создания аккаунта
    subscription_start_time = Column(DateTime, nullable=True)  # Время начала подписки на канал
    subscription_task_id = Column(Integer, nullable=True)  # ID задания, за которым следим
    
    created_at = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Ежедневный бонус
    last_daily_claim = Column(DateTime, nullable=True)  # Дата последнего получения дневного бонуса
    
    # Кошелек
    wallet_address = Column(String(255), nullable=True)
    
    # Отношения
    completed_tasks = relationship("CompletedTask", back_populates="user", cascade="all, delete-orphan")
    wheel_spins = relationship("WheelSpin", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")
    deposits = relationship("Deposit", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("SubscriptionCheck", back_populates="user", cascade="all, delete-orphan")
    referrals_given = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referrals_received = relationship("Referral", foreign_keys="Referral.user_id", back_populates="user")

class Referral(Base):
    __tablename__ = 'referrals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    referrer_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    tasks_completed = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    bonus_paid = Column(Boolean, default=False)
    passive_earnings = Column(Float, default=0.0)
    passive_active = Column(Boolean, default=False)
    last_activity = Column(DateTime, nullable=True)
    
    user = relationship("User", foreign_keys=[user_id], back_populates="referrals_received")
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_given")
    
    __table_args__ = (
        Index('idx_referral_unique', 'user_id', 'referrer_id', unique=True),
    )

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    reward = Column(Float, nullable=False)
    task_type = Column(String(50), default='channel_subscription')
    
    # Для подписки на канал
    channel_id = Column(BigInteger, nullable=True)
    channel_username = Column(String(255), nullable=True)
    channel_url = Column(String(255), nullable=True)
    
    # Для перехода по ссылке
    link_url = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    total_completions = Column(Integer, default=0)
    max_completions = Column(Integer, default=0)
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    completions = relationship("CompletedTask", back_populates="task", cascade="all, delete-orphan")
    subscriptions = relationship("SubscriptionCheck", back_populates="task", cascade="all, delete-orphan")

class CompletedTask(Base):
    __tablename__ = 'completed_tasks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    completed_at = Column(DateTime, default=func.now())
    reward_earned = Column(Float, nullable=False)
    ip_address = Column(String(50), nullable=True)  # Для античита
    user_agent = Column(String(255), nullable=True)  # Для античита
    
    user = relationship("User", back_populates="completed_tasks")
    task = relationship("Task", back_populates="completions")
    
    __table_args__ = (
        Index('idx_user_task_completed', 'user_id', 'task_id', unique=True),
    )

class WheelSpin(Base):
    __tablename__ = 'wheel_spins'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    spin_time = Column(DateTime, default=func.now())
    reward = Column(Float, nullable=False)
    is_free = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="wheel_spins")

class Withdrawal(Base):
    __tablename__ = 'withdrawals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    amount = Column(Float, nullable=False)
    withdrawal_type = Column(String(20), nullable=False)  # usdt, ton
    wallet_address = Column(String(255), nullable=False)
    status = Column(String(20), default='pending')  # pending, completed, failed
    tx_hash = Column(String(255), nullable=True)
    requested_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(BigInteger, nullable=True)  # ID админа, который обработал
    
    user = relationship("User", back_populates="withdrawals")

class Deposit(Base):
    __tablename__ = 'deposits'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='ton')  # ton, usdt
    comment = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), default='pending')  # pending, completed, failed
    tx_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="deposits")
    
    def __repr__(self):
        return f"<Deposit(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"

class Bank(Base):
    __tablename__ = 'bank'
    
    id = Column(Integer, primary_key=True)
    balance = Column(Float, default=0.0)
    total_deposits = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    @staticmethod
    async def get_balance(session):
        """Получить баланс банка"""
        from sqlalchemy import select
        result = await session.execute(select(Bank).limit(1))
        bank = result.scalar_one_or_none()
        if not bank:
            bank = Bank()
            session.add(bank)
            await session.commit()
        return bank.balance
    
    @staticmethod
    async def add_funds(session, amount: float, description: str = ""):
        """Добавить средства в банк"""
        from sqlalchemy import select
        result = await session.execute(select(Bank).limit(1))
        bank = result.scalar_one_or_none()
        if not bank:
            bank = Bank()
            session.add(bank)
        
        bank.balance += amount
        bank.total_deposits += amount
        bank.last_updated = datetime.now()
        await session.commit()
        return bank.balance
    
    @staticmethod
    async def withdraw_funds(session, amount: float, description: str = ""):
        """Списать средства из банка"""
        from sqlalchemy import select
        result = await session.execute(select(Bank).limit(1))
        bank = result.scalar_one_or_none()
        if not bank:
            return False
        
        if bank.balance < amount:
            return False
        
        bank.balance -= amount
        bank.total_withdrawals += amount
        bank.last_updated = datetime.now()
        await session.commit()
        return True

class Captcha(Base):
    __tablename__ = 'captcha'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    task_visits = Column(Integer, default=0)  # Счетчик посещений раздела заданий
    last_captcha_time = Column(DateTime, nullable=True)
    captcha_passed = Column(Boolean, default=True)  # Прошла ли капча при последнем входе
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_captcha_user', 'user_id'),
    )

class SubscriptionCheck(Base):
    __tablename__ = 'subscription_checks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    channel_username = Column(String(255), nullable=False)
    subscribed_at = Column(DateTime, default=func.now())
    last_checked = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    warning_count = Column(Integer, default=0)  # Количество предупреждений за эту подписку
    
    user = relationship("User", back_populates="subscriptions")
    task = relationship("Task", back_populates="subscriptions")
    
    __table_args__ = (
        Index('idx_subscription_user_task', 'user_id', 'task_id'),
    )

class AdminSetting(Base):
    __tablename__ = 'admin_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger, nullable=True)
    
    def __repr__(self):
        return f"<AdminSetting(key={self.key}, value={self.value})>"

class AntiCheatLog(Base):
    __tablename__ = 'anticheat_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    action = Column(String(50), nullable=False)  # task_spam, withdrawal_abuse, etc
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_anticheat_user', 'user_id', 'created_at'),
    )

class DailyStats(Base):
    __tablename__ = 'daily_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=func.now())
    new_users = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    withdrawals_requested = Column(Integer, default=0)
    withdrawals_amount = Column(Float, default=0.0)
    deposits_count = Column(Integer, default=0)
    deposits_amount = Column(Float, default=0.0)
    wheel_spins = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_daily_stats_date', 'date'),
    )