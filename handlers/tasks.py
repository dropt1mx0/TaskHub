# handlers/tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger
import asyncio

from database.db import db
from database.queries import TaskQueries, UserQueries, ReferralQueries, CaptchaQueries, SubscriptionQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from services.captcha_service import captcha_service
from services.subscription_service import subscription_service
from config import config

router = Router()

# Хранилище временных данных для капчи
captcha_data = {}

@router.callback_query(F.data == "tasks")
async def show_tasks(callback: CallbackQuery, lang: str):
    """Показать список доступных заданий"""
    user_id = callback.from_user.id
    
    async with await db.get_session() as session:
        # Увеличиваем счетчик посещений
        await CaptchaQueries.increment_task_visits(session, user_id)
        
        # Проверяем, нужна ли капча
        needs_captcha = await CaptchaQueries.check_captcha_needed(session, user_id)
        
        if needs_captcha:
            await show_captcha(callback, lang)
            return
        
        tasks = await TaskQueries.get_available_tasks(session, user_id)
        
        if not tasks:
            await callback.message.edit_text(
                get_text('no_tasks', lang),
                reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                parse_mode='HTML'
            )
            return
        
        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task.id,
                'title': task.title,
                'reward': task.reward
            })
        
        await callback.message.edit_text(
            get_text('tasks_title', lang),
            reply_markup=InlineKeyboards.tasks_list(tasks_list, lang),
            parse_mode='HTML'
        )

@router.callback_query(F.data.startswith("task_"))
async def show_task_detail(callback: CallbackQuery, lang: str):
    """Показать детали задания"""
    try:
        task_id = int(callback.data.split('_')[1])
        
        async with await db.get_session() as session:
            task = await TaskQueries.get_task_by_id(session, task_id)
            
            if not task:
                await callback.answer("Задание не найдено", show_alert=True)
                return
            
            text = f"<b>{task.title}</b>\n\n"
            if task.description:
                text += f"{task.description}\n\n"
            text += f"💰 Награда: <b>{task.reward} USDT</b>\n"
            
            if task.channel_username:
                text += f"📢 Канал: @{task.channel_username}\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboards.task_detail(task_id, lang),
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error in show_task_detail: {e}")
        await callback.answer("Ошибка загрузки задания", show_alert=True)

