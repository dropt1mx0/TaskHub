# utils/translations.py
from config import config

TRANSLATIONS = {
    'ru': {
        'welcome': 'Добро пожаловать в <b>{bot_name}</b>!\n\nЗарабатывай USDT за выполнение простых заданий.\nПриглашай друзей и получай бонусы.\nКрути колесо фортуны каждые 12 часов.\n\n🍀 Удачи в заработке!',
        'balance': 'Баланс: <b>{balance} USDT</b>',
        'main_menu': 'Главное меню',
        'tasks': 'Задания',
        'withdraw': 'Вывод',
        'profile': 'Профиль',
        'wheel': 'Колесо',
        'referrals': 'Рефералы',
        'leaders': 'Лидеры',
        'advertiser': 'Рекламодатель',
        'instructions': 'Инструкция',
        
        # Instructions
        'inst_earn': 'Как зарабатывать',
        'inst_earn_text': '📋 <b>Как зарабатывать USDT</b>\n\n'
                           '1. Нажмите кнопку "Задания"\n'
                           '2. Выберите задание из списка\n'
                           '3. Подпишитесь на канал или перейдите по ссылке\n'
                           '4. Нажмите "Выполнить задание"\n'
                           '5. Награда поступит на ваш баланс\n\n'
                           '💰 Минимальная награда: 0.001 USDT',
        
        'inst_withdraw': 'Как выводить',
        'inst_withdraw_text': '💳 <b>Как выводить средства</b>\n\n'
                              '1. Перейдите в раздел "Вывод"\n'
                              '2. Выберите способ вывода (TON или USDT)\n'
                              '3. Введите сумму (минимум 1.0 USDT)\n'
                              '4. Введите адрес вашего кошелька\n'
                              '5. Дождитесь подтверждения администратором\n\n'
                              '⏳ Выводы обрабатываются в течение 24 часов',
        
        'inst_referrals': 'Рефералы',
        'inst_referrals_text': '👥 <b>Реферальная программа</b>\n\n'
                              '• Приглашайте друзей по своей ссылке\n'
                              '• Получайте 0.005 USDT за обычного пользователя\n'
                              '• Получайте 0.05 USDT за Premium пользователя\n'
                              '• Зарабатывайте 90% от дохода рефералов после 20 заданий\n\n'
                              '🔗 Ваша ссылка в разделе "Рефералы"',
        
        'inst_wheel': 'Колесо фортуны',
        'inst_wheel_text': '🎰 <b>Колесо фортуны</b>\n\n'
                          '• Бесплатное вращение каждые 12 часов\n'
                          '• Платное вращение: 0.25 USDT\n'
                          '• Призы от 0.001 до 0.1 USDT\n\n'
                          '🎲 Крутите и выигрывайте!',
        
        'inst_advertiser': 'Рекламодателям',
        'inst_advertiser_text': '📢 <b>Для рекламодателей</b>\n\n'
                               '• Создавайте задания для пользователей\n'
                               '• Минимальная награда: 0.001 USDT\n'
                               '• Нужно минимум 0.5 USDT на балансе\n'
                               '• Средства списываются только при выполнении\n\n'
                               '📊 Отслеживайте задания в разделе "Мои задания"',
        
        # Tasks
        'tasks_title': 'Доступные задания:',
        'no_tasks': 'На данный момент доступных заданий нет.\nВозвращайся позже!',
        'task_completed': 'Задание выполнено!\nНачислено: <b>+{reward} USDT</b>',
        'task_already_done': 'Вы уже выполнили это задание',
        'complete_task': 'Выполнить задание',
        'subscribe_required': 'Для выполнения задания необходимо подписаться на канал',
        'check_subscription': 'Проверить подписку',
        
        # Profile
        'profile_title': 'Профиль',
        'profile_stats': 'Баланс: {balance} USDT\nВсего заработано: {total_earned} USDT\nЗаданий выполнено: {tasks_completed}\nСерия входов: {streak} дн.\nРефералов: {referrals}',
        'back': 'Назад',
        
        # Withdraw
        'withdraw_title': 'Выберите способ вывода:',
        'usdt': 'USDT (TON)',
        'ton': 'TON',
        'enter_amount': 'Введите сумму для вывода (мин. {min} {currency}):',
        'enter_wallet': 'Введите адрес вашего кошелька:',
        'enter_wallet_ton': 'Введите ваш TON кошелек (начинается с EQ или UQ):',
        'enter_wallet_usdt': 'Введите ваш USDT адрес (сеть TON):',
        'withdrawal_created': 'Заявка на вывод создана!\n\nСумма: {amount} {currency}\nАдрес: {wallet}',
        'insufficient_balance': 'Недостаточно средств. Доступно: {balance} USDT',
        'invalid_amount': 'Неверная сумма. Минимум {min} {currency}',
        'invalid_ton_address': 'Неверный TON адрес. Адрес должен начинаться с EQ или UQ',
        'invalid_usdt_address': 'Неверный USDT адрес',
        'withdrawal_pending': 'Ваша заявка ожидает обработки администратором.',
        'withdrawal_history': 'История выводов',
        'no_withdrawals': 'У вас пока нет выводов',
        'network_fee': 'Комиссия сети: ~{fee} TON будет вычтена',
        
        # Advertiser panel
        'advertiser_title': 'Панель рекламодателя',
        'advertiser_stats': 'Баланс: {balance} USDT\nЗаданий: {tasks}\nВыполнений: {completions}',
        'spent': 'Потрачено',
        'min_reward': 'Мин. награда',
        'min_balance_required': 'Мин. баланс: {balance} USDT',
        'create_task': 'Создать задание',
        'my_tasks': 'Мои задания',
        'deposit': 'Пополнить',
        'insufficient_balance_for_task': 'Вам нужно минимум {min_balance} USDT для создания заданий. Текущий баланс: {balance} USDT',
        'invalid_reward_min': 'Награда должна быть не менее {min_reward} USDT',
        'task_balance_warning': 'Предупреждение: Ваш баланс ({balance} USDT) меньше награды ({reward} USDT). Убедитесь, что у вас достаточно средств при выполнении заданий.',
        'no_tasks_created': 'Вы еще не создали ни одного задания',
        'not_your_task': 'Вы можете удалять только свои задания',
        'enter_delete_reason': 'Введите причину удаления задания:',
        'cannot_delete_task': 'Невозможно удалить это задание. Возможно, оно уже удалено или у вас нет прав.',
        'task_deleted': 'Задание #{task_id} успешно удалено.',
        'delete_failed': 'Не удалось удалить задание.',
        
        # Task creation
        'enter_task_title': 'Введите название задания:',
        'enter_task_desc': 'Введите описание задания:',
        'enter_task_reward': 'Введите награду за задание (в USDT):',
        'enter_channel': 'Отправьте ссылку на канал или @username:',
        'task_preview': 'Предпросмотр задания:\n\nНазвание: {title}\nНаграда: {reward} USDT\nКанал: {channel}\n\nПодтвердить создание?',
        'task_created': 'Задание успешно создано!',
        'task_cancelled': 'Создание задания отменено',
        'invalid_reward': 'Неверная награда. Минимум: 0.001 USDT',
        'invalid_channel': 'Неверная ссылка на канал',
        
        # Wheel
        'wheel_title': 'Колесо фортуны',
        'free_spin_available': 'Доступно бесплатное вращение!',
        'next_free_in': 'Следующее бесплатное через: {hours}ч {minutes}м',
        'spin_result': 'Вы выиграли <b>{reward} USDT</b>!',
        'spin_paid': 'Крутить за 0.250 USDT',
        'insufficient_funds': 'Недостаточно средств',
        
        # Referrals
        'referral_title': 'Реферальная программа',
        'your_link': 'Ваша ссылка:\n<code>{link}</code>',
        'referral_stats': 'Рефералов: {count}\nЗаработано: {total} USDT',
        'referral_bonuses': '\n\nБонусы:\n• За обычного пользователя: 0.005 USDT\n• За Premium пользователя: 0.05 USDT\n• 90% от заработка реферала после 20 заданий',
        
        # Leaders
        'leaders_title': 'Таблица лидеров',
        'leaders_empty': 'Пока нет участников в таблице лидеров',
        'leaders_prizes': '1 место: 0.500 USDT\n2 место: 0.300 USDT\n3 место: 0.150 USDT',
        'leader_row': '{place}. {name} — {amount} USDT',
        
        # Admin panel
        'admin_panel': 'Админ-панель',
        'admin_stats': 'Статистика',
        'admin_broadcast': 'Рассылка',
        'admin_withdrawals': 'Выплаты',
        'admin_tasks': 'Управление заданиями',
        'pending_withdrawals': 'Ожидающие выплаты:',
        'no_pending': 'Нет ожидающих выплат',
        'approve': 'Подтвердить',
        'reject': 'Отклонить',
        'bank_balance': 'Баланс банка: {balance} USDT',
        'wallets_balance': 'Баланс кошельков: {balance} TON',
        'refresh_balances': 'Обновить балансы',
        'total_users': 'Всего пользователей',
        'new_users_24h': 'Новых (24ч)',
        'premium_users': 'Premium',
        'tasks_completed': 'Выполнено заданий',
        'total_withdrawn': 'Всего выведено',
        'created_by': 'Создано',
        'enter_broadcast': 'Введите текст для рассылки:',
        'broadcast_preview': 'Предпросмотр рассылки:\n\n{text}\n\nБудет отправлено {count} пользователям.',
        'broadcast_sent': 'Рассылка завершена!\n\nОтправлено: {success}\nОшибок: {failed}',
        'broadcast_cancelled': 'Рассылка отменена',
        'loading': 'Загрузка...',
        
        # Deposit
        'important_comment': '❗️❗️❗️ ВАЖНО ❗️❗️❗️',
        'must_include_comment': 'Обязательно укажите этот комментарий при переводе:',
        'without_comment': 'Без этого комментария деньги не зачислятся автоматически!',
        'check_comment': 'Проверьте что вы указали правильный комментарий:',
        'payment_details': 'Детали платежа',
        'click_to_pay': 'Нажмите для оплаты в TON кошельке',
        'view_qr': 'Посмотреть QR-код',
        'after_payment': 'После оплаты нажмите "Я оплатил" для проверки.',
        'i_paid': 'Я оплатил',
        'cancel': 'Отмена',
        'min_amount': 'Минимальная сумма',
        'amount': 'Сумма',
        'status': 'Статус',
        'pending': 'Ожидание',
        'comment': 'Комментарий',
        'wallet_address': 'Кошелек',
        'payment_not_detected': 'Платеж еще не обнаружен. Убедитесь что вы отправили точную сумму ({amount} TON) с правильным комментарием.',
        'click_after_sending': 'Нажмите "Я оплатил" снова после отправки.',
        'deposit_completed': 'Депозит завершен!',
        'new_balance': 'Новый баланс',
        
        # Captcha
        'captcha_title': 'Требуется проверка',
        'captcha_description': 'Решите простой пример для доступа к заданиям:',
        'captcha_instruction': 'Нажмите правильную цифру на клавиатуре ниже.',
        'captcha_current_input': 'Текущий ввод',
        'captcha_ok': 'Готово',
        'captcha_clear': 'Очистить',
        'captcha_enter_number': 'Введите ответ с помощью цифр ниже.',
        'captcha_wrong': 'Неверный ответ. Попыток: {attempts}/3',
        'captcha_too_many': 'Слишком много неудачных попыток. Возврат в главное меню.',
        'captcha_session_expired': 'Сессия истекла. Попробуйте снова.',
        'captcha_reset': 'Сбросить',
        'captcha_cancel': 'Отмена',
        
        # Anti-cheat
        'anti_abuse': 'Обнаружена подозрительная активность',
        'try_later': 'Попробуйте позже',
    }
}

def get_text(key: str, lang: str = 'ru', **kwargs) -> str:
    """Получить текст на русском языке"""
    text = TRANSLATIONS['ru'].get(key, key)
    if '{bot_name}' in text and 'bot_name' not in kwargs:
        kwargs['bot_name'] = config.BOT_NAME
    return text.format(**kwargs) if kwargs else text