# handlers/language.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from loguru import logger

from database.db import db
from database.queries import UserQueries
from keyboards.inline import InlineKeyboards
from utils.translations import get_text
from config import config

router = Router()

@router.message(Command("language"))
async def cmd_language(message: Message):
    """Команда /language - теперь только русский"""
    await message.answer("🌐 Язык бота: Русский")