@router.callback_query(F.data.startswith("complete_"))
async def complete_task(callback: CallbackQuery, lang: str):
    """Выполнить задание"""
    user_id = callback.from_user.id
    task_id = int(callback.data.split('_')[1])
    
    async with await db.get_session() as session:
        task = await TaskQueries.get_task_by_id(session, task_id)
        
        if not task:
            await callback.answer("Задание не найдено", show_alert=True)
            return
        
        # Проверяем, не выполнял ли пользователь это задание
        completed_tasks = await TaskQueries.get_completed_tasks(session, user_id)
        completed_task_ids = [ct.task_id for ct in completed_tasks]
        
        if task_id in completed_task_ids:
            await callback.answer(
                get_text('task_already_done', lang),
                show_alert=True
            )
            return
        
        # Проверяем баланс создателя задания
        creator = await UserQueries.get_user(session, task.created_by)
        if creator.balance < task.reward:
            await callback.answer(
                "❌ У создателя задания недостаточно средств. Задание временно недоступно.",
                show_alert=True
            )
            return
        
        # Проверяем подписку на канал
        if task.channel_username:
            try:
                bot_member = await callback.bot.get_chat_member(
                    chat_id=f"@{task.channel_username}",
                    user_id=callback.bot.id
                )
                if bot_member.status not in ['administrator', 'creator']:
                    await callback.answer(
                        "❌ Бот не является администратором канала. Задание временно недоступно.",
                        show_alert=True
                    )
                    return
                
                chat_member = await callback.bot.get_chat_member(
                    chat_id=f"@{task.channel_username}",
                    user_id=user_id
                )
                
                if chat_member.status not in ['member', 'administrator', 'creator']:
                    await callback.answer(
                        get_text('subscribe_required', lang),
                        show_alert=True
                    )
                    return
                    
            except Exception as e:
                logger.error(f"Error checking subscription: {e}")
                await callback.answer(
                    "❌ Ошибка при проверке подписки. Канал недоступен.",
                    show_alert=True
                )
                return
        
        # Проверяем возраст аккаунта
        days_enough, days_in_bot = await subscription_service.check_user_age(user_id)
        
        if not days_enough:
            warning_text = (
                f"⚠️ <b>Важно!</b>\n\n"
                f"Вы находитесь в боте всего {days_in_bot} дней.\n"
                f"Для получения награды нужно оставаться подписанным на канал минимум 5 дней.\n\n"
                f"Если вы отпишетесь раньше:\n"
                f"• Награда {task.reward} USDT будет списана обратно\n"
                f"• Штрафные очки (макс. 3)\n"
                f"• При 3 очках - блокировка аккаунта\n\n"
                f"Продолжить?"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Да, я согласен",
                        callback_data=f"accept_terms_{task_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Нет, отмена",
                        callback_data="tasks"
                    )
                ]
            ])
            
            await callback.message.edit_text(
                warning_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            return
        
        # Если аккаунт старый, начисляем награду сразу
        await process_task_completion(callback, user_id, task_id, task, lang)

@router.callback_query(F.data.startswith("accept_terms_"))
async def accept_terms(callback: CallbackQuery, lang: str):
    """Принять условия и выполнить задание"""
    user_id = callback.from_user.id
    task_id = int(callback.data.split('_')[2])
    
    async with await db.get_session() as session:
        task = await TaskQueries.get_task_by_id(session, task_id)
        
        if not task:
            await callback.answer("Задание не найдено", show_alert=True)
            return
        
        await process_task_completion(callback, user_id, task_id, task, lang, track_subscription=True)

async def process_task_completion(callback: CallbackQuery, user_id: int, task_id: int, task, lang: str, track_subscription: bool = False):
    """Общая функция для выполнения задания"""
    
    async with await db.get_session() as session:
        reward = await TaskQueries.complete_task(session, user_id, task_id)
        
        if reward:
            # Списываем средства у создателя задания
            await UserQueries.update_balance(
                session, task.created_by, -reward, hold=False
            )
            
            # Начисляем исполнителю СРАЗУ на баланс
            await UserQueries.update_balance(
                session, user_id, reward, hold=False, task_completed=True
            )
            
            # Обрабатываем реферальные бонусы
            await ReferralQueries.update_referral_progress(session, user_id, reward)
            
            if track_subscription and task.channel_username:
                await subscription_service.start_subscription_tracking(
                    user_id, task_id, task.channel_username
                )
                
                await callback.message.edit_text(
                    f"✅ Задание выполнено!\n\n"
                    f"💰 Начислено: <b>+{reward} USDT</b>\n\n"
                    f"⚠️ <b>Важно!</b> Если вы отпишетесь от канала в течение 5 дней, "
                    f"награда будет списана обратно.",
                    reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                    parse_mode='HTML'
                )
            else:
                await callback.message.edit_text(
                    get_text('task_completed', lang, reward=reward),
                    reply_markup=InlineKeyboards.back_button('back_to_main', lang),
                    parse_mode='HTML'
                )
            
            logger.info(f"User {user_id} completed task {task_id}, earned {reward} USDT" + 
                       (" (tracked)" if track_subscription else ""))
        else:
            await callback.answer(
                get_text('task_already_done', lang),
                show_alert=True
            )

# Капча функции
async def show_captcha(callback: CallbackQuery, lang: str):
    """Показать капчу пользователю"""
    user_id = callback.from_user.id
    
    captcha_service.reset_attempts(user_id)
    captcha_service.reset_input(user_id)
    
    question, answer_hash, keyboard, correct_answer = captcha_service.generate_captcha()
    
    captcha_data[user_id] = {
        'answer_hash': answer_hash,
        'correct_answer': correct_answer,
        'message_id': callback.message.message_id,
        'attempts': 0,
        'last_text': None
    }
    
    text = f"🔒 <b>{get_text('captcha_title', lang)}</b>\n\n"
    text += f"{get_text('captcha_description', lang)}\n\n"
    text += f"<b>{question}</b>\n\n"
    text += f"{get_text('captcha_instruction', lang)}\n\n"
    text += f"{get_text('captcha_current_input', lang)}: <b>{captcha_service.get_input(user_id)}</b>"
    
    captcha_data[user_id]['last_text'] = text
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("captcha_num_"))
async def process_captcha_number(callback: CallbackQuery, lang: str):
    """Обработка нажатия на цифру в капче"""
    user_id = callback.from_user.id
    
    parts = callback.data.split('_')
    if len(parts) < 4:
        await callback.answer("Неверные данные капчи", show_alert=True)
        return
    
    selected_num = parts[2]
    answer_hash = parts[3]
    
    if user_id not in captcha_data:
        await callback.answer(get_text('captcha_session_expired', lang), show_alert=True)
        await show_tasks(callback, lang)
        return
    
    current_input = captcha_service.add_digit(user_id, selected_num)
    correct_answer = captcha_data[user_id]['correct_answer']
    
    if correct_answer < 10 and len(current_input) == 1:
        await check_captcha_answer(callback, user_id, current_input, answer_hash, lang)
    else:
        new_text = f"🔒 <b>{get_text('captcha_title', lang)}</b>\n\n"
        new_text += f"{get_text('captcha_instruction', lang)}\n\n"
        new_text += f"{get_text('captcha_current_input', lang)}: <b>{current_input}</b>\n\n"
        new_text += f"Нажмите Готово когда закончите или продолжайте вводить цифры."
        
        last_text = captcha_data[user_id].get('last_text')
        
        if new_text != last_text:
            captcha_data[user_id]['last_text'] = new_text
            await callback.message.edit_text(
                new_text,
                reply_markup=callback.message.reply_markup,
                parse_mode='HTML'
            )
        
        await callback.answer()

