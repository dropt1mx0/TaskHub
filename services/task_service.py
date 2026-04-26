# services/task_service.py
from typing import Optional, List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
import re

from database.models import Task, CompletedTask, User
from database.queries import TaskQueries, UserQueries, ReferralQueries
from utils.helpers import format_number
from config import config

class TaskService:
    """Сервис для работы с заданиями"""
    
    @staticmethod
    async def get_available_tasks(
        session: AsyncSession, 
        user_id: int
    ) -> List[Dict]:
        """Получить доступные задания с форматированием"""
        tasks = await TaskQueries.get_available_tasks(session, user_id)
        
        result = []
        for task in tasks:
            result.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'reward': format_number(task.reward),
                'type': task.task_type,
                'channel_url': task.channel_url
            })
        
        return result
    
    @staticmethod
    async def check_subscription(
        bot,
        user_id: int,
        channel_username: str
    ) -> bool:
        """Проверить подписку на канал"""
        try:
            # Пытаемся получить статус участника
            chat_member = await bot.get_chat_member(
                chat_id=f"@{channel_username}",
                user_id=user_id
            )
            
            # Проверяем статусы
            valid_statuses = ['member', 'administrator', 'creator']
            return chat_member.status in valid_statuses
        except Exception as e:
            # Если канал не найден или бот не админ
            return False
    
    @staticmethod
    async def verify_and_complete(
        session: AsyncSession,
        bot,
        user_id: int,
        task_id: int
    ) -> Tuple[bool, str, Optional[float]]:
        """Проверить и выполнить задание"""
        
        # Получаем задание
        task = await TaskQueries.get_task_by_id(session, task_id)
        if not task:
            return False, "Задание не найдено", None
        
        # Проверяем, не выполнял ли уже
        completed_tasks = await TaskQueries.get_completed_tasks(session, user_id)
        completed_ids = [t.task_id for t in completed_tasks]
        if task.id in completed_ids:
            return False, "Задание уже выполнено", None
        
        # Проверка в зависимости от типа задания
        if task.task_type == 'channel_subscription' and task.channel_username:
            is_subscribed = await TaskService.check_subscription(
                bot, user_id, task.channel_username
            )
            
            if not is_subscribed:
                return False, "Необходимо подписаться на канал", None
        
        # Выполняем задание
        reward = await TaskQueries.complete_task(session, user_id, task_id)
        
        if reward:
            # Обновляем баланс (на удержание)
            await UserQueries.update_balance(
                session, user_id, reward, hold=True, task_completed=True
            )
            
            # Обрабатываем реферальные бонусы
            await ReferralQueries.update_referral_progress(session, user_id, reward)
            
            return True, "Задание выполнено!", reward
        
        return False, "Ошибка выполнения", None
    
    @staticmethod
    async def get_completed_tasks_stats(
        session: AsyncSession,
        user_id: int
    ) -> Dict:
        """Получить статистику выполненных заданий"""
        completed = await TaskQueries.get_completed_tasks(session, user_id)
        
        total_reward = sum(c.reward_earned for c in completed)
        
        return {
            'count': len(completed),
            'total_reward': format_number(total_reward),
            'last_tasks': [
                {
                    'title': c.task.title,
                    'reward': format_number(c.reward_earned),
                    'date': c.completed_at.strftime('%d.%m.%Y')
                }
                for c in completed[:5]
            ]
        }
    
    @staticmethod
    async def get_task_by_id(
        session: AsyncSession,
        task_id: int
    ) -> Optional[Dict]:
        """Получить задание по ID с форматированием"""
        task = await TaskQueries.get_task_by_id(session, task_id)
        
        if not task:
            return None
        
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'reward': format_number(task.reward),
            'type': task.task_type,
            'channel_username': task.channel_username,
            'channel_url': task.channel_url,
            'is_active': task.is_active,
            'total_completions': task.total_completions,
            'created_by': task.created_by
        }
    
    @staticmethod
    async def get_creator_tasks_stats(
        session: AsyncSession,
        creator_id: int
    ) -> Dict:
        """Получить статистику по заданиям создателя"""
        tasks = await TaskQueries.get_tasks_by_creator(session, creator_id)
        
        total_completions = sum(t.total_completions for t in tasks)
        total_spent = sum(t.reward * t.total_completions for t in tasks)
        active_tasks = sum(1 for t in tasks if t.is_active)
        
        return {
            'total_tasks': len(tasks),
            'active_tasks': active_tasks,
            'total_completions': total_completions,
            'total_spent': format_number(total_spent),
            'tasks': [
                {
                    'id': t.id,
                    'title': t.title,
                    'reward': format_number(t.reward),
                    'is_active': t.is_active,
                    'completions': t.total_completions
                }
                for t in tasks[:10]
            ]
        }