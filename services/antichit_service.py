# services/antichit_service.py
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import asyncio

class AntiCheatService:
    """Сервис для защиты от накруток и абуза"""
    
    def __init__(self):
        # Хранилище для отслеживания действий пользователей
        self.user_actions = defaultdict(list)
        self.suspicious_ips = set()
        self.blocked_users = set()
        
    async def check_task_abuse(self, user_id: int, task_id: int) -> bool:
        """Проверка на абуз заданий"""
        now = datetime.now()
        key = f"{user_id}_{task_id}"
        
        # Очищаем старые записи (старше 1 часа)
        self.user_actions[key] = [
            t for t in self.user_actions[key] 
            if (now - t).total_seconds() < 3600
        ]
        
        # Проверяем частоту выполнения
        if len(self.user_actions[key]) >= 3:
            return False  # Слишком часто
        
        self.user_actions[key].append(now)
        return True
    
    async def check_withdrawal_abuse(self, user_id: int, amount: float) -> bool:
        """Проверка на абуз выводов"""
        now = datetime.now()
        
        # Проверяем количество выводов за последние 24 часа
        withdrawals = [
            w for w in self.user_actions[f"withdraw_{user_id}"]
            if isinstance(w, dict) and (now - w['time']).total_seconds() < 86400
        ]
        self.user_actions[f"withdraw_{user_id}"] = withdrawals
        
        if len(withdrawals) >= 5:  # Не больше 5 выводов в день
            return False
        
        # Проверяем общую сумму за день
        total_amount = sum(w['amount'] for w in withdrawals)
        if total_amount + amount > 100:  # Не больше 100 USDT в день
            return False
        
        self.user_actions[f"withdraw_{user_id}"].append({
            'time': now,
            'amount': amount
        })
        
        return True
    
    async def check_subscription_abuse(self, user_id: int, channel_id: str) -> bool:
        """Проверка на абуз подписок"""
        now = datetime.now()
        
        # Проверяем количество подписок за последний час
        subscriptions = [
            t for t in self.user_actions[f"sub_{user_id}"]
            if (now - t).total_seconds() < 3600
        ]
        
        if len(subscriptions) >= 10:  # Не больше 10 подписок в час
            return False
        
        self.user_actions[f"sub_{user_id}"].append(now)
        return True
    
    async def check_suspicious_activity(self, user_id: int, ip: str = None) -> bool:
        """Проверка на подозрительную активность"""
        if user_id in self.blocked_users:
            return False
        
        if ip and ip in self.suspicious_ips:
            self.blocked_users.add(user_id)
            return False
        
        return True
    
    async def block_user(self, user_id: int, reason: str = "Abuse"):
        """Заблокировать пользователя"""
        self.blocked_users.add(user_id)
        # Здесь можно добавить запись в БД о блокировке
        
    async def unblock_user(self, user_id: int):
        """Разблокировать пользователя"""
        self.blocked_users.discard(user_id)

# Создаем глобальный экземпляр
anti_cheat = AntiCheatService()