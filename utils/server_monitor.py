#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль мониторинга сервера для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import asyncio
import logging
import psutil
import subprocess
import os
import time
from datetime import datetime
import aiohttp

from config import (
    CPU_THRESHOLD,
    MEMORY_THRESHOLD,
    DISK_THRESHOLD,
    ADMIN_IDS
)
from database.models import ServerMetricsModel, NotificationModel

logger = logging.getLogger(__name__)

class ServerMonitor:
    def __init__(self, bot=None):
        self.bot = bot
        self.metrics_model = ServerMetricsModel()
        self.notification_model = NotificationModel()
        self.previous_network_io = psutil.net_io_counters()
        self.previous_time = time.time()
        self.monitoring_interval = 300  # 5 минут по умолчанию
    
    async def get_system_metrics(self):
        """Получает текущие метрики системы"""
        try:
            # CPU использование
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Использование памяти
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Использование диска
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Сетевой трафик (разница с предыдущим измерением)
            current_network_io = psutil.net_io_counters()
            current_time = time.time()
            
            time_diff = current_time - self.previous_time
            
            network_in = (current_network_io.bytes_recv - self.previous_network_io.bytes_recv) / time_diff
            network_out = (current_network_io.bytes_sent - self.previous_network_io.bytes_sent) / time_diff
            
            self.previous_network_io = current_network_io
            self.previous_time = current_time
            
            # Активные подключения WireGuard
            active_connections = 0
            try:
                wg_show = subprocess.run(
                    ['wg', 'show'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Считаем количество строк "peer:"
                active_connections = wg_show.stdout.count('peer:')
            except subprocess.CalledProcessError:
                logger.warning("Не удалось получить информацию о подключениях WireGuard")
            except Exception as e:
                logger.error(f"Ошибка при получении активных подключений: {e}")
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'network_in': network_in,
                'network_out': network_out,
                'active_connections': active_connections
            }
        except Exception as e:
            logger.error(f"Ошибка при получении метрик системы: {e}")
            return None
    
    async def check_thresholds(self, metrics):
        """Проверяет превышение пороговых значений метрик"""
        warnings = []
        
        if metrics['cpu_usage'] > CPU_THRESHOLD:
            warnings.append(f"⚠️ Высокая загрузка CPU: {metrics['cpu_usage']}% (порог: {CPU_THRESHOLD}%)")
        
        if metrics['memory_usage'] > MEMORY_THRESHOLD:
            warnings.append(f"⚠️ Высокое использование памяти: {metrics['memory_usage']}% (порог: {MEMORY_THRESHOLD}%)")
        
        if metrics['disk_usage'] > DISK_THRESHOLD:
            warnings.append(f"⚠️ Высокое использование диска: {metrics['disk_usage']}% (порог: {DISK_THRESHOLD}%)")
        
        return warnings
    
    async def send_alerts(self, warnings):
        """Отправляет предупреждения администраторам"""
        if not warnings:
            return
        
        # Формируем сообщение с предупреждениями
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"🚨 ПРЕДУПРЕЖДЕНИЕ О СОСТОЯНИИ СЕРВЕРА ({current_time}):\n\n"
        message += "\n".join(warnings)
        
        # Создаем уведомление в базе данных
        await self.notification_model.create_notification(
            'server_alert',
            message,
            'high'
        )
        
        # Отправляем сообщение всем администраторам
        if self.bot:
            for admin_id in ADMIN_IDS:
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Не удалось отправить предупреждение администратору {admin_id}: {e}")
    
    async def log_metrics_to_db(self, metrics):
        """Логирует метрики в базу данных"""
        try:
            await self.metrics_model.log_metrics(
                metrics['cpu_usage'],
                metrics['memory_usage'],
                metrics['disk_usage'],
                metrics['network_in'],
                metrics['network_out'],
                metrics['active_connections']
            )
        except Exception as e:
            logger.error(f"Ошибка при записи метрик в базу данных: {e}")
    
    async def cleanup_old_metrics(self):
        """Удаляет старые метрики из базы данных"""
        try:
            await self.metrics_model.delete_old_metrics()
        except Exception as e:
            logger.error(f"Ошибка при удалении старых метрик: {e}")
    
    async def monitor_once(self):
        """Выполняет одну итерацию мониторинга"""
        try:
            # Получаем текущие метрики
            metrics = await self.get_system_metrics()
            if not metrics:
                logger.error("Не удалось получить метрики системы")
                return
            
            # Проверяем пороговые значения
            warnings = await self.check_thresholds(metrics)
            
            # Отправляем предупреждения при необходимости
            if warnings:
                await self.send_alerts(warnings)
            
            # Логируем метрики в базу данных
            await self.log_metrics_to_db(metrics)
        except Exception as e:
            logger.error(f"Ошибка при выполнении мониторинга: {e}")
    
    async def start_monitoring_loop(self):
        """Запускает цикл мониторинга"""
        logger.info("Запуск цикла мониторинга сервера")
        
        # Выполняем начальную инициализацию сетевых метрик
        self.previous_network_io = psutil.net_io_counters()
        self.previous_time = time.time()
        
        try:
            while True:
                await self.monitor_once()
                
                # Очищаем старые метрики раз в сутки
                if datetime.now().hour == 2 and datetime.now().minute < 5:
                    await self.cleanup_old_metrics()
                
                # Ждем указанный интервал перед следующей проверкой
                await asyncio.sleep(self.monitoring_interval)
        except asyncio.CancelledError:
            logger.info("Цикл мониторинга сервера остановлен")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в цикле мониторинга: {e}")

async def start_monitoring(bot=None):
    """Запускает мониторинг сервера"""
    monitor = ServerMonitor(bot)
    await monitor.start_monitoring_loop()
