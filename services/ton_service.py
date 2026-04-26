# services/ton_service.py
import aiohttp
import hashlib
import random
from typing import Optional, Dict, Tuple, List
from loguru import logger
from config import config
import asyncio

class TONService:
    """Сервис для работы с TON API"""
    
    def __init__(self):
        self.api_url = config.TON_API_URL
        self.api_key = config.TON_API_KEY
        self.wallet_addresses = config.get_all_ton_addresses()
        # Словарь для отслеживания последнего использованного кошелька
        self.last_used_index = 0
        # Кэш для балансов (чтобы не делать слишком много запросов)
        self.balance_cache = {}
        self.last_balance_update = {}
    
    def get_next_wallet(self) -> str:
        """Получить следующий кошелек по кругу (round-robin)"""
        address = self.wallet_addresses[self.last_used_index]
        self.last_used_index = (self.last_used_index + 1) % len(self.wallet_addresses)
        return address
    
    def get_random_wallet(self) -> str:
        """Получить случайный кошелек"""
        return random.choice(self.wallet_addresses)
    
    def get_wallet_for_user(self, user_id: int) -> str:
        """
        Получить кошелек для конкретного пользователя
        Используем user_id для детерминированного выбора, чтобы один пользователь
        всегда видел один и тот же кошелек
        """
        index = user_id % len(self.wallet_addresses)
        return self.wallet_addresses[index]
    
    def get_all_wallets(self) -> List[str]:
        """Получить все кошельки"""
        return self.wallet_addresses
    
    async def get_wallet_balance(self, address: str) -> Optional[float]:
        """
        Получить баланс конкретного кошелька в TON
        """
        # Проверяем кэш (обновляем не чаще чем раз в 5 минут)
        import time
        current_time = time.time()
        if address in self.balance_cache and current_time - self.last_balance_update.get(address, 0) < 300:
            return self.balance_cache[address]
        
        if not self.api_key:
            logger.warning("TON API key not configured, using mock balance")
            # Для тестирования возвращаем случайный баланс
            mock_balance = round(random.uniform(10, 100), 2)
            self.balance_cache[address] = mock_balance
            self.last_balance_update[address] = current_time
            return mock_balance
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}getAddressBalance"
                params = {
                    "address": address
                }
                headers = {}
                if self.api_key:
                    headers["X-API-Key"] = self.api_key
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("ok") and data.get("result"):
                            # Баланс в наноTON
                            nano_balance = int(data["result"])
                            balance = nano_balance / 1_000_000_000
                            
                            # Сохраняем в кэш
                            self.balance_cache[address] = balance
                            self.last_balance_update[address] = current_time
                            
                            return balance
                    return None
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None
    
    async def get_all_wallets_balances(self) -> List[Dict[str, any]]:
        """
        Получить балансы всех кошельков
        """
        result = []
        for address in self.wallet_addresses:
            balance = await self.get_wallet_balance(address)
            result.append({
                'address': address,
                'balance': balance if balance is not None else 0,
                'balance_formatted': f"{balance:.2f}" if balance else "0.00"
            })
            # Небольшая задержка между запросами
            await asyncio.sleep(0.1)
        return result
    
    async def get_total_balance(self) -> float:
        """
        Получить суммарный баланс всех кошельков
        """
        balances = await self.get_all_wallets_balances()
        total = sum(w['balance'] for w in balances if w['balance'] is not None)
        return total
    
    async def generate_payment_link(self, amount: float, comment: str, wallet_address: str = None) -> str:
        """
        Генерирует ссылку для оплаты в TON
        Формат: ton://transfer/ADDRESS?amount=AMOUNT&text=COMMENT
        """
        # Если кошелек не указан, выбираем следующий по очереди
        if wallet_address is None:
            wallet_address = self.get_next_wallet()
        
        # Конвертируем сумму в наноTON (1 TON = 1e9 nanoTON)
        nano_amount = int(amount * 1_000_000_000)
        
        # Кодируем комментарий для URL
        import urllib.parse
        encoded_comment = urllib.parse.quote(comment)
        
        # Формируем ссылку
        link = f"ton://transfer/{wallet_address}?amount={nano_amount}&text={encoded_comment}"
        
        return link
    
    async def generate_qr_code(self, amount: float, comment: str, wallet_address: str = None) -> str:
        """
        Генерирует URL для QR-кода с платежом
        Использует API qrserver.com для создания QR-кода
        """
        payment_link = await self.generate_payment_link(amount, comment, wallet_address)
        import urllib.parse
        encoded_link = urllib.parse.quote(payment_link)
        
        # QR код с платежной ссылкой
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_link}"
        
        return qr_url
    
    async def check_transaction(self, comment: str, expected_amount: float) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Проверяет, была ли совершена транзакция с указанным комментарием
        Проверяет все кошельки
        """
        if not self.api_key:
            # Если нет API ключа, используем заглушку для тестирования
            logger.warning("TON API key not configured, using test mode")
            return True, expected_amount, "test_transaction_hash"
        
        try:
            # Проверяем каждый кошелек
            for wallet_address in self.wallet_addresses:
                # Получаем последние транзакции кошелька
                async with aiohttp.ClientSession() as session:
                    url = f"{self.api_url}getTransactions"
                    params = {
                        "address": wallet_address,
                        "limit": 10,
                        "archival": "true"
                    }
                    headers = {}
                    if self.api_key:
                        headers["X-API-Key"] = self.api_key
                    
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("ok") and data.get("result"):
                                for tx in data["result"]:
                                    # Проверяем комментарий в транзакции
                                    tx_comment = self._extract_comment(tx)
                                    if tx_comment == comment:
                                        # Проверяем сумму
                                        tx_amount = self._extract_amount(tx)
                                        if abs(tx_amount - expected_amount) < 0.01:  # Допустимая погрешность
                                            tx_hash = tx.get("transaction_id", {}).get("hash", "unknown")
                                            return True, tx_amount, tx_hash
                    
                    # Небольшая задержка между запросами к разным кошелькам
                    await asyncio.sleep(0.1)
            
            return False, None, None
        except Exception as e:
            logger.error(f"Error checking transaction: {e}")
            return False, None, None
    
    def _extract_comment(self, transaction: Dict) -> Optional[str]:
        """Извлекает комментарий из транзакции"""
        try:
            # В TON комментарии могут быть в разных местах
            if "in_msg" in transaction:
                msg = transaction["in_msg"]
                if "message" in msg:
                    # Декодируем из base64 или hex
                    import base64
                    try:
                        decoded = base64.b64decode(msg["message"]).decode('utf-8')
                        return decoded
                    except:
                        return msg["message"]
        except:
            pass
        return None
    
    def _extract_amount(self, transaction: Dict) -> float:
        """Извлекает сумму из транзакции (конвертирует из наноTON в TON)"""
        try:
            if "in_msg" in transaction:
                msg = transaction["in_msg"]
                if "value" in msg:
                    # Сумма в наноTON (1e9)
                    nano_amount = int(msg["value"])
                    return nano_amount / 1_000_000_000
        except:
            pass
        return 0.0
    
    def generate_comment(self, user_id: int, deposit_id: int) -> str:
        """
        Генерирует уникальный комментарий для платежа
        Формат: taskhub_USERID_DEPOSITID_TIMESTAMP
        """
        import time
        timestamp = int(time.time())
        comment = f"taskhub_{user_id}_{deposit_id}_{timestamp}"
        return comment
    
    async def verify_comment(self, comment: str, user_id: int, deposit_id: int) -> bool:
        """
        Проверяет, соответствует ли комментарий ожидаемому
        """
        parts = comment.split('_')
        if len(parts) >= 4 and parts[0] == 'taskhub':
            try:
                comment_user_id = int(parts[1])
                comment_deposit_id = int(parts[2])
                return comment_user_id == user_id and comment_deposit_id == deposit_id
            except:
                pass
        return False
    
    async def clear_cache(self):
        """Очистить кэш балансов"""
        self.balance_cache.clear()
        self.last_balance_update.clear()
        logger.info("TON balance cache cleared")

# Создаем глобальный экземпляр
ton_service = TONService()