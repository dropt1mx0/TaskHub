# handlers/advertiser.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import time

from database.db import db
from database.queries import TaskQueries, UserQueries, DepositQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from utils.validators import validate_channel_link
from config import config
from services.ton_service import ton_service

router = Router()

class AdvertiserTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_reward = State()
    waiting_for_channel = State()
    waiting_for_confirmation = State()
    waiting_for_delete_reason = State()

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment = State()

@router.callback_query(F.data == "advertiser")
async def show_advertiser_panel(callback: CallbackQuery, lang: str):
    """Показать панель рекламодателя"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            
            if not user:
                await callback.answer("User not found")
                return
            
            # Получаем задания созданные пользователем
            tasks = await TaskQueries.get_tasks_by_creator(session, user_id)
            
            # Статистика
            tasks_count = len(tasks)
            total_completions = sum(t.total_completions for t in tasks)
            total_spent = sum(t.reward * t.total_completions for t in tasks)
            
            text = f"<b>{get_text('advertiser_title', lang)}</b>\n\n"
            text += get_text('advertiser_stats', lang,
                            balance=user.balance,
                            tasks=tasks_count,
                            completions=total_completions)
            text += f"\n{get_text('spent', lang)}: {round(total_spent, 3)} USDT"
            text += f"\n\n{get_text('min_reward', lang)}: {config.MIN_TASK_REWARD} USDT"
            text += f"\n{get_text('min_balance_required', lang, balance=config.MIN_BALANCE_FOR_TASK_CREATION)}"
            
            # Если пользователь админ, показываем специальную метку
            if config.is_admin(user_id):
                text += "\n\n⭐ Вы администратор! Задания создаются бесплатно."
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text('create_task', lang), 
                    callback_data="advertiser_create_task"
                )],
                [InlineKeyboardButton(
                    text=get_text('my_tasks', lang), 
                    callback_data="advertiser_my_tasks"
                )],
                [InlineKeyboardButton(
                    text=get_text('deposit', lang), 
                    callback_data="advertiser_deposit"
                )],
                [InlineKeyboardButton(
                    text=get_text('back', lang), 
                    callback_data="back_to_main"
                )]
            ])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in advertiser panel: {e}")
        await callback.answer("Error loading advertiser panel")

@router.callback_query(F.data == "advertiser_create_task")
async def advertiser_create_task_start(callback: CallbackQuery, state: FSMContext, lang: str):
    """Начать создание задания"""
    user_id = callback.from_user.id
    
    # Проверяем баланс пользователя перед созданием задания
    async with await db.get_session() as session:
        user = await UserQueries.get_user(session, user_id)
        
        # Админы могут создавать задания без проверки баланса
        if not config.is_admin(user_id) and user.balance < config.MIN_BALANCE_FOR_TASK_CREATION:
            error_text = get_text('insufficient_balance_for_task', lang, 
                                 min_balance=config.MIN_BALANCE_FOR_TASK_CREATION,
                                 balance=user.balance)
            await callback.answer(error_text, show_alert=True)
            return
    
    await state.set_state(AdvertiserTaskStates.waiting_for_title)
    
    text = f"{get_text('enter_task_title', lang)}\n\n{get_text('min_reward', lang)}: {config.MIN_TASK_REWARD} USDT"
    if config.is_admin(user_id):
        text += "\n\n⭐ Вы администратор! Задание создается бесплатно."
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboards.back_button('advertiser', lang)
    )

@router.message(AdvertiserTaskStates.waiting_for_title)
async def advertiser_process_task_title(message: Message, state: FSMContext, lang: str):
    """Обработка названия задания"""
    await state.update_data(title=message.text)
    await state.set_state(AdvertiserTaskStates.waiting_for_description)
    
    await message.answer(
        get_text('enter_task_desc', lang),
        reply_markup=InlineKeyboards.back_button('advertiser', lang)
    )

@router.message(AdvertiserTaskStates.waiting_for_description)
async def advertiser_process_task_description(message: Message, state: FSMContext, lang: str):
    """Обработка описания задания"""
    await state.update_data(description=message.text)
    await state.set_state(AdvertiserTaskStates.waiting_for_reward)
    
    await message.answer(
        f"{get_text('enter_task_reward', lang)}\n\n{get_text('min_reward', lang)}: {config.MIN_TASK_REWARD} USDT",
        reply_markup=InlineKeyboards.back_button('advertiser', lang)
    )

# handlers/advertiser.py - обновляем функцию проверки награды

@router.message(AdvertiserTaskStates.waiting_for_reward)
async def advertiser_process_task_reward(message: Message, state: FSMContext, lang: str):
    """Обработка награды за задание"""
    user_id = message.from_user.id
    
    try:
        reward = float(message.text.replace(',', '.'))
        
        # Проверяем минимальную награду (теперь 0.001)
        if reward < config.MIN_TASK_REWARD:
            error_text = get_text('invalid_reward_min', lang, min_reward=config.MIN_TASK_REWARD)
            await message.answer(
                error_text,
                reply_markup=InlineKeyboards.back_button('advertiser', lang)
            )
            return
        
        await state.update_data(reward=reward)
        await state.set_state(AdvertiserTaskStates.waiting_for_channel)
        
        await message.answer(
            get_text('enter_channel', lang),
            reply_markup=InlineKeyboards.back_button('advertiser', lang)
        )
    except ValueError:
        await message.answer(
            get_text('invalid_reward', lang),
            reply_markup=InlineKeyboards.back_button('advertiser', lang)
        )

@router.message(AdvertiserTaskStates.waiting_for_channel)
async def advertiser_process_task_channel(message: Message, state: FSMContext, lang: str):
    """Обработка ссылки на канал"""
    user_id = message.from_user.id
    is_admin = config.is_admin(user_id)
    
    is_valid, username, error = validate_channel_link(message.text)
    
    if not is_valid:
        await message.answer(
            error or get_text('invalid_channel', lang),
            reply_markup=InlineKeyboards.back_button('advertiser', lang)
        )
        return
    
    data = await state.get_data()
    
    # Проверяем баланс пользователя еще раз перед созданием (только для обычных пользователей)
    if not is_admin:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            
            if user.balance < config.MIN_BALANCE_FOR_TASK_CREATION:
                error_text = get_text('insufficient_balance_for_task', lang,
                                     min_balance=config.MIN_BALANCE_FOR_TASK_CREATION,
                                     balance=user.balance)
                await message.answer(
                    error_text,
                    reply_markup=InlineKeyboards.back_button('advertiser', lang)
                )
                await state.clear()
                return
            
            # Проверяем, хватит ли баланса на награду (предупреждение)
            if user.balance < data['reward']:
                warning_text = get_text('task_balance_warning', lang,
                                       balance=user.balance,
                                       reward=data['reward'])
                await message.answer(
                    warning_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="Confirm", callback_data="advertiser_continue_task"),
                            InlineKeyboardButton(text="Cancel", callback_data="advertiser_cancel_task")
                        ]
                    ])
                )
                await state.update_data(channel_username=username, channel_url=f"https://t.me/{username}")
                await state.set_state(AdvertiserTaskStates.waiting_for_confirmation)
                return
    
    # Предпросмотр задания
    text = get_text('task_preview', lang,
                   title=data['title'],
                   reward=data['reward'],
                   channel=f"@{username}")
    
    if is_admin:
        text += "\n\n⭐ Задание создается бесплатно (админ)"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Confirm", callback_data="advertiser_confirm_task"),
            InlineKeyboardButton(text="Cancel", callback_data="advertiser_cancel_task")
        ]
    ])
    
    await state.update_data(channel_username=username, channel_url=f"https://t.me/{username}")
    await state.set_state(AdvertiserTaskStates.waiting_for_confirmation)
    
    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

@router.callback_query(F.data == "advertiser_continue_task")
async def advertiser_continue_task(callback: CallbackQuery, state: FSMContext, lang: str):
    """Продолжить создание задания с предупреждением"""
    data = await state.get_data()
    
    text = get_text('task_preview', lang,
                   title=data['title'],
                   reward=data['reward'],
                   channel=f"@{data['channel_username']}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Confirm", callback_data="advertiser_confirm_task"),
            InlineKeyboardButton(text="Cancel", callback_data="advertiser_cancel_task")
        ]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

@router.callback_query(F.data == "advertiser_confirm_task")
async def advertiser_confirm_task_creation(callback: CallbackQuery, state: FSMContext, lang: str):
    """Подтверждение создания задания"""
    user_id = callback.from_user.id
    data = await state.get_data()
    is_admin = config.is_admin(user_id)
    
    try:
        async with await db.get_session() as session:
            # Создаем задание
            task = await TaskQueries.create_task(
                session,
                title=data['title'],
                description=data['description'],
                reward=data['reward'],
                created_by=user_id,
                channel_url=data.get('channel_url'),
                channel_username=data.get('channel_username'),
                task_type='channel_subscription'
            )
            
            logger.info(f"User {user_id} created task #{task.id}" + (" (admin)" if is_admin else ""))
            
            await callback.message.edit_text(
                get_text('task_created', lang),
                reply_markup=InlineKeyboards.back_button('advertiser', lang),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await callback.message.edit_text(
            "Error creating task",
            reply_markup=InlineKeyboards.back_button('advertiser', lang)
        )
    
    await state.clear()

@router.callback_query(F.data == "advertiser_cancel_task")
async def advertiser_cancel_task_creation(callback: CallbackQuery, state: FSMContext, lang: str):
    """Отмена создания задания"""
    await state.clear()
    await callback.message.edit_text(
        get_text('task_cancelled', lang),
        reply_markup=InlineKeyboards.back_button('advertiser', lang),
        parse_mode='HTML'
    )

@router.callback_query(F.data == "advertiser_my_tasks")
async def advertiser_my_tasks(callback: CallbackQuery, lang: str):
    """Показать задания пользователя"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            tasks = await TaskQueries.get_tasks_by_creator(session, user_id)
            
            if not tasks:
                await callback.message.edit_text(
                    get_text('no_tasks_created', lang),
                    reply_markup=InlineKeyboards.back_button('advertiser', lang)
                )
                return
            
            text = f"<b>{get_text('my_tasks', lang)}</b>\n\n"
            total_cost = 0
            
            for task in tasks[:5]:
                status = "✅ Активно" if task.is_active else "❌ Неактивно"
                cost = task.reward * task.total_completions
                total_cost += cost
                text += f"#{task.id}: {task.title}\n"
                text += f"   Награда: {task.reward} USDT | Статус: {status}\n"
                text += f"   Выполнено: {task.total_completions} | Потрачено: {cost:.3f} USDT\n\n"
            
            text += f"Всего потрачено: {total_cost:.3f} USDT"
            
            # Добавляем кнопки для удаления заданий
            keyboard = []
            for task in tasks[:5]:
                keyboard.append([
                    InlineKeyboardButton(
                        text=f"🗑 Удалить #{task.id}",
                        callback_data=f"advertiser_delete_task_{task.id}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton(
                text=get_text('back', lang),
                callback_data="advertiser"
            )])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error showing tasks: {e}")
        await callback.answer("Error loading tasks")

