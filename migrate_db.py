# migrate_db.py
import asyncio
import aiosqlite
from loguru import logger

async def migrate_database():
    """Миграция базы данных - добавление новых колонок"""
    
    async with aiosqlite.connect('taskhub.db') as db:
        # Проверяем существующие колонки
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Добавляем новые колонки, если их нет
        new_columns = [
            ('warning_points', 'INTEGER DEFAULT 0'),
            ('last_warning_date', 'TIMESTAMP'),
            ('account_created_date', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('subscription_start_time', 'TIMESTAMP'),
            ('subscription_task_id', 'INTEGER')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in column_names:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                logger.info(f"Added column {col_name}")
        
        # Создаем новую таблицу subscription_checks
        await db.execute('''
            CREATE TABLE IF NOT EXISTS subscription_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_id INTEGER,
                channel_username TEXT,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                warning_count INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # Создаем индексы
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_subscription_user_task 
            ON subscription_checks(user_id, task_id)
        ''')
        
        await db.commit()
        logger.success("Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate_database())