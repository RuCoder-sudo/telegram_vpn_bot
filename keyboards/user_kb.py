#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Клавиатуры пользователя для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def start_kb(is_admin=False, has_profile=False):
    """Главная клавиатура бота"""
    keyboard = []
    
    # Кнопки для пользователей с профилем
    if has_profile:
        keyboard.append([
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="user_profile")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📱 Настройка устройств", callback_data="user_setup"),
            InlineKeyboardButton(text="❓ FAQ", callback_data="user_faq")
        ])
    
    # Общие кнопки
    keyboard.append([
        InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="user_about"),
        InlineKeyboardButton(text="💬 Обратная связь", callback_data="user_feedback")
    ])
    
    # Кнопка для администраторов
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(text="👨‍💻 Панель администратора", callback_data="admin")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def help_kb():
    """Клавиатура для страницы помощи"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️ Вернуться", callback_data="user_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def profile_kb(is_active=True):
    """Клавиатура для страницы профиля"""
    keyboard = []
    
    # Кнопки доступные только для активных профилей
    if is_active:
        keyboard.append([
            InlineKeyboardButton(text="📥 Скачать конфигурацию", callback_data="download_config"),
            InlineKeyboardButton(text="📱 Показать QR-код", callback_data="show_qr")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📚 Инструкции по настройке", callback_data="user_setup")
        ])
        
        keyboard.append([
            InlineKeyboardButton(text="🚀 Тест скорости", callback_data="speed_test")
        ])
    
    # Общие кнопки
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Вернуться", callback_data="user_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def setup_kb():
    """Клавиатура для выбора инструкций по настройке"""
    keyboard = [
        [
            InlineKeyboardButton(text="📱 Android", callback_data="setup_android"),
            InlineKeyboardButton(text="📱 iOS", callback_data="setup_ios")
        ],
        [
            InlineKeyboardButton(text="💻 Windows", callback_data="setup_windows"),
            InlineKeyboardButton(text="💻 macOS", callback_data="setup_macos")
        ],
        [
            InlineKeyboardButton(text="🐧 Linux", callback_data="setup_linux")
        ],
        [
            InlineKeyboardButton(text="⬅️ Вернуться", callback_data="user_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def faq_kb():
    """Клавиатура для страницы FAQ"""
    keyboard = [
        [
            InlineKeyboardButton(text="❓ Что такое WireGuard?", callback_data="faq_question_1")
        ],
        [
            InlineKeyboardButton(text="❓ Как установить WireGuard?", callback_data="faq_question_2")
        ],
        [
            InlineKeyboardButton(text="❓ VPN не подключается", callback_data="faq_question_3")
        ],
        [
            InlineKeyboardButton(text="❓ Срок действия доступа", callback_data="faq_question_4")
        ],
        [
            InlineKeyboardButton(text="❓ Безопасность VPN", callback_data="faq_question_5")
        ],
        [
            InlineKeyboardButton(text="⬅️ Вернуться", callback_data="user_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def feedback_kb():
    """Клавиатура для страницы обратной связи"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️ Вернуться", callback_data="user_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_main_kb():
    """Кнопка возврата в главное меню"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="user_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