@router.callback_query(F.data.startswith("advertiser_delete_task_"))
async def advertiser_delete_task_start(callback: CallbackQuery, state: FSMContext, lang: str):
    """Начать удаление задания"""
    task_id = int(callback.data.split('_')[3])
    user_id = callback.from_user.id
    
    async with await db.get_session() as session:
        task = await TaskQueries.get_task_by_id(session, task_id)
        
        if not task:
            await callback.answer("Задание не найдено", show_alert=True)
            return
        
        # Проверяем, что пользователь является создателем
        if task.created_by != user_id:
            await callback.answer(get_text('not_your_task', lang), show_alert=True)
            return
        
        await state.update_data(task_id=task_id, task_title=task.title)
        await state.set_state(AdvertiserTaskStates.waiting_for_delete_reason)
        
        await callback.message.edit_text(
            get_text('enter_delete_reason', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text('back', lang),
                    callback_data="advertiser_my_tasks"
                )]
            ])
        )

@router.message(AdvertiserTaskStates.waiting_for_delete_reason)
async def advertiser_process_delete_reason(message: Message, state: FSMContext, lang: str):
    """Обработка причины удаления и удаление задания"""
    data = await state.get_data()
    task_id = data.get('task_id')
    task_title = data.get('task_title')
    reason = message.text
    user_id = message.from_user.id
    
    try:
        async with await db.get_session() as session:
            # Проверяем еще раз, что пользователь - создатель
            task = await TaskQueries.get_task_by_id(session, task_id)
            
            if not task or task.created_by != user_id:
                await message.answer(
                    get_text('cannot_delete_task', lang),
                    reply_markup=InlineKeyboards.back_button('advertiser', lang)
                )
                await state.clear()
                return
            
            # Удаляем задание
            success = await TaskQueries.delete_task(session, task_id)
            
            if success:
                logger.info(f"User {user_id} deleted their task #{task_id}")
                
                await message.answer(
                    get_text('task_deleted', lang, task_id=task_id),
                    reply_markup=InlineKeyboards.back_button('advertiser', lang)
                )
            else:
                await message.answer(
                    get_text('delete_failed', lang),
                    reply_markup=InlineKeyboards.back_button('advertiser', lang)
                )
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        await message.answer("Error deleting task")
    
    await state.clear()

