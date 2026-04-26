# services/captcha_service.py
import random
import string
from typing import Tuple, Optional, Dict, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import hashlib
import time

class CaptchaService:
    """Сервис для генерации и проверки капчи"""
    
    def __init__(self):
        self.secret_key = "taskhub_captcha_secret_key_2024"
        # Хранилище для отслеживания попыток (в реальном проекте использовать Redis)
        self.attempts: Dict[int, int] = {}
        # Хранилище для ввода многоцифровых ответов
        self.user_input: Dict[int, str] = {}
    
    def generate_captcha(self) -> Tuple[str, str, InlineKeyboardMarkup, int]:
        """
        Генерирует капчу и возвращает (текст_для_показа, правильный_ответ, клавиатура, правильный_результат)
        """
        # Генерируем два случайных числа от 1 до 10
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        
        # Выбираем случайную операцию
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            result = num1 + num2
            question = f"{num1} + {num2} = ?"
        elif operation == '-':
            # Убеждаемся, что результат неотрицательный
            if num1 < num2:
                num1, num2 = num2, num1
            result = num1 - num2
            question = f"{num1} - {num2} = ?"
        else:  # *
            num1 = random.randint(1, 5)
            num2 = random.randint(1, 5)
            result = num1 * num2
            question = f"{num1} × {num2} = ?"
        
        # Генерируем хеш ответа для проверки
        answer_hash = self._hash_answer(str(result))
        
        # Создаем клавиатуру с цифрами
        keyboard = self._create_number_keyboard(answer_hash, result)
        
        return question, answer_hash, keyboard, result
    
    def _hash_answer(self, answer: str) -> str:
        """Создает хеш ответа для безопасной передачи"""
        timestamp = str(int(time.time() // 60))  # Округляем до минуты
        data = f"{answer}:{timestamp}:{self.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def verify_answer(self, user_answer: str, answer_hash: str) -> bool:
        """
        Проверяет правильность ответа
        """
        # Проверяем с текущей минутой и предыдущей (на случай перехода)
        current_minute = str(int(time.time() // 60))
        prev_minute = str(int(time.time() // 60) - 1)
        
        for minute in [current_minute, prev_minute]:
            data = f"{user_answer}:{minute}:{self.secret_key}"
            computed_hash = hashlib.sha256(data.encode()).hexdigest()[:16]
            if computed_hash == answer_hash:
                return True
        
        return False
    
    def _create_number_keyboard(self, answer_hash: str, correct_answer: int) -> InlineKeyboardMarkup:
        """Создает клавиатуру с цифрами для ввода ответа"""
        # Создаем перемешанный список цифр от 0 до 9
        numbers = list(range(10))
        random.shuffle(numbers)
        
        keyboard = []
        row = []
        
        for i, num in enumerate(numbers):
            row.append(
                InlineKeyboardButton(
                    text=str(num),
                    callback_data=f"captcha_num_{num}_{answer_hash}"
                )
            )
            
            # По 3 кнопки в ряд
            if (i + 1) % 3 == 0:
                keyboard.append(row)
                row = []
        
        # Добавляем оставшиеся кнопки
        if row:
            keyboard.append(row)
        
        # Добавляем кнопки управления
        control_row = []
        
        # Кнопка подтверждения (только если ответ больше 9)
        if correct_answer > 9:
            control_row.append(
                InlineKeyboardButton(text="✅ OK", callback_data=f"captcha_submit_{answer_hash}")
            )
        
        # Кнопка очистки
        control_row.append(
            InlineKeyboardButton(text="⌫ Clear", callback_data=f"captcha_clear_{answer_hash}")
        )
        
        # Кнопка сброса
        control_row.append(
            InlineKeyboardButton(text="⟲ Reset", callback_data=f"captcha_reset_{answer_hash}")
        )
        
        keyboard.append(control_row)
        
        # Кнопка отмены
        keyboard.append([
            InlineKeyboardButton(text="✖ Cancel", callback_data="captcha_cancel")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    def generate_text_captcha(self) -> Tuple[str, str]:
        """Генерирует текстовую капчу (для отправки сообщением)"""
        # Генерируем 4 случайные буквы
        letters = ''.join(random.choices(string.ascii_uppercase, k=4))
        
        # Добавляем случайные цифры для сложности
        digits = ''.join(random.choices(string.digits, k=2))
        
        # Перемешиваем
        captcha = list(letters + digits)
        random.shuffle(captcha)
        captcha_text = ''.join(captcha)
        
        # Хешируем ответ
        answer_hash = self._hash_answer(captcha_text)
        
        return captcha_text, answer_hash
    
    def increment_attempts(self, user_id: int) -> int:
        """Увеличивает счетчик попыток для пользователя"""
        self.attempts[user_id] = self.attempts.get(user_id, 0) + 1
        return self.attempts[user_id]
    
    def get_attempts(self, user_id: int) -> int:
        """Возвращает количество попыток для пользователя"""
        return self.attempts.get(user_id, 0)
    
    def reset_attempts(self, user_id: int):
        """Сбрасывает счетчик попыток"""
        if user_id in self.attempts:
            del self.attempts[user_id]
    
    def add_digit(self, user_id: int, digit: str) -> str:
        """Добавляет цифру к текущему вводу пользователя"""
        if user_id not in self.user_input:
            self.user_input[user_id] = ""
        
        # Ограничиваем длину ввода (максимум 2 цифры, так как примеры до 20)
        if len(self.user_input[user_id]) < 2:
            self.user_input[user_id] += digit
        
        return self.user_input[user_id]
    
    def clear_input(self, user_id: int) -> str:
        """Очищает текущий ввод пользователя"""
        if user_id in self.user_input:
            self.user_input[user_id] = ""
        return ""
    
    def get_input(self, user_id: int) -> str:
        """Возвращает текущий ввод пользователя"""
        return self.user_input.get(user_id, "")
    
    def reset_input(self, user_id: int):
        """Сбрасывает ввод пользователя"""
        if user_id in self.user_input:
            del self.user_input[user_id]

# Создаем глобальный экземпляр
captcha_service = CaptchaService()