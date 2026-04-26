# config.py
import os
import random
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    
    # ID главного администратора (владелец бота)
    OWNER_ID: int = 1708686259
    
    # ID администраторов
    ADMIN_IDS: List[int] = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    
    # База данных
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///taskhub.db')
    
    # Уровень логирования
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # TON Константы (загружаем из .env, запятая-разделитель)
    TON_ADDRESSES: List[str] = [x.strip() for x in os.getenv('TON_ADDRESSES', '').split(',') if x.strip()]
    
    # API ключ от toncenter.com
    TON_API_KEY: str = os.getenv('TON_API_KEY', '')
    TON_API_URL: str = "https://toncenter.com/api/v2/"
    
    # Минимальная сумма пополнения в TON
    MIN_DEPOSIT: float = 0.1
    
    # Минимальная сумма вывода в USDT
    MIN_WITHDRAWAL: float = 1.0
    
    # Комиссия сети TON
    TON_NETWORK_FEE: float = 0.05
    
    # Минимальная награда за задание (ИЗМЕНЕНО с 0.1 на 0.001)
    MIN_TASK_REWARD: float = 0.001  # 0.001 USDT = 0.1 цента
    
    # Минимальный баланс для создания задания
    MIN_BALANCE_FOR_TASK_CREATION: float = 0.5
    
    # Интервал между бесплатными вращениями колеса
    WHEEL_COOLDOWN_HOURS: int = 12
    
    # Стоимость платного вращения в USDT
    WHEEL_PAID_COST: float = 0.25
    
    # Реферальные бонусы
    REFERRAL_BONUS_REGULAR: float = 0.005
    REFERRAL_BONUS_PREMIUM: float = 0.05
    REFERRAL_PASSIVE_PERCENT: float = 0.9
    REFERRAL_PASSIVE_START: int = 20
    
    # Призы колеса фортуны
    WHEEL_PRIZES: list = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
    WHEEL_PRIZE_PROBABILITIES: list = [0.3, 0.25, 0.2, 0.1, 0.07, 0.05, 0.03]
    
    # Название бота
    BOT_NAME: str = "TaskHub"
    
    # Mini App (WebApp) settings
    # Render устанавливает PORT автоматически, keep_alive.py его читает
    WEBAPP_URL: str = os.getenv('WEBAPP_URL', 'https://taskhub-4bi4.onrender.com')  # URL от Render
    
    # Ссылки
    NEWS_CHANNEL: str = os.getenv('NEWS_CHANNEL', '')
    SUPPORT_LINK: str = os.getenv('SUPPORT_LINK', 'https://t.me/TheOpenEarnAD')
    
    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS
    
    def is_owner(self, user_id: int) -> bool:
        return user_id == self.OWNER_ID
    
    def get_random_ton_address(self) -> str:
        return random.choice(self.TON_ADDRESSES)
    
    def get_all_ton_addresses(self) -> List[str]:
        return self.TON_ADDRESSES

config = Config()