# utils/validators.py
import re
from typing import Optional, Tuple

def validate_amount(amount_str: str, min_amount: float = 0.5) -> Tuple[bool, Optional[float], Optional[str]]:
    """Проверить корректность суммы"""
    try:
        # Заменяем запятую на точку и убираем пробелы
        cleaned = amount_str.strip().replace(',', '.')
        amount = float(cleaned)
        
        if amount < min_amount:
            return False, None, f"Minimum amount: {min_amount} USDT"
        
        if amount > 10000:
            return False, None, "Maximum amount: 10000 USDT"
        
        # Округляем до 3 знаков
        amount = round(amount, 3)
        
        return True, amount, None
    except ValueError:
        return False, None, "Invalid number. Please enter a valid amount."

def validate_channel_link(link: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Проверить ссылку на канал"""
    link = link.strip()
    
    # Паттерны для Telegram каналов
    patterns = [
        r'^@([a-zA-Z0-9_]{5,})$',
        r'^https?://t\.me/([a-zA-Z0-9_]+)$',
        r'^https?://telegram\.me/([a-zA-Z0-9_]+)$',
        r'^t\.me/([a-zA-Z0-9_]+)$',
        r'^([a-zA-Z0-9_]{5,})$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, link)
        if match:
            username = match.group(1)
            return True, username, None
    
    return False, None, "Invalid channel link. Example: @channel or https://t.me/channel"