async def check_captcha_answer(callback: CallbackQuery, user_id: int, answer: str, answer_hash: str, lang: str):
    """Проверка ответа капчи"""
    if captcha_service.verify_answer(answer, answer_hash):
        async with await db.get_session() as session:
            await CaptchaQueries.mark_captcha_passed(session, user_id)
        
        if user_id in captcha_data:
            del captcha_data[user_id]
        captcha_service.reset_input(user_id)
        
        await show_tasks(callback, lang)
    else:
        attempts = captcha_service.increment_attempts(user_id)
        
        if attempts >= 3:
            await callback.answer(get_text('captcha_too_many', lang), show_alert=True)
            if user_id in captcha_data:
                del captcha_data[user_id]
            captcha_service.reset_input(user_id)
            from handlers.start import back_to_main
            await back_to_main(callback)
        else:
            captcha_service.reset_input(user_id)
            await callback.answer(
                get_text('captcha_wrong', lang, attempts=attempts), 
                show_alert=True
            )
            await show_captcha(callback, lang)

@router.callback_query(F.data.startswith("captcha_submit_"))
async def process_captcha_submit(callback: CallbackQuery, lang: str):
    """Подтверждение ввода для двузначных чисел"""
    user_id = callback.from_user.id
    
    parts = callback.data.split('_')
    if len(parts) < 3:
        await callback.answer("Неверные данные капчи", show_alert=True)
        return
    
    answer_hash = parts[2]
    
    if user_id not in captcha_data:
        await callback.answer(get_text('captcha_session_expired', lang), show_alert=True)
        await show_tasks(callback, lang)
        return
    
    current_input = captcha_service.get_input(user_id)
    
    if not current_input:
        await callback.answer("Введите число!", show_alert=True)
        return
    
    await check_captcha_answer(callback, user_id, current_input, answer_hash, lang)

@router.callback_query(F.data.startswith("captcha_clear_"))
async def process_captcha_clear(callback: CallbackQuery, lang: str):
    """Очистка текущего ввода"""
    user_id = callback.from_user.id
    
    captcha_service.clear_input(user_id)
    
    if user_id in captcha_data:
        new_text = f"🔒 <b>{get_text('captcha_title', lang)}</b>\n\n"
        new_text += f"{get_text('captcha_instruction', lang)}\n\n"
        new_text += f"{get_text('captcha_current_input', lang)}: <b></b>\n\n"
        new_text += f"Введите ответ с помощью цифр ниже."
        
        last_text = captcha_data[user_id].get('last_text')
        
        if new_text != last_text:
            captcha_data[user_id]['last_text'] = new_text
            await callback.message.edit_text(
                new_text,
                reply_markup=callback.message.reply_markup,
                parse_mode='HTML'
            )
    
    await callback.answer()

@router.callback_query(F.data.startswith("captcha_reset_"))
async def process_captcha_reset(callback: CallbackQuery, lang: str):
    """Сброс капчи - генерация новой"""
    user_id = callback.from_user.id
    
    if user_id not in captcha_data:
        await callback.answer(get_text('captcha_session_expired', lang), show_alert=True)
        await show_tasks(callback, lang)
        return
    
    await show_captcha(callback, lang)

@router.callback_query(F.data == "captcha_cancel")
async def process_captcha_cancel(callback: CallbackQuery, lang: str):
    """Отмена капчи - возврат в главное меню"""
    user_id = callback.from_user.id
    
    if user_id in captcha_data:
        del captcha_data[user_id]
    captcha_service.reset_input(user_id)
    
    from handlers.start import back_to_main
    await back_to_main(callback)