# database/db.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text
from loguru import logger
from config import config
from .models import Base

class Database:
    def __init__(self):
        self.engine = None
        self._session_maker = None
        self._initialized = False
        self._pool = None
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        try:
            # Определяем параметры пула в зависимости от типа БД
            if 'sqlite' in config.DATABASE_URL:
                # Для SQLite используем NullPool (каждое соединение отдельно)
                poolclass = NullPool
                pool_args = {}
                logger.info("Using SQLite database with NullPool")
            else:
                # Для PostgreSQL используем QueuePool с оптимизированными параметрами
                poolclass = QueuePool
                pool_args = {
                    'pool_size': 20,           # Максимальное количество соединений в пуле
                    'max_overflow': 10,         # Дополнительные соединения при пиковой нагрузке
                    'pool_timeout': 30,          # Таймаут ожидания соединения
                    'pool_recycle': 3600,        # Пересоздавать соединения каждый час
                    'pool_pre_ping': True        # Проверять соединение перед использованием
                }
                logger.info(f"Using PostgreSQL database with connection pool (size: {pool_args['pool_size']})")
            
            # Создаем движок с правильными параметрами
            self.engine = create_async_engine(
                config.DATABASE_URL,
                echo=False,                      # Не выводить SQL запросы (для производительности)
                poolclass=poolclass,
                future=True,
                **pool_args
            )
            
            # Создаем фабрику сессий
            self._session_maker = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Создание таблиц
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Миграция: добавляем новые колонки если их нет
            await self._run_migrations()
            
            self._initialized = True
            logger.success(f"Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _run_migrations(self):
        """Применить миграции (добавление новых колонок)"""
        migrations = [
            ("users", "last_daily_claim", "DATETIME"),
        ]
        async with self.engine.begin() as conn:
            for table, column, col_type in migrations:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    logger.info(f"Migration: added {table}.{column}")
                except Exception:
                    pass  # Колонка уже существует
    
    async def create_pool(self):
        """Создать пул соединений (для оптимизации)"""
        if self.engine and 'postgresql' in config.DATABASE_URL:
            try:
                # Прогрев пула - создаем несколько соединений заранее
                async with self.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection pool warmed up")
            except Exception as e:
                logger.warning(f"Could not warm up connection pool: {e}")
    
    async def close(self):
        """Закрытие подключения к БД"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    async def get_session(self) -> AsyncSession:
        """Получение сессии БД с повторными попытками при ошибках"""
        if not self._initialized:
            await self.initialize()
        
        if not self._session_maker:
            raise Exception("Database not initialized. Call initialize() first.")
        
        # Пытаемся получить сессию с повторными попытками
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                session = self._session_maker()
                # Проверяем, что сессия рабочая (только для PostgreSQL)
                if 'postgresql' in config.DATABASE_URL:
                    await session.execute(text("SELECT 1"))
                return session
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database session error (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to get database session after {max_retries} attempts: {e}")
                    raise
    
    @property
    def is_initialized(self) -> bool:
        """Проверка инициализации"""
        return self._initialized
    
    async def health_check(self) -> bool:
        """Проверка здоровья БД"""
        try:
            async with await self.get_session() as session:
                if 'postgresql' in config.DATABASE_URL:
                    await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Получить статистику БД"""
        stats = {
            'initialized': self._initialized,
            'database_url': config.DATABASE_URL.split('@')[-1] if '@' in config.DATABASE_URL else 'local',
        }
        
        if self.engine and hasattr(self.engine, 'pool'):
            if hasattr(self.engine.pool, 'size'):
                stats['pool_size'] = self.engine.pool.size()
            if hasattr(self.engine.pool, 'checkedin'):
                stats['checkedin_connections'] = self.engine.pool.checkedin()
            if hasattr(self.engine.pool, 'overflow'):
                stats['overflow'] = self.engine.pool.overflow()
        
        return stats

# Создаем экземпляр БД
db = Database()