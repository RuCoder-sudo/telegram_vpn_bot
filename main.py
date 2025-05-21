#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RUCODER VPN Bot - Главный файл запуска бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Добавление родительского каталога в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN, logger, ADMIN_IDS
from handlers.admin_handlers import register_admin_handlers
from handlers.user_handlers import register_user_handlers
from handlers.setup_handlers import register_setup_handlers
from database.migrations import run_migrations
from utils.server_monitor import start_monitoring
from init_db import init_db

async def on_startup(bot):
    """Действия при запуске бота"""
    # Инициализация базы данных, если она не существует
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vpn_bot.db')):
        logger.info("База данных не найдена. Инициализация...")
        init_db()
    
    # Запуск миграций
    await run_migrations()
    
    # Оповещение администраторов о запуске бота
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, 
                f"✅ Бот RuCoder VPN запущен!\n"
                f"Версия: {config.BOT_VERSION}\n"
                f"Время запуска: {config.SYSTEM_INFO['start_time']}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")
    
    # Запуск мониторинга сервера в отдельном потоке
    asyncio.create_task(start_monitoring(bot))
    
    logger.info("Бот успешно запущен и готов к работе!")

async def on_shutdown(bot):
    """Действия при остановке бота"""
    logger.info("Остановка бота...")
    
    # Оповещение администраторов об остановке бота
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "⚠️ Бот RuCoder VPN остановлен!")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {admin_id}: {e}")

async def main():
    """Основная функция запуска бота"""
    # Проверка наличия токена
    if not BOT_TOKEN:
        logger.error("Токен бота не найден! Убедитесь, что файл .env существует и содержит BOT_TOKEN.")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация обработчиков
    register_user_handlers(dp)
    register_admin_handlers(dp)
    register_setup_handlers(dp)
    
    # Регистрация хуков запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск бота
    try:
        logger.info("Запуск VPN бота")
        
        # Пропуск необработанных обновлений
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запуск опроса обновлений
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        import config  # Импорт в основной функции для избежания циклических импортов
        # Запуск основной функции в асинхронном режиме
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот был остановлен вручную")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
