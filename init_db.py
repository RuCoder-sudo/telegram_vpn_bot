#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт инициализации базы данных для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import logging
import sqlite3
from datetime import datetime
from config import DB_PATH, CLIENTS_DIR, BASE_DIR, BOT_VERSION, MIGRATIONS_TABLE

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='init_db.log'
)

logger = logging.getLogger(__name__)

def init_db():
    """Инициализация базы данных"""
    try:
        # Создаем директории, если они не существуют
        os.makedirs(CLIENTS_DIR, exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)
        
        # Подключаемся к базе данных (будет создана, если не существует)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Создаем таблицу клиентов с улучшенной структурой
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                user_id INTEGER,
                email TEXT,
                create_date TEXT NOT NULL,
                expiry_date TEXT,
                last_connection TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                is_blocked BOOLEAN NOT NULL DEFAULT 0,
                allowed_ips TEXT DEFAULT '0.0.0.0/0',
                public_key TEXT,
                private_key TEXT,
                data_limit INTEGER DEFAULT 0,
                data_used INTEGER DEFAULT 0
            )
        ''')
        
        # Создаем индексы для ускорения запросов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_is_active ON clients(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_is_blocked ON clients(is_blocked)')
        
        # Создаем таблицу статистики с улучшенной структурой
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                connection_date TEXT NOT NULL,
                disconnection_date TEXT,
                session_duration INTEGER DEFAULT 0,
                ip_address TEXT,
                bytes_received INTEGER DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        # Создаем индекс для ускорения запросов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_client_id ON stats(client_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stats_connection_date ON stats(connection_date)')
        
        # Создаем таблицу для хранения настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                value TEXT,
                description TEXT,
                updated_at TEXT
            )
        ''')
        
        # Создаем таблицу для хранения информации о миграциях
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            )
        ''')
        
        # Создаем таблицу для системных уведомлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read BOOLEAN NOT NULL DEFAULT 0,
                importance TEXT DEFAULT 'normal'
            )
        ''')
        
        # Создаем таблицу для обратной связи от пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                processed BOOLEAN NOT NULL DEFAULT 0,
                admin_response TEXT
            )
        ''')
        
        # Создаем таблицу для метрик сервера
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                network_in INTEGER,
                network_out INTEGER,
                active_connections INTEGER
            )
        ''')
        
        # Фиксируем изменения
        conn.commit()
        
        # Добавляем базовые настройки, если их нет
        settings = [
            ("bot_version", BOT_VERSION, "Текущая версия бота", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("bot_author", "RUCODER", "Автор бота", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("website_url", "https://рукодер.рф/vpn", "Веб-сайт проекта", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("max_clients", "50", "Максимальное количество клиентов", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("default_client_expiry", "30", "Срок действия клиента по умолчанию (дни)", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("metrics_retention", "30", "Срок хранения метрик (дни)", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("monitoring_interval", "5", "Интервал мониторинга (минуты)", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ]
        
        cursor.execute('SELECT name FROM settings')
        existing_settings = {row[0] for row in cursor.fetchall()}
        
        for setting in settings:
            if setting[0] not in existing_settings:
                cursor.execute(
                    'INSERT INTO settings (name, value, description, updated_at) VALUES (?, ?, ?, ?)', 
                    setting
                )
        
        conn.commit()
        conn.close()
        
        logger.info("База данных инициализирована успешно")
        print("✅ База данных инициализирована успешно")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False

if __name__ == "__main__":
    init_db()
