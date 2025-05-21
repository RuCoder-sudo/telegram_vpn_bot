#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Клавиатуры настройки для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def setup_main_kb():
    """Главная клавиатура настройки"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 Проверка WireGuard", callback_data="setup_check_wireguard")
        ],
        [
            InlineKeyboardButton(text="🔄 Перезапуск WireGuard", callback_data="setup_restart_wireguard")
        ],
        [
            InlineKeyboardButton(text="🔧 Переустановка WireGuard", callback_data="setup_reinstall_wireguard")
        ],
        [
            InlineKeyboardButton(text="🌐 Обновить информацию о сервере", callback_data="setup_update_server_info")
        ],
        [
            InlineKeyboardButton(text="⬅️ Вернуться в панель администратора", callback_data="setup_exit")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def setup_confirm_kb(confirm_callback):
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, выполнить", callback_data=confirm_callback),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="setup_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_setup_kb():
    """Кнопка возврата в меню настройки"""
    keyboard = [
        [
            InlineKeyboardButton(text="⬅️ Вернуться в меню настройки", callback_data="setup_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
