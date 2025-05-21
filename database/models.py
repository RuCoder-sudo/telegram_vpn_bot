#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модели базы данных для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import os
from config import DB_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    
    def get_connection(self):
        """Получает соединение с базой данных"""
        return sqlite3.connect(self.db_path)
    
    async def execute(self, query, params=None):
        """Выполняет запрос к базе данных"""
        params = params or ()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}\nЗапрос: {query}\nПараметры: {params}")
            raise e
        finally:
            if conn:
                conn.close()
    
    async def fetch_all(self, query, params=None):
        """Выполняет запрос и возвращает все результаты"""
        params = params or ()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}\nЗапрос: {query}\nПараметры: {params}")
            raise e
        finally:
            if conn:
                conn.close()
    
    async def fetch_one(self, query, params=None):
        """Выполняет запрос и возвращает один результат"""
        params = params or ()
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}\nЗапрос: {query}\nПараметры: {params}")
            raise e
        finally:
            if conn:
                conn.close()

class ClientModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def get_all_clients(self):
        """Получает список всех клиентов"""
        query = "SELECT * FROM clients ORDER BY create_date DESC"
        return await self.db.fetch_all(query)
    
    async def get_active_clients(self):
        """Получает список активных клиентов"""
        query = "SELECT * FROM clients WHERE is_active = 1 AND is_blocked = 0 ORDER BY create_date DESC"
        return await self.db.fetch_all(query)
    
    async def get_client_by_id(self, client_id):
        """Получает клиента по ID"""
        query = "SELECT * FROM clients WHERE id = ?"
        return await self.db.fetch_one(query, (client_id,))
    
    async def get_client_by_name(self, name):
        """Получает клиента по имени"""
        query = "SELECT * FROM clients WHERE name = ?"
        return await self.db.fetch_one(query, (name,))
    
    async def get_client_by_user_id(self, user_id):
        """Получает клиента по ID пользователя Telegram"""
        query = "SELECT * FROM clients WHERE user_id = ?"
        return await self.db.fetch_one(query, (user_id,))
    
    async def create_client(self, name, user_id=None, email=None, expiry_days=30, 
                            public_key=None, private_key=None):
        """Создает нового клиента"""
        create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S") if expiry_days else None
        
        query = """
            INSERT INTO clients 
            (name, user_id, email, create_date, expiry_date, is_active, public_key, private_key) 
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """
        await self.db.execute(query, (name, user_id, email, create_date, expiry_date, public_key, private_key))
        
        # Получаем созданного клиента
        return await self.get_client_by_name(name)
    
    async def update_client(self, client_id, **kwargs):
        """Обновляет данные клиента"""
        # Формируем части запроса
        set_parts = []
        params = []
        
        for key, value in kwargs.items():
            set_parts.append(f"{key} = ?")
            params.append(value)
        
        if not set_parts:
            return await self.get_client_by_id(client_id)
        
        # Добавляем ID в параметры
        params.append(client_id)
        
        query = f"UPDATE clients SET {', '.join(set_parts)} WHERE id = ?"
        await self.db.execute(query, params)
        
        return await self.get_client_by_id(client_id)
    
    async def delete_client(self, client_id):
        """Удаляет клиента"""
        query = "DELETE FROM clients WHERE id = ?"
        await self.db.execute(query, (client_id,))
    
    async def activate_client(self, client_id):
        """Активирует клиента"""
        return await self.update_client(client_id, is_active=1)
    
    async def deactivate_client(self, client_id):
        """Деактивирует клиента"""
        return await self.update_client(client_id, is_active=0)
    
    async def block_client(self, client_id):
        """Блокирует клиента"""
        return await self.update_client(client_id, is_blocked=1)
    
    async def unblock_client(self, client_id):
        """Разблокирует клиента"""
        return await self.update_client(client_id, is_blocked=0)
    
    async def update_client_usage(self, client_id, bytes_received, bytes_sent):
        """Обновляет использование трафика клиентом"""
        client = await self.get_client_by_id(client_id)
        if not client:
            return None
        
        current_usage = client[13] or 0  # data_used колонка
        new_usage = current_usage + bytes_received + bytes_sent
        
        return await self.update_client(client_id, data_used=new_usage, last_connection=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    async def check_expired_clients(self):
        """Проверяет и деактивирует просроченные аккаунты клиентов"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = f"""
            UPDATE clients 
            SET is_active = 0 
            WHERE expiry_date IS NOT NULL 
            AND expiry_date < '{now}' 
            AND is_active = 1
        """
        await self.db.execute(query)
        
        # Возвращаем список деактивированных клиентов
        query = f"""
            SELECT * FROM clients 
            WHERE expiry_date IS NOT NULL 
            AND expiry_date < '{now}' 
            AND is_active = 0
        """
        return await self.db.fetch_all(query)

class StatsModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def log_connection(self, client_id, ip_address):
        """Логирует подключение клиента"""
        connection_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO stats 
            (client_id, connection_date, ip_address, bytes_received, bytes_sent) 
            VALUES (?, ?, ?, 0, 0)
        """
        await self.db.execute(query, (client_id, connection_date, ip_address))
        
        # Получаем ID созданной записи
        query = "SELECT last_insert_rowid()"
        result = await self.db.fetch_one(query)
        return result[0] if result else None
    
    async def log_disconnection(self, stats_id, bytes_received, bytes_sent):
        """Логирует отключение клиента"""
        disconnection_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Получаем текущую запись
        query = "SELECT connection_date FROM stats WHERE id = ?"
        stats = await self.db.fetch_one(query, (stats_id,))
        
        if not stats:
            return None
        
        # Вычисляем продолжительность сессии
        connection_date = datetime.strptime(stats[0], "%Y-%m-%d %H:%M:%S")
        disconnection_date_obj = datetime.now()
        session_duration = int((disconnection_date_obj - connection_date).total_seconds())
        
        # Обновляем запись
        query = """
            UPDATE stats 
            SET disconnection_date = ?, bytes_received = ?, bytes_sent = ?, session_duration = ? 
            WHERE id = ?
        """
        await self.db.execute(query, (disconnection_date, bytes_received, bytes_sent, session_duration, stats_id))
        
        return stats_id
    
    async def get_client_stats(self, client_id, limit=10):
        """Получает статистику клиента"""
        query = """
            SELECT * FROM stats 
            WHERE client_id = ? 
            ORDER BY connection_date DESC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (client_id, limit))
    
    async def get_client_usage_total(self, client_id):
        """Получает общее использование трафика клиентом"""
        query = """
            SELECT SUM(bytes_received) as total_received, SUM(bytes_sent) as total_sent 
            FROM stats 
            WHERE client_id = ?
        """
        result = await self.db.fetch_one(query, (client_id,))
        return result or (0, 0)
    
    async def get_client_usage_by_period(self, client_id, start_date, end_date):
        """Получает использование трафика клиентом за период"""
        query = """
            SELECT SUM(bytes_received) as total_received, SUM(bytes_sent) as total_sent 
            FROM stats 
            WHERE client_id = ? AND connection_date BETWEEN ? AND ?
        """
        result = await self.db.fetch_one(query, (client_id, start_date, end_date))
        return result or (0, 0)
    
    async def get_overall_stats(self):
        """Получает общую статистику использования"""
        # Общее количество подключений
        query1 = "SELECT COUNT(*) FROM stats"
        connections_count = await self.db.fetch_one(query1)
        
        # Общий трафик
        query2 = "SELECT SUM(bytes_received), SUM(bytes_sent) FROM stats"
        traffic = await self.db.fetch_one(query2)
        
        # Активные сессии (без даты отключения)
        query3 = "SELECT COUNT(*) FROM stats WHERE disconnection_date IS NULL"
        active_sessions = await self.db.fetch_one(query3)
        
        # Статистика по дням за последний месяц
        query4 = """
            SELECT 
                date(connection_date) as day, 
                COUNT(*) as connections, 
                SUM(bytes_received) as received, 
                SUM(bytes_sent) as sent 
            FROM stats 
            WHERE connection_date >= date('now', '-30 days') 
            GROUP BY day 
            ORDER BY day
        """
        daily_stats = await self.db.fetch_all(query4)
        
        return {
            "connections_count": connections_count[0] if connections_count else 0,
            "total_received": traffic[0] if traffic and traffic[0] else 0,
            "total_sent": traffic[1] if traffic and traffic[1] else 0,
            "active_sessions": active_sessions[0] if active_sessions else 0,
            "daily_stats": daily_stats
        }

class SettingsModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def get_setting(self, name):
        """Получает значение настройки по имени"""
        query = "SELECT value FROM settings WHERE name = ?"
        result = await self.db.fetch_one(query, (name,))
        return result[0] if result else None
    
    async def get_all_settings(self):
        """Получает все настройки"""
        query = "SELECT name, value, description, updated_at FROM settings ORDER BY name"
        return await self.db.fetch_all(query)
    
    async def update_setting(self, name, value):
        """Обновляет значение настройки"""
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "UPDATE settings SET value = ?, updated_at = ? WHERE name = ?"
        await self.db.execute(query, (value, updated_at, name))
        
        return await self.get_setting(name)
    
    async def create_setting(self, name, value, description=""):
        """Создает новую настройку"""
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO settings (name, value, description, updated_at) 
            VALUES (?, ?, ?, ?)
        """
        await self.db.execute(query, (name, value, description, updated_at))
        
        return await self.get_setting(name)

class NotificationModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def create_notification(self, notification_type, message, importance="normal"):
        """Создает новое уведомление"""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO notifications (type, message, created_at, read, importance) 
            VALUES (?, ?, ?, 0, ?)
        """
        await self.db.execute(query, (notification_type, message, created_at, importance))
        
        # Получаем ID созданного уведомления
        query = "SELECT last_insert_rowid()"
        result = await self.db.fetch_one(query)
        return result[0] if result else None
    
    async def get_unread_notifications(self, limit=10):
        """Получает непрочитанные уведомления"""
        query = """
            SELECT * FROM notifications 
            WHERE read = 0 
            ORDER BY 
                CASE importance 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'normal' THEN 3 
                    WHEN 'low' THEN 4 
                    ELSE 5 
                END, 
                created_at DESC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))
    
    async def get_all_notifications(self, limit=50):
        """Получает все уведомления"""
        query = """
            SELECT * FROM notifications 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))
    
    async def mark_as_read(self, notification_id):
        """Отмечает уведомление как прочитанное"""
        query = "UPDATE notifications SET read = 1 WHERE id = ?"
        await self.db.execute(query, (notification_id,))
    
    async def mark_all_as_read(self):
        """Отмечает все уведомления как прочитанные"""
        query = "UPDATE notifications SET read = 1 WHERE read = 0"
        await self.db.execute(query)
    
    async def delete_notification(self, notification_id):
        """Удаляет уведомление"""
        query = "DELETE FROM notifications WHERE id = ?"
        await self.db.execute(query, (notification_id,))
    
    async def delete_old_notifications(self, days=30):
        """Удаляет старые уведомления"""
        query = f"DELETE FROM notifications WHERE created_at < datetime('now', '-{days} days')"
        await self.db.execute(query)

class FeedbackModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def create_feedback(self, user_id, message):
        """Создает новую обратную связь"""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO feedback (user_id, message, created_at, processed) 
            VALUES (?, ?, ?, 0)
        """
        await self.db.execute(query, (user_id, message, created_at))
        
        # Получаем ID созданной обратной связи
        query = "SELECT last_insert_rowid()"
        result = await self.db.fetch_one(query)
        return result[0] if result else None
    
    async def get_unprocessed_feedback(self, limit=10):
        """Получает необработанную обратную связь"""
        query = """
            SELECT * FROM feedback 
            WHERE processed = 0 
            ORDER BY created_at ASC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))
    
    async def get_all_feedback(self, limit=50):
        """Получает всю обратную связь"""
        query = """
            SELECT * FROM feedback 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))
    
    async def respond_to_feedback(self, feedback_id, admin_response):
        """Отвечает на обратную связь"""
        query = """
            UPDATE feedback 
            SET processed = 1, admin_response = ? 
            WHERE id = ?
        """
        await self.db.execute(query, (admin_response, feedback_id))
    
    async def get_feedback_by_id(self, feedback_id):
        """Получает обратную связь по ID"""
        query = "SELECT * FROM feedback WHERE id = ?"
        return await self.db.fetch_one(query, (feedback_id,))

