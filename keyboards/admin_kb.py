#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Клавиатуры администратора для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_main_kb():
    """Главная клавиатура администратора"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Список клиентов", callback_data="admin_list_clients"),
            InlineKeyboardButton(text="➕ Добавить клиента", callback_data="admin_add_client")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_statistics"),
            InlineKeyboardButton(text="🖥️ Мониторинг", callback_data="admin_monitoring")
        ],
        [
            InlineKeyboardButton(text="📣 Массовая рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🔧 Статус системы", callback_data="admin_system_status")
        ],
        [
            InlineKeyboardButton(text="🛠️ Настройка сервера", callback_data="setup")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_admin_kb():
    """Кнопка возврата в панель администратора"""
    keyboard = [
        [
            InlineKeyboardButton(text="« Назад в панель администратора", callback_data="admin_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def client_list_kb(clients):
    """Клавиатура со списком клиентов"""
    keyboard = []
    
    # Добавляем кнопки для каждого клиента
    for client in clients[:10]:  # Показываем максимум 10 клиентов на странице
        client_id, name, *_ = client
        keyboard.append([
            InlineKeyboardButton(text=f"{name}", callback_data=f"manage_client_{client_id}")
        ])
    
    # Добавляем кнопку возврата
    keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data="admin_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def client_manage_kb(client_id, is_active, is_blocked):
    """Клавиатура управления клиентом"""
    keyboard = []
    
    # Кнопки активации/деактивации
    if is_active:
        keyboard.append([
            InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"toggle_client_deactivate_{client_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="✅ Активировать", callback_data=f"toggle_client_activate_{client_id}")
        ])
    
    # Кнопки блокировки/разблокировки
    if is_blocked:
        keyboard.append([
            InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"toggle_client_unblock_{client_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="🔒 Заблокировать", callback_data=f"toggle_client_block_{client_id}")
        ])
    
    # Дополнительные действия
    keyboard.append([
        InlineKeyboardButton(text="🗂️ Конфигурация", callback_data=f"client_config_{client_id}"),
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"client_stats_{client_id}")
    ])
    
    # Удаление клиента
    keyboard.append([
        InlineKeyboardButton(text="🗑️ Удалить клиента", callback_data=f"delete_client_{client_id}")
    ])
    
    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton(text="« Назад к списку", callback_data="admin_list_clients")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_stats_kb():
    """Клавиатура страницы статистики"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Клиенты", callback_data="stats_clients"),
            InlineKeyboardButton(text="🖥️ Сервер", callback_data="stats_server")
        ],
        [
            InlineKeyboardButton(text="📈 Трафик", callback_data="stats_traffic"),
            InlineKeyboardButton(text="📊 Экспорт", callback_data="stats_export")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="admin_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def monitoring_kb():
    """Клавиатура страницы мониторинга"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_monitoring"),
            InlineKeyboardButton(text="🔁 Перезапустить WireGuard", callback_data="restart_wireguard")
        ],
        [
            InlineKeyboardButton(text="« Назад", callback_data="admin_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def broadcast_kb():
    """Клавиатура подтверждения рассылки"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Отправить всем", callback_data="send_broadcast"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="admin_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_action_kb(callback_data):
    """Клавиатура подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Да, подтверждаю", callback_data=callback_data),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_back")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def paginate_kb(callback_prefix, current_page, total_pages, back_callback="admin_back"):
    """Клавиатура пагинации"""
    keyboard = []
    
    # Добавляем навигационные кнопки
    navigation = []
    
    if current_page > 1:
        navigation.append(
            InlineKeyboardButton(text="« Пред", callback_data=f"{callback_prefix}_{current_page - 1}")
        )
    
    navigation.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="do_nothing")
    )
    
    if current_page < total_pages:
        navigation.append(
            InlineKeyboardButton(text="След »", callback_data=f"{callback_prefix}_{current_page + 1}")
        )
    
    keyboard.append(navigation)
    
    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton(text="« Назад", callback_data=back_callback)
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def generate_clients_kb(clients, page, total_pages):
    """Генерирует клавиатуру со списком клиентов и пагинацией"""
    keyboard = []
    
    # Определяем клиентов для текущей страницы
    start_idx = (page - 1) * 5
    end_idx = min(start_idx + 5, len(clients))
    page_clients = clients[start_idx:end_idx]
    
    # Добавляем кнопки для каждого клиента
    for client in page_clients:
        client_id, name, *_ = client
        keyboard.append([
            InlineKeyboardButton(text=f"{name}", callback_data=f"manage_client_{client_id}")
        ])
    
    # Добавляем навигационные кнопки
    navigation = []
    
    if page > 1:
        navigation.append(
            InlineKeyboardButton(text="« Пред", callback_data=f"client_page_{page - 1}")
        )
    
    navigation.append(
        InlineKeyboardButton(text=f"Стр {page}/{total_pages}", callback_data="do_nothing")
    )
    
    if page < total_pages:
        navigation.append(
            InlineKeyboardButton(text="След »", callback_data=f"client_page_{page + 1}")
        )
    
    keyboard.append(navigation)
    
    # Кнопка добавления нового клиента
    keyboard.append([
        InlineKeyboardButton(text="➕ Добавить клиента", callback_data="admin_add_client")
    ])
    
    # Кнопка возврата
    keyboard.append([
        InlineKeyboardButton(text="« Назад в панель администратора", callback_data="admin_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
