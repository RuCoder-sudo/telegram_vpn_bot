#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд администратора для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS, CLIENTS_DIR, BOT_VERSION, COPYRIGHT, WG_CONFIG_PATH
from keyboards.admin_kb import (
    admin_main_kb, client_list_kb, client_manage_kb, admin_stats_kb,
    confirm_action_kb, monitoring_kb, broadcast_kb, back_to_admin_kb,
    paginate_kb, generate_clients_kb
)
from database.models import ClientModel, StatsModel, NotificationModel, ServerMetricsModel
from utils.vpn_manager import VPNManager

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляры моделей
client_model = ClientModel()
stats_model = StatsModel()
notification_model = NotificationModel()
metrics_model = ServerMetricsModel()
vpn_manager = VPNManager()

# Определение состояний для FSM
class AdminStates(StatesGroup):
    add_client = State()
    edit_client = State()
    delete_client = State()
    block_client = State()
    broadcast_message = State()
    client_expiry = State()
    send_feedback_response = State()
    server_monitoring = State()

# Фильтр для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Обработчик команды /admin
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен. Вы не являетесь администратором.")
        return
    
    await message.answer(
        f"👨‍💻 Панель администратора RuCoder VPN\n"
        f"Версия бота: {BOT_VERSION}\n\n"
        f"Выберите действие:",
        reply_markup=admin_main_kb()
    )

