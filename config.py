#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VPN Telegram Bot
Автор: RUCODER
Веб-сайт: https://рукодер.рф/vpn
"""

import os
import logging
import platform
import psutil
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, 'vpn_bot.log')

# Создание каталога для логов, если он не существует
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Токен бота и ID администраторов
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Настройки сервера
SERVER_IP = os.getenv('SERVER_IP', '90.156.255.117')
SERVER_PORT = int(os.getenv('SERVER_PORT', '51820'))
DNS_SERVERS = os.getenv('DNS_SERVERS', '8.8.8.8, 8.8.4.4')

# Пути к файлам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'vpn_bot.db')
CLIENTS_DIR = os.path.join(BASE_DIR, 'clients')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Настройки Wireguard
WG_CONFIG_PATH = '/etc/wireguard/wg0.conf'
WG_SERVER_PRIVKEY_PATH = '/etc/wireguard/server_private.key'
WG_SERVER_PUBKEY_PATH = '/etc/wireguard/server_public.key'

# Настройки сайта и поддержки
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://рукодер.рф/vpn')
SUPPORT_CONTACT = '@RussCoder'

# Информация о боте
BOT_VERSION = '1.1.0'
BOT_AUTHOR = 'RUCODER'
COPYRIGHT = '© 2025 RUCODER. Все права защищены.'

# Параметры мониторинга
CPU_THRESHOLD = 80  # Процент использования CPU для оповещения
MEMORY_THRESHOLD = 80  # Процент использования памяти для оповещения
DISK_THRESHOLD = 90  # Процент использования диска для оповещения

# Информация о системе
SYSTEM_INFO = {
    "os": platform.system(),
    "os_version": platform.version(),
    "cpu_cores": psutil.cpu_count(),
    "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# Настройка для системы миграций
MIGRATIONS_TABLE = 'migrations'
MIGRATIONS_DIRECTORY = os.path.join(BASE_DIR, 'database/migrations')