@router.callback_query(F.data == "advertiser_deposit")
async def advertiser_deposit_start(callback: CallbackQuery, state: FSMContext):
    """Начать пополнение для рекламодателя"""
    user_id = callback.from_user.id
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        await state.update_data(is_bank_deposit=False)
        await state.set_state(DepositStates.waiting_for_amount)
        
        # Получаем кошелек для этого пользователя
        wallet_address = ton_service.get_wallet_for_user(user_id)
        
        text = f"<b>Пополнение баланса</b>\n\n"
        text += f"Введите сумму в TON (минимум {config.MIN_DEPOSIT} TON):\n\n"
        text += f"Кошелек для оплаты:\n<code>{wallet_address}</code>"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text('back', lang), 
                    callback_data="advertiser"
                )]
            ]),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in advertiser_deposit_start: {e}")
        await callback.answer("Ошибка", show_alert=True)

@router.message(DepositStates.waiting_for_amount)
async def advertiser_deposit_amount(message: Message, state: FSMContext):
    """Обработка суммы пополнения"""
    user_id = message.from_user.id
    data = await state.get_data()
    is_bank = data.get('is_bank_deposit', False)
    
    try:
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, user_id)
            lang = user.language if user else 'en'
        
        try:
            amount = float(message.text.replace(',', '.'))
            if amount < config.MIN_DEPOSIT:
                await message.answer(
                    f"Минимальная сумма {config.MIN_DEPOSIT} TON",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=get_text('back', lang), 
                            callback_data="advertiser"
                        )]
                    ])
                )
                return
            
            # Создаем запись о депозите
            async with await db.get_session() as session:
                comment = ton_service.generate_comment(user_id, int(time.time()))
                deposit = await DepositQueries.create_deposit(
                    session, user_id, amount, 'ton', comment
                )
                
                # Получаем кошелек для этого пользователя
                wallet_address = ton_service.get_wallet_for_user(user_id)
                
                # Генерируем ссылку для оплаты
                payment_link = await ton_service.generate_payment_link(amount, comment, wallet_address)
                qr_url = await ton_service.generate_qr_code(amount, comment, wallet_address)
                
                await state.update_data(
                    deposit_id=deposit.id,
                    amount=amount,
                    comment=comment,
                    payment_link=payment_link,
                    qr_url=qr_url,
                    wallet_address=wallet_address
                )
                
                text = f"<b>Депозит #{deposit.id}</b>\n\n"
                text += f"Сумма: {amount} TON\n"
                text += f"Статус: Ожидание\n\n"
                text += f"<b>❗️❗️❗️ ВАЖНО ❗️❗️❗️</b>\n\n"
                text += f"<b>Обязательно укажите этот комментарий при переводе:</b>\n"
                text += f"<code>❗️ {comment} ❗️</code>\n\n"
                text += f"<b>Без этого комментария деньги не зачислятся автоматически!</b>\n\n"
                text += f"<b>Детали платежа:</b>\n"
                text += f"Кошелек: <code>{wallet_address}</code>\n"
                text += f"Комментарий: <code>{comment}</code>\n\n"
                text += f"<a href='{payment_link}'>Нажмите для оплаты в TON кошельке</a>\n\n"
                text += f"<a href='{qr_url}'>Посмотреть QR-код</a>\n\n"
                text += f"После оплаты нажмите 'Я оплатил' для проверки."
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Я оплатил", callback_data="advertiser_deposit_check")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="advertiser_deposit_cancel")]
                ])
                
                await message.answer(
                    text,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                
                await state.set_state(DepositStates.waiting_for_payment)
                
        except ValueError:
            await message.answer(
                "Неверная сумма. Введите число.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=get_text('back', lang), 
                        callback_data="advertiser"
                    )]
                ])
            )
    except Exception as e:
        logger.error(f"Error in deposit_amount: {e}")
        await message.answer("Ошибка обработки депозита")

