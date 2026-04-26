# bot.py
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage  # Заменяем RedisStorage на MemoryStorage
from loguru import logger
import sys
from datetime import datetime

from config import config
from database.db import db
from database.queries import SubscriptionQueries, TaskQueries, UserQueries
from services.subscription_service import subscription_service
from keep_alive import keep_alive

# Импортируем все роутеры
from handlers import (
    start, language, tasks, profile, wallet, 
    wheel, referrals, leaders, advertiser, admin,
    admin_tasks, admin_withdrawals, deposit, instructions
)
from middlewares.language import LanguageMiddleware

# Настройка логирования
logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL)
logger.add("logs/bot.log", rotation="10 MB", level="INFO")

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()  # Используем MemoryStorage
dp = Dispatcher(storage=storage)

# Регистрация middleware
dp.message.middleware(LanguageMiddleware())
dp.callback_query.middleware(LanguageMiddleware())

# Регистрация всех роутеров
dp.include_router(start.router)
dp.include_router(language.router)
dp.include_router(tasks.router)
dp.include_router(profile.router)
dp.include_router(wallet.router)
dp.include_router(wheel.router)
dp.include_router(referrals.router)
dp.include_router(leaders.router)
dp.include_router(advertiser.router)
dp.include_router(admin.router)
dp.include_router(admin_tasks.router)
dp.include_router(admin_withdrawals.router)
dp.include_router(deposit.router)
dp.include_router(instructions.router)

async def subscription_checker():
    """Фоновый процесс для проверки подписок"""
    while True:
        try:
            async with await db.get_session() as session:
                subscriptions = await SubscriptionQueries.get_all_active_subscriptions(session)
                
                for sub in subscriptions:
                    days_passed = (datetime.now() - sub.subscribed_at).days
                    
                    # Если прошло 5 дней - начисляем награду
                    if days_passed >= 5:
                        # Получаем задание
                        task = await TaskQueries.get_task_by_id(session, sub.task_id)
                        if task:
                            # Переводим с удержания на баланс
                            user = await UserQueries.get_user(session, sub.user_id)
                            if user and user.on_hold >= task.reward:
                                user.on_hold -= task.reward
                                user.balance += task.reward
                                
                                # Отправляем уведомление
                                try:
                                    await bot.send_message(
                                        sub.user_id,
                                        f"✅ <b>Награда зачислена!</b>\n\n"
                                        f"Вы успешно продержались подписанным 5 дней.\n"
                                        f"💰 {task.reward} USDT переведены с удержания на баланс.",
                                        parse_mode='HTML'
                                    )
                                except:
                                    pass
                        
                        # Завершаем отслеживание
                        sub.is_active = False
                        await session.commit()
                    
                    # Проверяем подписку
                    try:
                        chat_member = await bot.get_chat_member(
                            chat_id=f"@{sub.channel_username}",
                            user_id=sub.user_id
                        )
                        
                        is_subscribed = chat_member.status in ['member', 'administrator', 'creator']
                        
                        if not is_subscribed and days_passed < 5:
                            # Применяем штраф
                            success, message, points = await subscription_service.apply_penalty(
                                sub.user_id, sub.task_id
                            )
                            
                            # Отправляем уведомление
                            try:
                                await bot.send_message(
                                    sub.user_id,
                                    f"⚠️ <b>Обнаружена отписка!</b>\n\n{message}",
                                    parse_mode='HTML'
                                )
                            except:
                                pass
                            
                            # Деактивируем подписку
                            sub.is_active = False
                            await session.commit()
                            
                    except Exception as e:
                        logger.error(f"Error checking subscription for user {sub.user_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in subscription checker: {e}")
        
        await asyncio.sleep(3600)  # Проверка каждый час

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Starting bot...")
    
    # Инициализация БД
    await db.initialize()
    
    # Создаем пул соединений (для оптимизации)
    await db.create_pool()
    
    # Инициализация банка, если его нет
    async with await db.get_session() as session:
        from database.models import Bank
        balance = await Bank.get_balance(session)
        logger.info(f"Bank balance: {balance} USDT")
    
    # Устанавливаем команды бота
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Start the bot"),
        types.BotCommand(command="language", description="Change language"),
        types.BotCommand(command="admin", description="Admin panel"),
    ])
    
    me = await bot.get_me()
    logger.success(f"Bot @{me.username} started successfully")
    logger.info("Bot is ready! Open Telegram and send /start")
    logger.info(f"Mini App available at {config.WEBAPP_URL}")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Stopping bot...")
    await db.close()
    await bot.session.close()
    logger.success("Bot stopped")

async def main():
    """Главная функция"""
    # Запускаем Mini App веб-сервер (keep_alive для Render + Mini App API)
    keep_alive()
    
    await on_startup()
    
    # Запускаем фоновый процесс для проверки подписок
    asyncio.create_task(subscription_checker())
    
    try:
        # Запускаем polling с оптимизированными параметрами
        await dp.start_polling(
            bot, 
            skip_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"]
        )
    finally:
        await on_shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")