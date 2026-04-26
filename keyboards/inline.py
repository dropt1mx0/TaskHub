# keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from utils.translations import get_text
from config import config

class InlineKeyboards:
    """Класс для создания всех инлайн клавиатур бота"""
    
    @staticmethod
    def main_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            # Mini App button (opens the WebApp)
            [InlineKeyboardButton(
                text="🚀 Open TaskHub App",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )],
            [InlineKeyboardButton(
                text=get_text('tasks', lang), 
                callback_data='tasks'
            )],
            [InlineKeyboardButton(
                text=get_text('instructions', lang), 
                callback_data='instructions'
            )],
            [
                InlineKeyboardButton(
                    text=get_text('withdraw', lang), 
                    callback_data='withdraw'
                ),
                InlineKeyboardButton(
                    text=get_text('profile', lang), 
                    callback_data='profile'
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text('wheel', lang), 
                    callback_data='wheel'
                ),
                InlineKeyboardButton(
                    text=get_text('referrals', lang), 
                    callback_data='referrals'
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text('leaders', lang), 
                    callback_data='leaders'
                ),
                InlineKeyboardButton(
                    text=get_text('advertiser', lang), 
                    callback_data='advertiser'
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def instructions_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Меню инструкции"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('inst_earn', lang),
                callback_data="inst_earn"
            )],
            [InlineKeyboardButton(
                text=get_text('inst_withdraw', lang),
                callback_data="inst_withdraw"
            )],
            [InlineKeyboardButton(
                text=get_text('inst_referrals', lang),
                callback_data="inst_referrals"
            )],
            [InlineKeyboardButton(
                text=get_text('inst_wheel', lang),
                callback_data="inst_wheel"
            )],
            [InlineKeyboardButton(
                text=get_text('inst_advertiser', lang),
                callback_data="inst_advertiser"
            )],
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def back_button(callback: str = 'back_to_main', lang: str = 'ru') -> InlineKeyboardMarkup:
        """Только кнопка назад"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('back', lang), 
                callback_data=callback
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def home_button(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Только кнопка домой"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('main_menu', lang), 
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def back_and_home(back_callback: str, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Кнопки назад и домой"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=get_text('back', lang), 
                    callback_data=back_callback
                ),
                InlineKeyboardButton(
                    text=get_text('main_menu', lang), 
                    callback_data='back_to_main'
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def tasks_list(tasks: list, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Список заданий"""
        keyboard = []
        for task in tasks:
            button_text = f"{task['title']} (+{task['reward']} USDT)"
            callback_data = f"task_{task['id']}"
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text=get_text('main_menu', lang),
                callback_data='back_to_main'
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def task_detail(task_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Детали задания"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('complete_task', lang),
                callback_data=f"complete_{task_id}"
            )],
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='tasks'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def withdraw_methods(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Методы вывода"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text=get_text('usdt', lang), 
                    callback_data='withdraw_usdt'
                ),
                InlineKeyboardButton(
                    text=get_text('ton', lang), 
                    callback_data='withdraw_ton'
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text('back', lang),
                    callback_data='back_to_main'
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def profile_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Меню профиля (без смены языка)"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def wheel_actions(can_spin_free: bool, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Действия с колесом фортуны"""
        keyboard = []
        
        if can_spin_free:
            keyboard.append([
                InlineKeyboardButton(
                    text='Бесплатное вращение',
                    callback_data='spin_free'
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text=get_text('spin_paid', lang),
                callback_data='spin_paid'
            )
        ])
        
        keyboard.append([
            InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def spin_result(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Результат вращения - только кнопка назад"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def leaders_list(leaders: list, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Таблица лидеров"""
        keyboard = []
        
        if leaders:
            for i, leader in enumerate(leaders[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text = f"{medal} {leader['name']} - {leader['amount']} USDT"
                keyboard.append([InlineKeyboardButton(text=text, callback_data=f"leader_{leader['user_id']}")])
        
        keyboard.append([
            InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def referrals_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Меню рефералов"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def admin_panel(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Админ панель"""
        keyboard = [
            [InlineKeyboardButton(
                text='📊 ' + get_text('admin_stats', lang), 
                callback_data='admin_stats'
            )],
            [InlineKeyboardButton(
                text='📢 ' + get_text('admin_broadcast', lang), 
                callback_data='admin_broadcast'
            )],
            [InlineKeyboardButton(
                text='💳 ' + get_text('admin_withdrawals', lang), 
                callback_data='admin_withdrawals'
            )],
            [InlineKeyboardButton(
                text='📋 ' + get_text('admin_tasks', lang), 
                callback_data='admin_tasks'
            )],
            [InlineKeyboardButton(
                text='➕ ' + get_text('create_task', lang), 
                callback_data='admin_create_task'
            )],
            [InlineKeyboardButton(
                text='💰 ' + get_text('bank_balance', lang, balance=''), 
                callback_data='admin_bank'
            )],
            [InlineKeyboardButton(
                text='👥 Управление админами', 
                callback_data='admin_management'
            )],
            [InlineKeyboardButton(
                text='🏠 ' + get_text('main_menu', lang), 
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def admin_back(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Кнопка назад в админке"""
        keyboard = [
            [InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='admin_back'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def confirm_action(confirm_callback: str, cancel_callback: str, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Подтверждение действия"""
        keyboard = [
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_callback),
                InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_callback)
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def withdrawals_list(withdrawals: list, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Список выплат для админа"""
        keyboard = []
        for w in withdrawals[:5]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"💰 {w['amount']} USDT - {w['user']}",
                    callback_data=f"admin_process_withdrawal_{w['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='admin_back'
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def withdrawal_action(withdrawal_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Действия с выплатой"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ " + get_text('approve', lang),
                    callback_data=f"admin_approve_{withdrawal_id}"
                ),
                InlineKeyboardButton(
                    text="❌ " + get_text('reject', lang),
                    callback_data=f"admin_reject_{withdrawal_id}"
                )
            ],
            [InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='admin_withdrawals'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def advertiser_menu(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Меню рекламодателя"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('create_task', lang), 
                callback_data='advertiser_create_task'
            )],
            [InlineKeyboardButton(
                text=get_text('my_tasks', lang), 
                callback_data='advertiser_my_tasks'
            )],
            [InlineKeyboardButton(
                text=get_text('deposit', lang), 
                callback_data='advertiser_deposit'
            )],
            [InlineKeyboardButton(
                text=get_text('back', lang), 
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def advertiser_tasks_list(tasks: list, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Список заданий рекламодателя"""
        keyboard = []
        for task in tasks[:5]:
            status = "✅" if task.is_active else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {task.title} ({task.total_completions} выполнений)",
                    callback_data=f"advertiser_task_{task.id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='advertiser'
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def task_management(task_id: int, is_active: bool, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Управление заданием для админа"""
        status_text = "Деактивировать" if is_active else "Активировать"
        status_callback = f"admin_toggle_task_{task_id}"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text=status_text,
                    callback_data=status_callback
                ),
                InlineKeyboardButton(
                    text="Удалить",
                    callback_data=f"admin_delete_task_{task_id}"
                )
            ],
            [InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='admin_tasks'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def deposit_methods(lang: str = 'ru') -> InlineKeyboardMarkup:
        """Методы пополнения"""
        keyboard = [
            [
                InlineKeyboardButton(
                    text='💎 USDT', 
                    callback_data='deposit_usdt'
                ),
                InlineKeyboardButton(
                    text='⚡️ TON', 
                    callback_data='deposit_ton'
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_text('back', lang),
                    callback_data='back_to_main'
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def wallet_history(lang: str = 'ru') -> InlineKeyboardMarkup:
        """История кошелька"""
        keyboard = [
            [InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data='back_to_main'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    def bank_menu(balance: float, lang: str = 'ru') -> InlineKeyboardMarkup:
        """Меню банка"""
        keyboard = [
            [InlineKeyboardButton(
                text='💰 Пополнить банк', 
                callback_data='admin_bank_deposit'
            )],
            [InlineKeyboardButton(
                text='🔄 Обновить балансы', 
                callback_data='admin_bank_refresh'
            )],
            [InlineKeyboardButton(
                text='◀️ ' + get_text('back', lang), 
                callback_data='admin_back'
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)