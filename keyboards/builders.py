from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional
from utils.translations import get_text

class KeyboardBuilder:
    @staticmethod
    def main_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [InlineKeyboardButton(text=get_text('tasks', lang), callback_data='tasks')],
            [
                InlineKeyboardButton(text=get_text('withdraw', lang), callback_data='withdraw'),
                InlineKeyboardButton(text=get_text('profile', lang), callback_data='profile')
            ],
            [
                InlineKeyboardButton(text=get_text('wheel', lang), callback_data='wheel'),
                InlineKeyboardButton(text=get_text('referrals', lang), callback_data='referrals')
            ],
            [
                InlineKeyboardButton(text=get_text('leaders', lang), callback_data='leaders'),
                InlineKeyboardButton(text=get_text('advertiser', lang), callback_data='advertiser')
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def with_back(text: str, callback: str, lang: str = 'ru', show_home: bool = True) -> InlineKeyboardMarkup:
        """Клавиатура с кнопкой назад"""
        keyboard = []
        
        if callback:
            keyboard.append([InlineKeyboardButton(text=text, callback_data=callback)])
        
        back_buttons = []
        if show_home:
            back_buttons.append(InlineKeyboardButton(text=get_text('home', lang), callback_data='back_to_main'))
        back_buttons.append(InlineKeyboardButton(text=get_text('back', lang), callback_data='back_to_previous'))
        
        keyboard.append(back_buttons)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def language_selector() -> InlineKeyboardMarkup:
        """Выбор языка"""
        keyboard = [
            [
                InlineKeyboardButton(text='🇷🇺 Русский', callback_data='lang_ru'),
                InlineKeyboardButton(text='🇺🇦 Українська', callback_data='lang_uk')
            ],
            [
                InlineKeyboardButton(text='🇬🇧 English', callback_data='lang_en'),
                InlineKeyboardButton(text='🇰🇿 Қазақша', callback_data='lang_kz')
            ],
            [InlineKeyboardButton(text='◀️ Назад', callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def tasks_list(tasks: List, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Список заданий"""
        keyboard = []
        for task in tasks:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{task.title} (+{task.reward} USDT)", 
                    callback_data=f"task_{task.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text=get_text('home', lang), callback_data='back_to_main')
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def task_action(task_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Действия с заданием"""
        keyboard = [
            [InlineKeyboardButton(text=get_text('complete_task', lang), callback_data=f"complete_{task_id}")],
            [InlineKeyboardButton(text=get_text('back', lang), callback_data='tasks')]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def withdraw_methods(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Методы вывода"""
        keyboard = [
            [
                InlineKeyboardButton(text=get_text('usdt', lang), callback_data='withdraw_usdt'),
                InlineKeyboardButton(text=get_text('ton', lang), callback_data='withdraw_ton')
            ],
            [InlineKeyboardButton(text=get_text('back', lang), callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def wheel_actions(has_free: bool, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Действия с колесом фортуны"""
        keyboard = []
        
        if has_free:
            keyboard.append([InlineKeyboardButton(text="🎰 Бесплатно", callback_data='spin_free')])
        
        keyboard.append([InlineKeyboardButton(
            text=get_text('spin_paid', lang, cost=0.25), 
            callback_data='spin_paid'
        )])
        
        keyboard.append([InlineKeyboardButton(text=get_text('back', lang), callback_data='back_to_main')])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)