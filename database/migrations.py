#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Система миграций для базы данных VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import sqlite3
import logging
import importlib.util
import sys
import re
from datetime import datetime
from config import DB_PATH, MIGRATIONS_TABLE, MIGRATIONS_DIRECTORY

logger = logging.getLogger(__name__)

async def run_migrations():
    """Запускает все доступные миграции базы данных"""
    try:
        # Создаем директорию для миграций, если её нет
        os.makedirs(MIGRATIONS_DIRECTORY, exist_ok=True)
        
        # Подключаемся к базе данных
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем существование таблицы миграций
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{MIGRATIONS_TABLE}'")
        if not cursor.fetchone():
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )
            ''')
            conn.commit()
        
        # Получаем список уже применённых миграций
        cursor.execute(f"SELECT version FROM {MIGRATIONS_TABLE}")
        applied_migrations = {row[0] for row in cursor.fetchall()}
        
        # Получаем список всех файлов миграций
        migration_files = []
        if os.path.exists(MIGRATIONS_DIRECTORY):
            for filename in os.listdir(MIGRATIONS_DIRECTORY):
                if filename.endswith('.py') and re.match(r'^m\d{14}_', filename):
                    version = filename[1:-3]  # Убираем 'm' в начале и '.py' в конце
                    migration_files.append((version, os.path.join(MIGRATIONS_DIRECTORY, filename)))
        
        # Сортируем миграции по версии
        migration_files.sort(key=lambda x: x[0])
        
        # Фильтруем только новые миграции
        new_migrations = [(version, path) for version, path in migration_files if version not in applied_migrations]
        
        if not new_migrations:
            logger.info("Нет новых миграций для применения")
            return
        
        logger.info(f"Найдено {len(new_migrations)} новых миграций для применения")
        
        # Применяем новые миграции
        for version, path in new_migrations:
            try:
                # Загружаем модуль миграции
                spec = importlib.util.spec_from_file_location(f"migration_{version}", path)
                migration_module = importlib.util.module_from_spec(spec)
                sys.modules[f"migration_{version}"] = migration_module
                spec.loader.exec_module(migration_module)
                
                # Выполняем миграцию
                logger.info(f"Применение миграции {version}...")
                await migration_module.migrate(conn, cursor)
                
                # Записываем информацию о применённой миграции
                cursor.execute(
                    f"INSERT INTO {MIGRATIONS_TABLE} (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                
                logger.info(f"Миграция {version} успешно применена")
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка при применении миграции {version}: {e}")
                raise e
        
        conn.close()
        logger.info("Все миграции успешно применены")
    except Exception as e:
        logger.error(f"Ошибка при запуске миграций: {e}")
        raise e

async def create_migration(name):
    """Создаёт новый файл миграции"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"m{timestamp}_{name}.py"
    filepath = os.path.join(MIGRATIONS_DIRECTORY, filename)
    
    # Создаем директорию для миграций, если её нет
    os.makedirs(MIGRATIONS_DIRECTORY, exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Миграция: {name}
Создана: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

async def migrate(conn, cursor):
    """
    Применяет миграцию к базе данных
    
    Args:
        conn: Соединение с базой данных
        cursor: Курсор базы данных
    """
    # Начало транзакции
    try:
        # Здесь код миграции
        # Пример: cursor.execute("ALTER TABLE table_name ADD COLUMN column_name TEXT")
        
        # Подтверждение транзакции
        conn.commit()
    except Exception as e:
        # Откат транзакции в случае ошибки
        conn.rollback()
        logger.error(f"Ошибка миграции: {e}")
        raise e
''')
    
    logger.info(f"Создан файл миграции: {filepath}")
    return filepath