class ServerMetricsModel:
    def __init__(self, db=None):
        self.db = db or Database()
    
    async def log_metrics(self, cpu_usage, memory_usage, disk_usage, network_in, network_out, active_connections):
        """Логирует метрики сервера"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO server_metrics 
            (timestamp, cpu_usage, memory_usage, disk_usage, network_in, network_out, active_connections) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(query, (timestamp, cpu_usage, memory_usage, disk_usage, 
                                      network_in, network_out, active_connections))
    
    async def get_latest_metrics(self, limit=1):
        """Получает последние метрики сервера"""
        query = """
            SELECT * FROM server_metrics 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        return await self.db.fetch_all(query, (limit,))
    
    async def get_metrics_by_period(self, start_date, end_date, interval='hour'):
        """Получает метрики за период с группировкой по интервалу"""
        interval_format = {
            'hour': '%Y-%m-%d %H:00:00',
            'day': '%Y-%m-%d 00:00:00',
            'week': '%Y-%W',  # ISO неделя года
            'month': '%Y-%m-01'
        }.get(interval, '%Y-%m-%d %H:00:00')
        
        groupby = f"strftime('{interval_format}', timestamp)"
        
        query = f"""
            SELECT 
                {groupby} as period,
                AVG(cpu_usage) as avg_cpu,
                AVG(memory_usage) as avg_memory,
                AVG(disk_usage) as avg_disk,
                SUM(network_in) as total_net_in,
                SUM(network_out) as total_net_out,
                AVG(active_connections) as avg_connections
            FROM server_metrics 
            WHERE timestamp BETWEEN ? AND ?
            GROUP BY period
            ORDER BY period
        """
        return await self.db.fetch_all(query, (start_date, end_date))
    
    async def delete_old_metrics(self, days=30):
        """Удаляет старые метрики"""
        query = f"DELETE FROM server_metrics WHERE timestamp < datetime('now', '-{days} days')"
        await self.db.execute(query)
    
    async def get_critical_events(self, cpu_threshold=80, memory_threshold=80, disk_threshold=90):
        """Получает события с превышением пороговых значений"""
        query = f"""
            SELECT * FROM server_metrics 
            WHERE 
                cpu_usage > {cpu_threshold} OR 
                memory_usage > {memory_threshold} OR 
                disk_usage > {disk_threshold}
            ORDER BY timestamp DESC
            LIMIT 50
        """
        return await self.db.fetch_all(query)