@router.callback_query(F.data == "advertiser_deposit_check")
async def advertiser_deposit_check(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    deposit_id = data.get('deposit_id')
    expected_amount = data.get('amount')
    comment = data.get('comment')
    wallet_address = data.get('wallet_address')
    
    if not all([deposit_id, expected_amount, comment]):
        await callback.answer("Нет активного депозита", show_alert=True)
        return
    
    try:
        await callback.message.edit_text("Проверка статуса платежа...")
        
        # Проверяем транзакцию на всех кошельках
        success, received_amount, tx_hash = await ton_service.check_transaction(comment, expected_amount)
        
        if success:
            async with await db.get_session() as session:
                user = await UserQueries.get_user(session, user_id)
                lang = user.language if user else 'en'
                
                # Обновляем статус депозита
                await DepositQueries.update_deposit_status(session, deposit_id, 'completed', tx_hash)
                
                # Пополняем баланс пользователя
                await UserQueries.update_balance(session, user_id, expected_amount, hold=False)
                user = await UserQueries.get_user(session, user_id)
                
                text = f"<b>Депозит завершен!</b>\n\n"
                text += f"Сумма: {expected_amount} TON зачислена на ваш баланс\n"
                text += f"Новый баланс: {user.balance} USDT\n"
                text += f"Tx: <code>{tx_hash}</code>"
                
                await callback.message.edit_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text=get_text('back', lang), 
                            callback_data="advertiser"
                        )]
                    ]),
                    parse_mode='HTML'
                )
                
                logger.info(f"Deposit {deposit_id} completed for user {user_id}")
                await state.clear()
        else:
            async with await db.get_session() as session:
                user = await UserQueries.get_user(session, user_id)
                lang = user.language if user else 'en'
            
            await callback.message.edit_text(
                f"<b>Депозит #{deposit_id}</b>\n\n"
                f"Сумма: {expected_amount} TON\n"
                f"Статус: Ожидание\n\n"
                f"<b>❗️❗️❗️ ВАЖНО ❗️❗️❗️</b>\n\n"
                f"<b>Проверьте что вы указали правильный комментарий:</b>\n"
                f"<code>❗️ {comment} ❗️</code>\n\n"
                f"<b>Без этого комментария платеж не будет обнаружен!</b>\n\n"
                f"<b>Детали платежа:</b>\n"
                f"Кошелек: <code>{wallet_address}</code>\n"
                f"Комментарий: <code>{comment}</code>\n\n"
                f"Платеж еще не обнаружен. Убедитесь что вы:\n"
                f"1. Отправили точную сумму ({expected_amount} TON)\n"
                f"2. Указали правильный комментарий\n"
                f"3. Транзакция подтверждена в блокчейне\n\n"
                f"Нажмите 'Я оплатил' снова после отправки.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Я оплатил", callback_data="advertiser_deposit_check")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="advertiser_deposit_cancel")]
                ]),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in deposit_check: {e}")
        await callback.answer("Ошибка проверки платежа", show_alert=True)

@router.callback_query(F.data == "advertiser_deposit_cancel")
async def advertiser_deposit_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена депозита"""
    data = await state.get_data()
    deposit_id = data.get('deposit_id')
    
    try:
        if deposit_id:
            async with await db.get_session() as session:
                await DepositQueries.update_deposit_status(session, deposit_id, 'failed')
        
        await state.clear()
        
        async with await db.get_session() as session:
            user = await UserQueries.get_user(session, callback.from_user.id)
            lang = user.language if user else 'en'
            await show_advertiser_panel(callback, lang)
    except Exception as e:
        logger.error(f"Error in deposit_cancel: {e}")
        await callback.answer("Ошибка", show_alert=True)