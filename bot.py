# bot.py
import asyncio
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from config import config
from database.db import db
from database.queries import SubscriptionQueries, TaskQueries, UserQueries
from services.subscription_service import subscription_service
from webapp.server import start_webapp

# Импортируем все роутеры
from handlers import (
    start, language, tasks, profile, wallet,
    wheel, referrals, leaders, advertiser, admin,
    admin_tasks, admin_withdrawals, deposit, instructions, daily
)
from middlewares.language import LanguageMiddleware

# Настройка логирования
os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL)
logger.add("logs/bot.log", rotation="10 MB", level="INFO")

# Глобальные переменные — инициализируются в main()
bot: Bot = None
dp: Dispatcher = None


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
                        task = await TaskQueries.get_task_by_id(session, sub.task_id)
                        if task:
                            user = await UserQueries.get_user(session, sub.user_id)
                            if user and user.on_hold >= task.reward:
                                user.on_hold -= task.reward
                                user.balance += task.reward

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
                            success, message, points = await subscription_service.apply_penalty(
                                sub.user_id, sub.task_id
                            )

                            try:
                                await bot.send_message(
                                    sub.user_id,
                                    f"⚠️ <b>Обнаружена отписка!</b>\n\n{message}",
                                    parse_mode='HTML'
                                )
                            except:
                                pass

                            sub.is_active = False
                            await session.commit()

                    except Exception as e:
                        logger.error(f"Error checking subscription for user {sub.user_id}: {e}")

        except Exception as e:
            logger.error(f"Error in subscription checker: {e}")

        await asyncio.sleep(3600)


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Starting bot...")

    # Инициализация БД
    await db.initialize()
    await db.create_pool()

    # Инициализация банка
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
    global bot, dp

    # 1. Сначала запускаем Mini App сервер — Render увидит открытый порт
    webapp_port = int(os.environ.get("PORT", 8080))
    await start_webapp(host="0.0.0.0", port=webapp_port)
    logger.info(f"Mini App server listening on port {webapp_port}")

    # 2. Теперь инициализируем бота (если токен невалидный — сервер уже работает)
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    # Роутеры
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
    dp.include_router(daily.router)

    await on_startup()

    # Фоновый процесс для проверки подписок
    asyncio.create_task(subscription_checker())

    try:
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
