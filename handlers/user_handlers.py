#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд пользователя для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    ADMIN_IDS, CLIENTS_DIR, BOT_VERSION, COPYRIGHT, 
    SUPPORT_CONTACT, WEBSITE_URL, TEMPLATES_DIR
)
from keyboards.user_kb import (
    start_kb, help_kb, profile_kb, feedback_kb,
    setup_kb, faq_kb, back_to_main_kb
)
from database.models import ClientModel, FeedbackModel
from utils.qr_generator import generate_qr_from_config
from utils.speed_test import run_speed_test

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляры моделей
client_model = ClientModel()
feedback_model = FeedbackModel()

# Определение состояний для FSM
class UserStates(StatesGroup):
    feedback = State()
    view_profile = State()

# Функция для чтения содержимого текстовых шаблонов
def read_template(filename):
    """Читает текст из шаблона"""
    try:
        file_path = os.path.join(TEMPLATES_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Ошибка при чтении шаблона {filename}: {e}")
        return f"Шаблон {filename} не найден"

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Проверяем, есть ли у пользователя уже профиль
    client = await client_model.get_client_by_user_id(user_id)
    
    # Получаем текст приветствия из шаблона
    welcome_text = read_template("welcome.txt")
    
    # Заменяем плейсхолдеры в тексте
    welcome_text = welcome_text.replace("{first_name}", first_name)
    welcome_text = welcome_text.replace("{bot_version}", BOT_VERSION)
    welcome_text = welcome_text.replace("{copyright}", COPYRIGHT)
    
    # Определяем клавиатуру в зависимости от наличия профиля и прав администратора
    keyboard = start_kb(user_id in ADMIN_IDS, client is not None)
    
    await message.answer(welcome_text, reply_markup=keyboard)

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    # Формируем текст справки
    help_text = (
        "🔍 Справка по командам бота:\n\n"
        "/start - Начало работы с ботом\n"
        "/help - Показать эту справку\n"
        "/profile - Посмотреть информацию о вашем профиле\n"
        "/about - Информация о сервисе\n\n"
    )
    
    if message.from_user.id in ADMIN_IDS:
        help_text += (
            "👨‍💻 Команды администратора:\n"
            "/admin - Панель администратора\n"
            "/addclient - Добавить нового клиента\n"
            "/status - Статус системы\n\n"
        )
    
    help_text += (
        f"💬 Поддержка: {SUPPORT_CONTACT}\n"
        f"🌐 Веб-сайт: {WEBSITE_URL}\n\n"
        f"{COPYRIGHT}"
    )
    
    await message.answer(help_text, reply_markup=help_kb())

# Обработчик команды /about
@router.message(Command("about"))
async def cmd_about(message: Message):
    about_text = read_template("about.txt")
    
    # Заменяем плейсхолдеры в тексте
    about_text = about_text.replace("{bot_version}", BOT_VERSION)
    about_text = about_text.replace("{support_contact}", SUPPORT_CONTACT)
    about_text = about_text.replace("{website_url}", WEBSITE_URL)
    about_text = about_text.replace("{copyright}", COPYRIGHT)
    
    await message.answer(about_text, reply_markup=start_kb(message.from_user.id in ADMIN_IDS, False))

# Обработчик команды /profile
@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    
    # Получаем профиль пользователя
    client = await client_model.get_client_by_user_id(user_id)
    
    if not client:
        await message.answer(
            "❌ У вас нет профиля VPN.\n\n"
            "Для получения доступа к VPN обратитесь к администратору."
        )
        return
    
    await show_user_profile(message, client)

async def show_user_profile(message, client):
    """Показывает профиль пользователя"""
    client_id, name, user_id, email, create_date, expiry_date, last_connection, is_active, is_blocked, *_ = client
    
    # Определяем статус клиента
    if is_blocked:
        status = "⛔ Заблокирован"
    elif not is_active:
        status = "❌ Неактивен"
    else:
        status = "✅ Активен"
    
    # Форматируем информацию о сроке действия
    if expiry_date:
        expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        
        if expiry_date_obj > now:
            days_left = (expiry_date_obj - now).days
            expiry_info = f"⏳ Срок действия: до {expiry_date} ({days_left} дней осталось)"
        else:
            expiry_info = f"⌛ Срок действия: истек {expiry_date}"
    else:
        expiry_info = "⏳ Срок действия: бессрочно"
    
    # Формируем текст сообщения
    text = (
        f"👤 Ваш профиль RuCoder VPN\n\n"
        f"🆔 ID: {client_id}\n"
        f"👤 Имя: {name}\n"
        f"{status}\n"
        f"📅 Дата создания: {create_date}\n"
        f"{expiry_info}\n"
    )
    
    if last_connection:
        text += f"🔄 Последнее подключение: {last_connection}\n"
    
    if email:
        text += f"📧 Email: {email}\n"
    
    # Добавляем инструкции, если профиль активен
    if is_active and not is_blocked:
        text += "\n🔧 Для настройки VPN вы можете использовать кнопки ниже."
    
    await message.answer(
        text,
        reply_markup=profile_kb(is_active and not is_blocked)
    )

@router.callback_query(F.data == "download_config")
async def cb_download_config(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.answer()
    
    # Получаем профиль пользователя
    client = await client_model.get_client_by_user_id(user_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ У вас нет профиля VPN.\n\n"
            "Для получения доступа к VPN обратитесь к администратору.",
            reply_markup=back_to_main_kb()
        )
        return
    
    client_id, name, *_ = client
    
    # Проверяем существование конфигурационного файла
    config_path = os.path.join(CLIENTS_DIR, name, f"{name}.conf")
    
    if not os.path.exists(config_path):
        await callback.message.edit_text(
            "❌ Конфигурационный файл не найден.\n\n"
            "Пожалуйста, обратитесь к администратору.",
            reply_markup=back_to_main_kb()
        )
        return
    
    # Отправляем конфигурационный файл
    await callback.bot.send_document(
        user_id,
        FSInputFile(config_path),
        caption="📋 Ваш конфигурационный файл WireGuard"
    )
    
    # Генерируем и отправляем QR-код
    qr_path = await generate_qr_from_config(config_path)
    
    if qr_path:
        await callback.bot.send_photo(
            user_id,
            FSInputFile(qr_path),
            caption="🔄 Отсканируйте этот QR-код в приложении WireGuard для быстрой настройки"
        )
        
        # Удаляем временный файл QR-кода
        os.remove(qr_path)
    
    await callback.message.edit_text(
        "✅ Ваши данные для подключения отправлены.\n\n"
        "Для настройки WireGuard выберите инструкцию для вашего устройства:",
        reply_markup=setup_kb()
    )

@router.callback_query(F.data == "show_qr")
async def cb_show_qr(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.answer()
    
    # Получаем профиль пользователя
    client = await client_model.get_client_by_user_id(user_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ У вас нет профиля VPN.\n\n"
            "Для получения доступа к VPN обратитесь к администратору.",
            reply_markup=back_to_main_kb()
        )
        return
    
    client_id, name, *_ = client
    
    # Проверяем существование конфигурационного файла
    config_path = os.path.join(CLIENTS_DIR, name, f"{name}.conf")
    
    if not os.path.exists(config_path):
        await callback.message.edit_text(
            "❌ Конфигурационный файл не найден.\n\n"
            "Пожалуйста, обратитесь к администратору.",
            reply_markup=back_to_main_kb()
        )
        return
    
    # Генерируем и отправляем QR-код
    qr_path = await generate_qr_from_config(config_path)
    
    if qr_path:
        await callback.message.answer_photo(
            FSInputFile(qr_path),
            caption="🔄 Отсканируйте этот QR-код в приложении WireGuard для быстрой настройки"
        )
        
        # Удаляем временный файл QR-кода
        os.remove(qr_path)
        
        await callback.message.edit_text(
            "Выберите инструкцию для настройки WireGuard на вашем устройстве:",
            reply_markup=setup_kb()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при генерации QR-кода.\n\n"
            "Пожалуйста, обратитесь к администратору.",
            reply_markup=back_to_main_kb()
        )

@router.callback_query(F.data.startswith("setup_"))
async def cb_setup_instructions(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.answer()
    
    device_type = callback.data.split("_")[1]
    
    # Определяем название шаблона в зависимости от типа устройства
    template_name = f"setup_{device_type}.txt"
    
    # Получаем инструкции из шаблона
    instructions = read_template(template_name)
    
    # Получаем профиль пользователя для персонализации инструкций
    client = await client_model.get_client_by_user_id(user_id)
    
    if client:
        client_name = client[1]  # name - индекс 1
        instructions = instructions.replace("{client_name}", client_name)
    
    # Заменяем общие плейсхолдеры
    instructions = instructions.replace("{support_contact}", SUPPORT_CONTACT)
    instructions = instructions.replace("{website_url}", WEBSITE_URL)
    instructions = instructions.replace("{copyright}", COPYRIGHT)
    
    await callback.message.edit_text(
        instructions,
        reply_markup=back_to_main_kb()
    )

@router.callback_query(F.data == "user_faq")
async def cb_user_faq(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.answer()
    
    # Получаем FAQ из шаблона
    faq_text = read_template("faq.txt")
    
    # Заменяем плейсхолдеры
    faq_text = faq_text.replace("{support_contact}", SUPPORT_CONTACT)
    faq_text = faq_text.replace("{website_url}", WEBSITE_URL)
    faq_text = faq_text.replace("{copyright}", COPYRIGHT)
    
    await callback.message.edit_text(
        faq_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "user_feedback")
async def cb_user_feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserStates.feedback)
    
    await callback.message.edit_text(
        "💬 Обратная связь\n\n"
        "Напишите ваше сообщение, вопрос или предложение. "
        "Администратор ответит вам в ближайшее время.",
        reply_markup=back_to_main_kb()
    )

@router.message(UserStates.feedback)
async def process_feedback(message: Message, state: FSMContext):
    user_id = message.from_user.id
    feedback_text = message.text
    
    if not feedback_text:
        await message.answer(
            "❌ Сообщение не может быть пустым. Пожалуйста, введите текст вашего сообщения.",
            reply_markup=back_to_main_kb()
        )
        return
    
    # Сохраняем обратную связь
    feedback_id = await feedback_model.create_feedback(user_id, feedback_text)
    
    if feedback_id:
        # Уведомляем пользователя
        await message.answer(
            "✅ Ваше сообщение отправлено администратору!\n\n"
            f"Мы ответим вам в ближайшее время.",
            reply_markup=back_to_main_kb()
        )
        
        # Уведомляем администраторов о новой обратной связи
        for admin_id in ADMIN_IDS:
            try:
                client = await client_model.get_client_by_user_id(user_id)
                client_name = client[1] if client else f"Пользователь {user_id}"
                
                admin_notification = (
                    f"📫 Новое сообщение обратной связи!\n\n"
                    f"От: {client_name}\n"
                    f"ID: {user_id}\n\n"
                    f"Сообщение:\n{feedback_text}"
                )
                
                await message.bot.send_message(admin_id, admin_notification)
            except Exception as e:
                logger.error(f"Ошибка при уведомлении администратора {admin_id}: {e}")
    else:
        await message.answer(
            "❌ Произошла ошибка при отправке сообщения.\n\n"
            f"Пожалуйста, попробуйте позже или свяжитесь с поддержкой: {SUPPORT_CONTACT}",
            reply_markup=back_to_main_kb()
        )
    
    await state.clear()

@router.callback_query(F.data == "user_back")
async def cb_user_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    
    # Получаем информацию о пользователе
    user_id = callback.from_user.id
    client = await client_model.get_client_by_user_id(user_id)
    
    await callback.message.edit_text(
        f"👋 Главное меню RuCoder VPN\n\n"
        f"Выберите действие:",
        reply_markup=start_kb(user_id in ADMIN_IDS, client is not None)
    )

@router.callback_query(F.data == "faq_question_1")
async def cb_faq_question_1(callback: CallbackQuery):
    await callback.answer()
    
    question_text = (
        "❓ Что такое WireGuard?\n\n"
        "WireGuard — это современный, быстрый и безопасный VPN-протокол, который обеспечивает "
        "защищенное соединение с минимальной нагрузкой на батарею и высокой скоростью работы.\n\n"
        "Он намного быстрее и проще в использовании, чем другие VPN-протоколы, такие как OpenVPN или IPSec."
    )
    
    await callback.message.edit_text(
        question_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "faq_question_2")
async def cb_faq_question_2(callback: CallbackQuery):
    await callback.answer()
    
    question_text = (
        "❓ Как установить WireGuard на мое устройство?\n\n"
        "1. Скачайте официальное приложение WireGuard из магазина приложений вашего устройства:\n"
        "   • iOS: App Store\n"
        "   • Android: Google Play\n"
        "   • Windows: wireguard.com/install\n"
        "   • macOS: App Store или wireguard.com/install\n"
        "   • Linux: используйте пакетный менеджер вашего дистрибутива\n\n"
        "2. После установки приложения используйте QR-код или конфигурационный файл, "
        "предоставленный ботом, для быстрой настройки."
    )
    
    await callback.message.edit_text(
        question_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "faq_question_3")
async def cb_faq_question_3(callback: CallbackQuery):
    await callback.answer()
    
    question_text = (
        "❓ Что делать, если VPN не подключается?\n\n"
        "1. Убедитесь, что вы используете актуальную конфигурацию. Загрузите её заново из бота.\n\n"
        "2. Проверьте подключение к интернету на вашем устройстве.\n\n"
        "3. Некоторые сети могут блокировать VPN-соединения. Попробуйте подключиться через другую сеть.\n\n"
        "4. Перезапустите приложение WireGuard и попробуйте подключиться снова.\n\n"
        f"Если проблема не решена, обратитесь в поддержку: {SUPPORT_CONTACT}"
    )
    
    await callback.message.edit_text(
        question_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "faq_question_4")
async def cb_faq_question_4(callback: CallbackQuery):
    await callback.answer()
    
    question_text = (
        "❓ Как узнать срок действия моего VPN-доступа?\n\n"
        "Информация о сроке действия вашего VPN-доступа отображается в вашем профиле. "
        "Вы можете проверить её, нажав на кнопку «Мой профиль» в главном меню или "
        "используя команду /profile.\n\n"
        f"Если ваш доступ истек или скоро истечет, свяжитесь с администратором: {SUPPORT_CONTACT}"
    )
    
    await callback.message.edit_text(
        question_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "faq_question_5")
async def cb_faq_question_5(callback: CallbackQuery):
    await callback.answer()
    
    question_text = (
        "❓ Безопасно ли использовать этот VPN?\n\n"
        "Да, наш VPN-сервис использует современный протокол WireGuard, который обеспечивает "
        "высокий уровень безопасности и конфиденциальности.\n\n"
        "• Шифрование на уровне военных стандартов\n"
        "• Отсутствие логирования вашей активности\n"
        "• Защита от утечек DNS\n"
        "• Защита от отслеживания\n\n"
        "Мы не собираем и не храним никакую информацию о вашей активности в интернете."
    )
    
    await callback.message.edit_text(
        question_text,
        reply_markup=faq_kb()
    )

@router.callback_query(F.data == "speed_test")
async def cb_speed_test(callback: CallbackQuery):
    """Обработчик запроса на тестирование скорости соединения"""
    await callback.answer("⏳ Запуск теста скорости, пожалуйста, подождите...")
    
    # Отправляем сообщение о начале тестирования
    await callback.message.edit_text(
        "🔄 Выполняется тестирование скорости соединения...\n\n"
        "⏳ Проверка пинга...\n"
        "⏳ Проверка скорости загрузки...\n\n"
        "Это может занять от 15 до 30 секунд. Пожалуйста, подождите.",
        reply_markup=None
    )
    
    try:
        # Выполняем тест скорости и получаем результаты
        results_text = await run_speed_test()
        
        # Дополняем сообщение о результатах
        full_text = (
            "✅ Тест скорости завершен!\n\n"
            f"{results_text}\n\n"
            f"🌐 Тестирование выполнено через: RuCoder VPN\n"
            f"⏱ Дата и время: {time.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"ℹ️ Результаты могут отличаться в зависимости от вашего интернет-провайдера "
            f"и текущей нагрузки на сеть."
        )
        
        # Отправляем пользователю результаты тестирования
        await callback.message.edit_text(
            full_text,
            reply_markup=profile_kb()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании скорости: {e}")
        
        # В случае ошибки отправляем сообщение пользователю
        await callback.message.edit_text(
            "❌ Произошла ошибка при тестировании скорости соединения.\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            reply_markup=profile_kb()
        )

def register_user_handlers(dp):
    """Регистрирует обработчики команд пользователя"""
    dp.include_router(router)
