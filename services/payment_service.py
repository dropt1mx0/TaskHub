# services/payment_service.py
from typing import Optional, Tuple, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import re

from database.models import Withdrawal, User
from database.queries import WithdrawalQueries, UserQueries
from config import config

class PaymentService:
    """Сервис для работы с платежами (TON/USDT)"""
    
    @staticmethod
    def validate_ton_address(address: str) -> bool:
        """Валидация TON адреса"""
        address = address.strip()
        
        # TON адреса в формате: EQ... или UQ... (48 символов)
        if re.match(r'^(EQ|UQ)[A-Za-z0-9_-]{46}$', address):
            return True
        
        # Также поддерживаем raw адреса (числовые)
        if address.isdigit() and len(address) > 10:
            return True
        
        return False
    
    @staticmethod
    def validate_usdt_address(address: str) -> bool:
        """Валидация USDT адреса (на TON)"""
        # USDT на TON использует те же адреса
        return PaymentService.validate_ton_address(address)
    
    @staticmethod
    async def create_withdrawal(
        session: AsyncSession,
        user_id: int,
        amount: float,
        currency: str,  # 'ton' или 'usdt'
        wallet_address: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Создать заявку на вывод TON/USDT"""
        
        # Проверка минимальной суммы
        if amount < config.MIN_WITHDRAWAL:
            return False, None, f"Minimum amount: {config.MIN_WITHDRAWAL} {currency.upper()}"
        
        # Валидация адреса
        if currency == 'ton':
            if not PaymentService.validate_ton_address(wallet_address):
                return False, None, "Invalid TON address. Address must start with EQ or UQ"
        else:  # usdt
            if not PaymentService.validate_usdt_address(wallet_address):
                return False, None, "Invalid USDT address"
        
        # Получаем пользователя
        user = await UserQueries.get_user(session, user_id)
        if not user:
            return False, None, "User not found"
        
        # Проверка баланса
        if user.balance < amount:
            return False, None, f"Insufficient funds. Available: {user.balance} {currency.upper()}"
        
        # Создаем заявку
        withdrawal = await WithdrawalQueries.create_withdrawal(
            session,
            user_id,
            amount,
            currency,
            wallet_address
        )
        
        # Списываем с баланса
        user.balance -= amount
        await session.commit()
        
        result = {
            'id': withdrawal.id,
            'amount': withdrawal.amount,
            'currency': withdrawal.withdrawal_type.upper(),
            'wallet': withdrawal.wallet_address,
            'date': withdrawal.requested_at.strftime('%d.%m.%Y %H:%M'),
            'status': withdrawal.status
        }
        
        return True, result, None
    
    @staticmethod
    async def get_withdrawal_history(
        session: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Получить историю выводов"""
        withdrawals = await WithdrawalQueries.get_user_withdrawals(session, user_id, limit)
        
        result = []
        for w in withdrawals:
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(w.status, '⏳')
            
            result.append({
                'id': w.id,
                'amount': w.amount,
                'currency': w.withdrawal_type.upper(),
                'wallet': f"{w.wallet_address[:6]}...{w.wallet_address[-4:]}",
                'date': w.requested_at.strftime('%d.%m.%Y'),
                'status': w.status,
                'status_emoji': status_emoji,
                'tx_hash': w.tx_hash
            })
        
        return result
    
    @staticmethod
    async def calculate_ton_fee(amount: float) -> float:
        """Рассчитать комиссию в TON (примерно 0.05 TON)"""
        return config.TON_NETWORK_FEE
    
    @staticmethod
    async def format_withdrawal_info(withdrawal: Dict) -> str:
        """Форматировать информацию о выводе"""
        text = f"💳 <b>Withdrawal #{withdrawal['id']}</b>\n\n"
        text += f"💰 Amount: {withdrawal['amount']} {withdrawal['currency']}\n"
        text += f"📝 Address: <code>{withdrawal['wallet']}</code>\n"
        text += f"📅 Date: {withdrawal['date']}\n"
        text += f"📊 Status: {withdrawal['status_emoji']} {withdrawal['status']}\n"
        
        if withdrawal.get('tx_hash'):
            text += f"\n🔗 Tx: <code>{withdrawal['tx_hash']}</code>"
        
        return text