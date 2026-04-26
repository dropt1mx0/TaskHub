# utils/helpers.py
import random
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

def format_number(num: float, decimals: int = 3) -> str:
    """
    Форматирует число с плавающей точкой, убирая лишние нули и округляя до нужного количества знаков.
    Пример: 0.2000000001232 -> 0.2
    """
    if num is None:
        return "0"
    
    # Округляем до нужного количества знаков
    rounded = round(num, decimals)
    
    # Если число целое, возвращаем без десятичной части
    if rounded == int(rounded):
        return str(int(rounded))
    
    # Убираем лишние нули в конце
    return str(rounded).rstrip('0').rstrip('.') if '.' in str(rounded) else str(rounded)

def generate_referral_link(bot_username: str, user_id: int) -> str:
    """Сгенерировать реферальную ссылку"""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def get_time_until(target_time: datetime) -> Tuple[int, int]:
    """Получить время до target_time"""
    now = datetime.now()
    if target_time <= now:
        return 0, 0
    
    diff = target_time - now
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    return hours, minutes

def spin_wheel() -> float:
    """Крутить колесо фортуны"""
    from config import config
    return random.choices(
        config.WHEEL_PRIZES,
        weights=config.WHEEL_PRIZE_PROBABILITIES,
        k=1
    )[0]

def validate_wallet_address(address: str, currency: str) -> bool:
    """Валидация адреса кошелька"""
    address = address.strip()
    
    if currency == 'usdt' or currency == 'ton':
        # TON адреса: начинаются с EQ или UQ, длина 48 символов
        pattern = r'^(EQ|UQ)[A-Za-z0-9_-]{46}$'
        if re.match(pattern, address):
            return True
        
        # Также принимаем адреса в формате raw (числовые)
        if address.isdigit() and len(address) > 10:
            return True
    
    return False

def extract_channel_username(text: str) -> Optional[str]:
    """Извлечь username канала из ссылки или текста"""
    # Убираем пробелы
    text = text.strip()
    
    # Если это @username
    if text.startswith('@'):
        return text[1:]
    
    # Если это ссылка на Telegram
    patterns = [
        r'https?://t\.me/([a-zA-Z0-9_]+)',
        r'https?://telegram\.me/([a-zA-Z0-9_]+)',
        r't\.me/([a-zA-Z0-9_]+)',
        r'telegram\.me/([a-zA-Z0-9_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    # Если просто username
    if re.match(r'^[a-zA-Z0-9_]{5,}$', text):
        return text
    
    return None

def calculate_passive_income(task_reward: float) -> float:
    """Рассчитать пассивный доход для реферера"""
    from config import config
    return task_reward * config.REFERRAL_PASSIVE_PERCENT