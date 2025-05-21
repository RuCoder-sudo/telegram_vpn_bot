#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Обработчики команд настройки для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import logging
import asyncio
import subprocess
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import (
    ADMIN_IDS, BOT_VERSION, COPYRIGHT, SUPPORT_CONTACT,
    WG_CONFIG_PATH, WG_SERVER_PRIVKEY_PATH, WG_SERVER_PUBKEY_PATH
)
from keyboards.setup_kb import setup_main_kb, setup_confirm_kb, back_to_setup_kb
from database.models import SettingsModel
from utils.vpn_manager import VPNManager

logger = logging.getLogger(__name__)
router = Router()

# Создаем экземпляры моделей
settings_model = SettingsModel()
vpn_manager = VPNManager()

# Определение состояний для FSM
class SetupStates(StatesGroup):
    waiting_confirmation = State()
    waiting_server_ip = State()
    waiting_server_port = State()

# Фильтр для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Обработчик команды /setup (только для администраторов)
@router.message(Command("setup"))
async def cmd_setup(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен. Вы не являетесь администратором.")
        return
    
    await message.answer(
        f"🛠️ Настройка VPN-сервера RuCoder\n"
        f"Версия бота: {BOT_VERSION}\n\n"
        f"Внимание! Эта функция предназначена для первоначальной настройки или "
        f"восстановления работы VPN-сервера.\n\n"
        f"⚠️ Некоторые действия могут привести к временной недоступности сервера.\n\n"
        f"Выберите действие:",
        reply_markup=setup_main_kb()
    )

@router.callback_query(F.data == "setup_check_wireguard")
async def cb_check_wireguard(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer("Проверка WireGuard...")
    
    # Проверяем установлен ли WireGuard
    try:
        wg_installed = subprocess.run(['which', 'wg'], stdout=subprocess.PIPE).returncode == 0
    except Exception:
        wg_installed = False
    
    # Проверяем существование конфигурационных файлов
    config_exists = os.path.exists(WG_CONFIG_PATH)
    privkey_exists = os.path.exists(WG_SERVER_PRIVKEY_PATH)
    pubkey_exists = os.path.exists(WG_SERVER_PUBKEY_PATH)
    
    # Проверяем статус службы
    wg_service_status = vpn_manager.check_wireguard_status()
    
    # Формируем текст сообщения
    text = "🔍 Результаты проверки WireGuard:\n\n"
    
    text += f"📦 Установка WireGuard: {'✅' if wg_installed else '❌'}\n"
    text += f"📄 Конфигурация сервера: {'✅' if config_exists else '❌'}\n"
    text += f"🔑 Приватный ключ сервера: {'✅' if privkey_exists else '❌'}\n"
    text += f"🔑 Публичный ключ сервера: {'✅' if pubkey_exists else '❌'}\n"
    text += f"🚀 Статус службы: {'✅ активна' if wg_service_status['is_active'] else '❌ не активна'}\n\n"
    
    if not wg_installed or not config_exists or not privkey_exists or not pubkey_exists:
        text += "⚠️ Обнаружены проблемы с установкой WireGuard.\n"
        text += "Рекомендуется выполнить переустановку WireGuard."
    elif not wg_service_status['is_active']:
        text += "⚠️ Служба WireGuard не активна.\n"
        text += "Попробуйте перезапустить службу."
    else:
        text += "✅ WireGuard установлен и работает корректно."
    
    await callback.message.edit_text(
        text,
        reply_markup=setup_main_kb()
    )

@router.callback_query(F.data == "setup_restart_wireguard")
async def cb_restart_wireguard(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    # Проверяем подтверждение
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите перезапустить службу WireGuard?\n\n"
        "Это действие может привести к временному отключению всех VPN-соединений.",
        reply_markup=setup_confirm_kb("confirm_restart_wireguard")
    )

@router.callback_query(F.data == "confirm_restart_wireguard")
async def cb_confirm_restart_wireguard(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    
    await callback.message.edit_text("⏳ Перезапуск WireGuard...")
    
    # Выполняем перезапуск
    success = vpn_manager.restart_wireguard()
    
    # Ждем немного, чтобы служба успела запуститься
    await asyncio.sleep(3)
    
    # Проверяем статус после перезапуска
    status = vpn_manager.check_wireguard_status()
    
    if success and status['is_active']:
        await callback.message.edit_text(
            "✅ WireGuard успешно перезапущен и работает",
            reply_markup=back_to_setup_kb()
        )
    else:
        error_text = status['error'] if status['error'] else "Неизвестная ошибка"
        await callback.message.edit_text(
            f"❌ Ошибка при перезапуске WireGuard\n\n{error_text}",
            reply_markup=back_to_setup_kb()
        )

@router.callback_query(F.data == "setup_reinstall_wireguard")
async def cb_reinstall_wireguard(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(SetupStates.waiting_confirmation)
    
    await callback.message.edit_text(
        "⚠️ ВНИМАНИЕ! Вы собираетесь переустановить WireGuard.\n\n"
        "Это действие:\n"
        "- Остановит службу WireGuard\n"
        "- Удалит существующую конфигурацию\n"
        "- Создаст новые ключи и конфигурацию\n"
        "- Потребует повторной настройки всех клиентских устройств\n\n"
        "Вы уверены, что хотите продолжить?",
        reply_markup=setup_confirm_kb("confirm_reinstall_wireguard")
    )

@router.callback_query(F.data == "confirm_reinstall_wireguard")
async def cb_confirm_reinstall_wireguard(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text("⏳ Переустановка WireGuard... Это может занять некоторое время")
    
    try:
        # Останавливаем службу WireGuard
        subprocess.run(['systemctl', 'stop', 'wg-quick@wg0'], check=True)
        
        # Сохраняем копию старой конфигурации
        backup_time = datetime.now().strftime("%Y%m%d%H%M%S")
        if os.path.exists(WG_CONFIG_PATH):
            os.rename(WG_CONFIG_PATH, f"{WG_CONFIG_PATH}.backup-{backup_time}")
        
        # Генерируем новые ключи
        subprocess.run(
            ['wg', 'genkey'], 
            stdout=open(WG_SERVER_PRIVKEY_PATH, 'w'),
            check=True
        )
        
        subprocess.run(
            ['wg', 'pubkey'], 
            stdin=open(WG_SERVER_PRIVKEY_PATH, 'r'),
            stdout=open(WG_SERVER_PUBKEY_PATH, 'w'),
            check=True
        )
        
        # Создаем новую конфигурацию
        with open(WG_SERVER_PRIVKEY_PATH, 'r') as f:
            server_private_key = f.read().strip()
        
        with open(WG_CONFIG_PATH, 'w') as f:
            f.write(f'''[Interface]
PrivateKey = {server_private_key}
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = false
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o $(ip route | grep default | awk '{{print $5}}') -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o $(ip route | grep default | awk '{{print $5}}') -j MASQUERADE

# Клиенты будут добавлены здесь
''')
        
        # Настраиваем IP-форвардинг
        with open('/etc/sysctl.d/99-wireguard.conf', 'w') as f:
            f.write('net.ipv4.ip_forward = 1\n')
        
        subprocess.run(['sysctl', '-p', '/etc/sysctl.d/99-wireguard.conf'], check=True)
        
        # Запускаем службу WireGuard
        subprocess.run(['systemctl', 'enable', 'wg-quick@wg0'], check=True)
        subprocess.run(['systemctl', 'start', 'wg-quick@wg0'], check=True)
        
        # Ждем немного и проверяем статус
        await asyncio.sleep(3)
        status = vpn_manager.check_wireguard_status()
        
        if status['is_active']:
            await callback.message.edit_text(
                "✅ WireGuard успешно переустановлен и запущен!\n\n"
                "⚠️ ВНИМАНИЕ! Все существующие клиентские конфигурации больше не действительны.\n"
                "Необходимо создать новые конфигурации для всех клиентов.",
                reply_markup=back_to_setup_kb()
            )
        else:
            await callback.message.edit_text(
                f"⚠️ WireGuard переустановлен, но не запущен.\n\n"
                f"Ошибка: {status['error'] if status['error'] else 'Неизвестная ошибка'}\n\n"
                f"Попробуйте перезапустить службу вручную или обратитесь к документации.",
                reply_markup=back_to_setup_kb()
            )
    except Exception as e:
        logger.error(f"Ошибка при переустановке WireGuard: {e}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при переустановке WireGuard:\n\n{str(e)}",
            reply_markup=back_to_setup_kb()
        )

@router.callback_query(F.data == "setup_update_server_info")
async def cb_update_server_info(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(SetupStates.waiting_server_ip)
    
    await callback.message.edit_text(
        "🌐 Обновление информации о сервере\n\n"
        "Введите IP-адрес сервера (или оставьте пустым для автоматического определения):",
        reply_markup=back_to_setup_kb()
    )

@router.message(SetupStates.waiting_server_ip)
async def process_server_ip(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен")
        await state.clear()
        return
    
    server_ip = message.text.strip()
    
    # Если IP не указан, пытаемся определить его автоматически
    if not server_ip:
        try:
            import requests
            server_ip = requests.get('https://api.ipify.org').text
        except Exception as e:
            logger.error(f"Ошибка при определении IP-адреса: {e}")
            await message.answer(
                "❌ Не удалось автоматически определить IP-адрес сервера.\n"
                "Пожалуйста, введите IP-адрес вручную:",
                reply_markup=back_to_setup_kb()
            )
            return
    
    # Проверяем формат IP
    import re
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', server_ip):
        await message.answer(
            "❌ Неверный формат IP-адреса.\n"
            "Пожалуйста, введите корректный IPv4 адрес (например, 192.168.1.1):",
            reply_markup=back_to_setup_kb()
        )
        return
    
    # Сохраняем IP в состоянии
    await state.update_data(server_ip=server_ip)
    await state.set_state(SetupStates.waiting_server_port)
    
    await message.answer(
        f"🔢 Введите порт WireGuard (или оставьте пустым для использования порта по умолчанию: 51820):"
    )

@router.message(SetupStates.waiting_server_port)
async def process_server_port(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен")
        await state.clear()
        return
    
    port_text = message.text.strip()
    
    # Если порт не указан, используем порт по умолчанию
    if not port_text:
        server_port = 51820
    else:
        try:
            server_port = int(port_text)
            if server_port < 1 or server_port > 65535:
                raise ValueError("Порт должен быть в диапазоне от 1 до 65535")
        except ValueError as e:
            await message.answer(
                f"❌ Ошибка: {str(e)}.\n"
                f"Пожалуйста, введите корректный порт (от 1 до 65535):",
                reply_markup=back_to_setup_kb()
            )
            return
    
    # Получаем IP из состояния
    data = await state.get_data()
    server_ip = data.get('server_ip')
    
    # Обновляем настройки
    await settings_model.update_setting('SERVER_IP', server_ip)
    await settings_model.update_setting('SERVER_PORT', str(server_port))
    
    # Обновляем переменные окружения
    with open('.env', 'r') as f:
        env_content = f.readlines()
    
    new_env_content = []
    ip_updated = False
    port_updated = False
    
    for line in env_content:
        if line.startswith('SERVER_IP='):
            new_env_content.append(f'SERVER_IP={server_ip}\n')
            ip_updated = True
        elif line.startswith('SERVER_PORT='):
            new_env_content.append(f'SERVER_PORT={server_port}\n')
            port_updated = True
        else:
            new_env_content.append(line)
    
    if not ip_updated:
        new_env_content.append(f'SERVER_IP={server_ip}\n')
    
    if not port_updated:
        new_env_content.append(f'SERVER_PORT={server_port}\n')
    
    with open('.env', 'w') as f:
        f.writelines(new_env_content)
    
    await state.clear()
    
    await message.answer(
        f"✅ Информация о сервере обновлена:\n\n"
        f"IP-адрес: {server_ip}\n"
        f"Порт: {server_port}\n\n"
        f"⚠️ Внимание! Все существующие клиентские конфигурации нужно обновить с новыми данными.",
        reply_markup=setup_main_kb()
    )

@router.callback_query(F.data == "setup_back")
async def cb_setup_back(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        f"🛠️ Настройка VPN-сервера RuCoder\n"
        f"Версия бота: {BOT_VERSION}\n\n"
        f"Выберите действие:",
        reply_markup=setup_main_kb()
    )

@router.callback_query(F.data == "setup_exit")
async def cb_setup_exit(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен", show_alert=True)
        return
    
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        f"👋 Главное меню RuCoder VPN\n\n"
        f"Вы вышли из режима настройки. Чтобы вернуться в панель администратора, "
        f"используйте команду /admin",
        reply_markup=None
    )

def register_setup_handlers(dp):
    """Регистрирует обработчики команд настройки"""
    dp.include_router(router)