# Обработчик нажатия на кнопку "Список клиентов"
@router.callback_query(F.data == "admin_list_clients")
async def cb_list_clients(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    clients = await client_model.get_all_clients()
    
    if not clients:
        await callback.message.edit_text(
            "📋 Список клиентов пуст",
            reply_markup=back_to_admin_kb()
        )
        return
    
    page = 1
    total_pages = (len(clients) + 4) // 5  # 5 клиентов на странице
    
    await show_clients_page(callback.message, clients, page, total_pages)

async def show_clients_page(message, clients, page, total_pages):
    """Показывает страницу со списком клиентов"""
    start_idx = (page - 1) * 5
    end_idx = min(start_idx + 5, len(clients))
    
    page_clients = clients[start_idx:end_idx]
    
    text = f"📋 Список клиентов (страница {page}/{total_pages}):\n\n"
    
    for client in page_clients:
        # Формат: ID, имя, статус, дата создания, дата истечения
        client_id, name, user_id, email, create_date, expiry_date, is_active, is_blocked, *_ = client
        
        status = "✅ Активен" if is_active and not is_blocked else "⛔ Заблокирован" if is_blocked else "❌ Неактивен"
        expiry_info = f"до {expiry_date}" if expiry_date else "бессрочно"
        
        text += f"🆔 {client_id} | 👤 {name} | {status}\n"
        text += f"📅 Создан: {create_date} | ⏳ Действует: {expiry_info}\n"
        if user_id:
            text += f"🔗 Telegram ID: {user_id}\n"
        if email:
            text += f"📧 Email: {email}\n"
        text += "\n"
    
    await message.edit_text(
        text,
        reply_markup=generate_clients_kb(clients, page, total_pages)
    )

@router.callback_query(F.data.startswith("client_page_"))
async def cb_client_page(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    page = int(callback.data.split("_")[-1])
    clients = await client_model.get_all_clients()
    
    if not clients:
        await callback.message.edit_text(
            "📋 Список клиентов пуст",
            reply_markup=back_to_admin_kb()
        )
        return
    
    total_pages = (len(clients) + 4) // 5  # 5 клиентов на странице
    
    await show_clients_page(callback.message, clients, page, total_pages)

@router.callback_query(F.data.startswith("manage_client_"))
async def cb_manage_client(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    client_id = int(callback.data.split("_")[-1])
    client = await client_model.get_client_by_id(client_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ Клиент не найден",
            reply_markup=back_to_admin_kb()
        )
        return
    
    client_id, name, user_id, email, create_date, expiry_date, last_connection, is_active, is_blocked, allowed_ips, public_key, private_key, data_limit, data_used = client
    
    status = "✅ Активен" if is_active and not is_blocked else "⛔ Заблокирован" if is_blocked else "❌ Неактивен"
    expiry_info = f"до {expiry_date}" if expiry_date else "бессрочно"
    connection_info = f"{last_connection}" if last_connection else "никогда"
    
    data_limit_str = f"{data_limit/(1024*1024*1024):.2f} ГБ" if data_limit else "неограничено"
    data_used_str = f"{data_used/(1024*1024*1024):.2f} ГБ" if data_used else "0 ГБ"
    
    text = f"📝 Управление клиентом:\n\n"
    text += f"🆔 ID: {client_id}\n"
    text += f"👤 Имя: {name}\n"
    text += f"📱 Статус: {status}\n"
    text += f"📅 Создан: {create_date}\n"
    text += f"⏳ Действует: {expiry_info}\n"
    text += f"🔄 Последнее подключение: {connection_info}\n"
    text += f"📊 Лимит трафика: {data_limit_str}\n"
    text += f"📈 Использовано: {data_used_str}\n"
    
    if user_id:
        text += f"🔗 Telegram ID: {user_id}\n"
    if email:
        text += f"📧 Email: {email}\n"
    if allowed_ips:
        text += f"🌐 Разрешённые IP: {allowed_ips}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=client_manage_kb(client_id, is_active, is_blocked)
    )

@router.callback_query(F.data.startswith("toggle_client_"))
async def cb_toggle_client(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Формат: toggle_client_{action}_{client_id}
    parts = callback.data.split("_")
    action = parts[2]
    client_id = int(parts[3])
    
    client = await client_model.get_client_by_id(client_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ Клиент не найден",
            reply_markup=back_to_admin_kb()
        )
        return
    
    if action == "activate":
        await client_model.update_client(client_id, is_active=1)
        await callback.message.edit_text(
            f"✅ Клиент {client[1]} активирован",
            reply_markup=back_to_admin_kb()
        )
    elif action == "deactivate":
        await client_model.update_client(client_id, is_active=0)
        await callback.message.edit_text(
            f"❌ Клиент {client[1]} деактивирован",
            reply_markup=back_to_admin_kb()
        )
    elif action == "block":
        await client_model.update_client(client_id, is_blocked=1)
        await callback.message.edit_text(
            f"⛔ Клиент {client[1]} заблокирован",
            reply_markup=back_to_admin_kb()
        )
    elif action == "unblock":
        await client_model.update_client(client_id, is_blocked=0)
        await callback.message.edit_text(
            f"✅ Блокировка снята с клиента {client[1]}",
            reply_markup=back_to_admin_kb()
        )

@router.callback_query(F.data.startswith("delete_client_"))
async def cb_delete_client_confirm(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    client_id = int(callback.data.split("_")[-1])
    client = await client_model.get_client_by_id(client_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ Клиент не найден",
            reply_markup=back_to_admin_kb()
        )
        return
    
    await callback.message.edit_text(
        f"⚠️ Вы действительно хотите удалить клиента {client[1]}?\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=confirm_action_kb(f"confirm_delete_{client_id}")
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
async def cb_delete_client(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    client_id = int(callback.data.split("_")[-1])
    client = await client_model.get_client_by_id(client_id)
    
    if not client:
        await callback.message.edit_text(
            "❌ Клиент не найден",
            reply_markup=back_to_admin_kb()
        )
        return
    
    # Удаляем клиента из WireGuard
    success = vpn_manager.delete_client(client[1], client[10])  # name, public_key
    
    if success:
        # Удаляем клиента из базы данных
        await client_model.delete_client(client_id)
        await callback.message.edit_text(
            f"✅ Клиент {client[1]} успешно удален",
            reply_markup=back_to_admin_kb()
        )
    else:
        await callback.message.edit_text(
            f"❌ Ошибка при удалении клиента {client[1]} из WireGuard",
            reply_markup=back_to_admin_kb()
        )

@router.callback_query(F.data == "admin_add_client")
async def cb_add_client(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.add_client)
    
    await callback.message.edit_text(
        "🆕 Добавление нового клиента\n\n"
        "Введите имя для нового клиента (латинские буквы, цифры и знаки подчеркивания):",
        reply_markup=back_to_admin_kb()
    )

@router.message(AdminStates.add_client)
async def process_client_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен")
        await state.clear()
        return
    
    # Проверка формата имени
    client_name = message.text.strip()
    if not client_name.replace("_", "").isalnum():
        await message.answer(
            "⚠️ Ошибка: Имя клиента должно содержать только латинские буквы, цифры и знаки подчеркивания.\n\n"
            "Введите корректное имя:",
            reply_markup=back_to_admin_kb()
        )
        return
    
    # Проверка существования клиента с таким именем
    existing_client = await client_model.get_client_by_name(client_name)
    if existing_client:
        await message.answer(
            f"⚠️ Ошибка: Клиент с именем {client_name} уже существует.\n\n"
            f"Введите другое имя:",
            reply_markup=back_to_admin_kb()
        )
        return
    
    # Создание нового VPN-клиента
    await message.answer("⏳ Создание конфигурации VPN... Пожалуйста, подождите")
    
    # Генерируем конфигурацию VPN
    client_data = vpn_manager.create_client(client_name)
    
    if not client_data:
        await message.answer(
            "❌ Ошибка при создании конфигурации VPN",
            reply_markup=admin_main_kb()
        )
        await state.clear()
        return
    
    # Сохраняем клиента в базу данных
    client = await client_model.create_client(
        client_name,
        public_key=client_data["public_key"],
        private_key=client_data["private_key"]
    )
    
    if not client:
        await message.answer(
            "❌ Ошибка при сохранении клиента в базу данных",
            reply_markup=admin_main_kb()
        )
        await state.clear()
        return
    
    # Отправляем конфигурационный файл
    config_path = os.path.join(CLIENTS_DIR, client_name, f"{client_name}.conf")
    
    if os.path.exists(config_path):
        await message.answer_document(
            FSInputFile(config_path),
            caption=f"✅ Клиент {client_name} успешно создан!\n\n"
                    f"📱 Используйте этот файл конфигурации для настройки WireGuard на устройстве."
        )
        
        # Генерируем и отправляем QR-код
        from utils.qr_generator import generate_qr_from_config
        qr_path = await generate_qr_from_config(config_path)
        
        if qr_path:
            await message.answer_photo(
                FSInputFile(qr_path),
                caption="🔄 Отсканируйте этот QR-код в приложении WireGuard для быстрой настройки."
            )
            
            # Удаляем временный файл QR-кода
            os.remove(qr_path)
    else:
        await message.answer(
            f"⚠️ Конфигурационный файл создан, но не найден по пути {config_path}",
            reply_markup=admin_main_kb()
        )
    
    await state.clear()
    await message.answer(
        "Выберите дальнейшее действие:",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_statistics")
async def cb_admin_statistics(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Получаем общую статистику
    stats = await stats_model.get_overall_stats()
    
    # Получаем последние метрики сервера
    server_metrics = await metrics_model.get_latest_metrics(1)
    
    # Получаем список активных клиентов
    active_clients = await client_model.get_active_clients()
    
    # Формируем текст сообщения
    text = f"📊 Статистика RuCoder VPN\n\n"
    
    # Статистика клиентов
    text += f"👥 Всего клиентов: {len(await client_model.get_all_clients())}\n"
    text += f"✅ Активных клиентов: {len(active_clients)}\n"
    text += f"🔄 Всего подключений: {stats['connections_count']}\n"
    text += f"⚡ Активных сессий: {stats['active_sessions']}\n\n"
    
    # Статистика трафика
    received_gb = stats['total_received'] / (1024 * 1024 * 1024) if stats['total_received'] else 0
    sent_gb = stats['total_sent'] / (1024 * 1024 * 1024) if stats['total_sent'] else 0
    
    text += f"📥 Получено: {received_gb:.2f} ГБ\n"
    text += f"📤 Отправлено: {sent_gb:.2f} ГБ\n"
    text += f"📊 Общий трафик: {received_gb + sent_gb:.2f} ГБ\n\n"
    
    # Статистика сервера
    if server_metrics:
        metrics = server_metrics[0]
        timestamp, cpu, memory, disk, net_in, net_out, connections = metrics
        
        text += f"💻 Сервер (последнее обновление: {timestamp}):\n"
        text += f"  CPU: {cpu:.1f}%\n"
        text += f"  RAM: {memory:.1f}%\n"
        text += f"  Диск: {disk:.1f}%\n"
        
        # Переводим байты в удобные единицы измерения
        net_in_mbps = net_in * 8 / 1024 / 1024 if net_in else 0
        net_out_mbps = net_out * 8 / 1024 / 1024 if net_out else 0
        
        text += f"  Сеть: ⬇️ {net_in_mbps:.2f} Мбит/с | ⬆️ {net_out_mbps:.2f} Мбит/с\n"
        text += f"  Активные подключения: {connections}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=admin_stats_kb()
    )

@router.callback_query(F.data.startswith("stats_"))
async def cb_stats_detail(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    stats_type = callback.data.split("_")[1]
    
    if stats_type == "clients":
        # Список активных клиентов и их использование
        active_clients = await client_model.get_active_clients()
        
        if not active_clients:
            await callback.message.edit_text(
                "📋 Нет активных клиентов",
                reply_markup=back_to_admin_kb()
            )
            return
        
        text = "👥 Статистика клиентов:\n\n"
        
        for client in active_clients[:15]:  # Показываем только первые 15 клиентов
            # Распаковываем только нужные элементы из client
            client_parts = list(client)
            client_id = client_parts[0]
            name = client_parts[1]
            last_connection = client_parts[-5]
            is_active = client_parts[-4]
            is_blocked = client_parts[-3]
            data_used = client_parts[-1]
            
            # Получаем общее использование трафика
            client_stats = await stats_model.get_client_usage_total(client_id)
            total_received, total_sent = client_stats
            
            # Переводим байты в мегабайты или гигабайты
            def format_bytes(bytes_count):
                if bytes_count is None:
                    return "0 Б"
                if bytes_count < 1024 * 1024:
                    return f"{bytes_count / 1024:.2f} КБ"
                elif bytes_count < 1024 * 1024 * 1024:
                    return f"{bytes_count / (1024 * 1024):.2f} МБ"
                else:
                    return f"{bytes_count / (1024 * 1024 * 1024):.2f} ГБ"
            
            text += f"👤 {name}\n"
            text += f"  📅 Последнее подключение: {last_connection or 'никогда'}\n"
            text += f"  📥 Получено: {format_bytes(total_received)}\n"
            text += f"  📤 Отправлено: {format_bytes(total_sent)}\n"
            text += f"  📊 Всего: {format_bytes(total_received + total_sent)}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=back_to_admin_kb()
        )
    
    elif stats_type == "server":
        # Статистика сервера за последние 24 часа
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        server_stats = await metrics_model.get_metrics_by_period(
            yesterday.strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d %H:%M:%S"),
            'hour'
        )
        
        if not server_stats:
            await callback.message.edit_text(
                "📊 Нет данных о сервере за последние 24 часа",
                reply_markup=back_to_admin_kb()
            )
            return
        
        text = "💻 Статистика сервера за 24 часа:\n\n"
        
        for i, stat in enumerate(server_stats[-12:]):  # Показываем последние 12 записей
            period, cpu, memory, disk, net_in, net_out, connections = stat
            
            text += f"⏰ {period}:\n"
            text += f"  CPU: {cpu:.1f}%\n"
            text += f"  RAM: {memory:.1f}%\n"
            text += f"  Диск: {disk:.1f}%\n"
            
            # Переводим байты в удобные единицы измерения
            net_in_mbps = net_in * 8 / 1024 / 1024 if net_in else 0
            net_out_mbps = net_out * 8 / 1024 / 1024 if net_out else 0
            
            text += f"  Сеть: ⬇️ {net_in_mbps:.2f} Мбит/с | ⬆️ {net_out_mbps:.2f} Мбит/с\n"
            text += f"  Подключения: {connections}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=back_to_admin_kb()
        )
    
    elif stats_type == "traffic":
        # Статистика общего трафика по дням за последний месяц
        stats = await stats_model.get_overall_stats()
        daily_stats = stats["daily_stats"]
        
        if not daily_stats:
            await callback.message.edit_text(
                "📊 Нет данных о трафике за последний месяц",
                reply_markup=back_to_admin_kb()
            )
            return
        
        text = "📊 Статистика трафика по дням:\n\n"
        
        for day, connections, received, sent in daily_stats[-15:]:  # Показываем последние 15 дней
            # Переводим байты в мегабайты или гигабайты
            received_str = f"{received / (1024*1024*1024):.2f} ГБ" if received and received > 1024*1024*1024 else f"{received / (1024*1024):.2f} МБ" if received else "0 Б"
            sent_str = f"{sent / (1024*1024*1024):.2f} ГБ" if sent and sent > 1024*1024*1024 else f"{sent / (1024*1024):.2f} МБ" if sent else "0 Б"
            
            text += f"📅 {day}:\n"
            text += f"  🔄 Подключения: {connections}\n"
            text += f"  📥 Получено: {received_str}\n"
            text += f"  📤 Отправлено: {sent_str}\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=back_to_admin_kb()
        )

@router.callback_query(F.data == "admin_monitoring")
async def cb_admin_monitoring(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Получаем статус WireGuard
    wg_status = vpn_manager.check_wireguard_status()
    
    # Получаем активные подключения
    active_connections = vpn_manager.get_active_connections()
    
    # Получаем последние метрики сервера
    server_metrics = await metrics_model.get_latest_metrics(1)
    
    # Получаем критические события
    critical_events = await metrics_model.get_critical_events()
    
    # Формируем текст сообщения
    text = f"🖥️ Мониторинг сервера\n\n"
    
    # Статус WireGuard
    text += f"✅ WireGuard: {'активен' if wg_status['is_active'] else '❌ не активен'}\n\n"
    
    # Информация о сервере
    if server_metrics:
        metrics = server_metrics[0]
        timestamp, cpu, memory, disk, net_in, net_out, connections = metrics
        
        text += f"💻 Сервер (последнее обновление: {timestamp}):\n"
        text += f"  CPU: {cpu:.1f}%\n"
        text += f"  RAM: {memory:.1f}%\n"
        text += f"  Диск: {disk:.1f}%\n"
        
        # Переводим байты в удобные единицы измерения
        net_in_mbps = net_in * 8 / 1024 / 1024 if net_in else 0
        net_out_mbps = net_out * 8 / 1024 / 1024 if net_out else 0
        
        text += f"  Сеть: ⬇️ {net_in_mbps:.2f} Мбит/с | ⬆️ {net_out_mbps:.2f} Мбит/с\n"
        text += f"  Активные подключения: {connections}\n\n"
    
    # Информация о подключениях
    text += f"🔌 Активные подключения ({len(active_connections)}):\n\n"
    
    if active_connections:
        for i, conn in enumerate(active_connections[:5]):  # Показываем только первые 5 подключений
            endpoint = conn.get("endpoint", "неизвестно")
            latest_handshake = conn.get("latest_handshake", "никогда")
            received = conn.get("received", "0 B")
            sent = conn.get("sent", "0 B")
            
            text += f"  {i+1}. Endpoint: {endpoint}\n"
            text += f"     Handshake: {latest_handshake}\n"
            text += f"     Трафик: ⬇️ {received} | ⬆️ {sent}\n\n"
    else:
        text += "  Нет активных подключений\n\n"
    
    # Критические события
    if critical_events:
        text += f"⚠️ Критические события ({len(critical_events)}):\n\n"
        for i, event in enumerate(critical_events[:3]):  # Показываем только первые 3 события
            timestamp, cpu, memory, disk, *_ = event
            
            text += f"  {i+1}. {timestamp}:\n"
            if cpu > 80:
                text += f"     CPU: {cpu:.1f}% ⚠️\n"
            if memory > 80:
                text += f"     RAM: {memory:.1f}% ⚠️\n"
            if disk > 90:
                text += f"     Диск: {disk:.1f}% ⚠️\n"
            text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=monitoring_kb()
    )

@router.callback_query(F.data == "restart_wireguard")
async def cb_restart_wireguard(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer("Перезапуск WireGuard...")
    
    success = vpn_manager.restart_wireguard()
    
    if success:
        await callback.message.edit_text(
            "✅ WireGuard успешно перезапущен",
            reply_markup=back_to_admin_kb()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при перезапуске WireGuard",
            reply_markup=back_to_admin_kb()
        )

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.broadcast_message)
    
    await callback.message.edit_text(
        "📣 Массовая рассылка\n\n"
        "Введите текст сообщения для отправки всем пользователям:",
        reply_markup=back_to_admin_kb()
    )

@router.message(AdminStates.broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен")
        await state.clear()
        return
    
    broadcast_text = message.text
    
    # Сохраняем текст сообщения в состоянии
    await state.update_data(broadcast_text=broadcast_text)
    
    preview_text = f"📣 Предварительный просмотр сообщения:\n\n{broadcast_text}\n\n"
    preview_text += "Выберите действие:"
    
    await message.answer(
        preview_text,
        reply_markup=broadcast_kb()
    )

@router.callback_query(F.data == "send_broadcast")
async def cb_send_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Получаем текст сообщения из состояния
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")
    
    if not broadcast_text:
        await callback.message.edit_text(
            "❌ Ошибка: текст сообщения не найден",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()
        return
    
    # Получаем всех клиентов с Telegram ID
    clients = await client_model.get_all_clients()
    telegram_users = [client for client in clients if client[2]]  # user_id - индекс 2
    
    if not telegram_users:
        await callback.message.edit_text(
            "❌ Нет пользователей с привязанными Telegram аккаунтами",
            reply_markup=back_to_admin_kb()
        )
        await state.clear()
        return
    
    # Отправляем сообщение пользователям
    sent_count = 0
    failed_count = 0
    
    await callback.message.edit_text(
        f"⏳ Отправка сообщений {len(telegram_users)} пользователям..."
    )
    
    bot = callback.bot
    
    for client in telegram_users:
        try:
            await bot.send_message(
                client[2],  # user_id
                f"📣 Сообщение от администратора RuCoder VPN:\n\n{broadcast_text}\n\n{COPYRIGHT}"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {client[2]}: {e}")
            failed_count += 1
        
        # Небольшая задержка, чтобы избежать ограничений API
        await asyncio.sleep(0.1)
    
    await callback.message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Результаты:\n"
        f"  ✓ Успешно отправлено: {sent_count}\n"
        f"  ✗ Ошибок отправки: {failed_count}\n",
        reply_markup=back_to_admin_kb()
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        f"👨‍💻 Панель администратора RuCoder VPN\n"
        f"Версия бота: {BOT_VERSION}\n\n"
        f"Выберите действие:",
        reply_markup=admin_main_kb()
    )

@router.callback_query(F.data == "admin_system_status")
async def cb_system_status(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Проверка статуса файла конфигурации WireGuard
    wg_config_exists = os.path.exists(WG_CONFIG_PATH)
    
    # Проверка статуса службы WireGuard
    wg_service_status = vpn_manager.check_wireguard_status()
    
    # Формируем текст сообщения
    text = "🖥️ Статус системы\n\n"
    
    # WireGuard
    text += "🔒 WireGuard:\n"
    text += f"  • Конфигурация: {'✅ найдена' if wg_config_exists else '❌ не найдена'}\n"
    text += f"  • Служба: {'✅ активна' if wg_service_status['is_active'] else '❌ не активна'}\n"
    
    # Информация о боте
    text += "\n🤖 Бот:\n"
    text += f"  • Версия: {BOT_VERSION}\n"
    text += f"  • База данных: ✅ подключена\n"
    
    # Статистика по файловой системе
    disk_usage = os.statvfs('/')
    free_disk_space = disk_usage.f_bavail * disk_usage.f_frsize / (1024 * 1024 * 1024)
    total_disk_space = disk_usage.f_blocks * disk_usage.f_frsize / (1024 * 1024 * 1024)
    
    # Клиенты
    total_clients = len(await client_model.get_all_clients())
    active_clients = len(await client_model.get_active_clients())
    
    text += "\n📊 Статистика:\n"
    text += f"  • Всего клиентов: {total_clients}\n"
    text += f"  • Активных клиентов: {active_clients}\n"
    text += f"  • Свободно на диске: {free_disk_space:.2f} ГБ / {total_disk_space:.2f} ГБ\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_admin_kb()
    )

def register_admin_handlers(dp):
    """Регистрирует обработчики команд администратора"""
    dp.include_router(router)
