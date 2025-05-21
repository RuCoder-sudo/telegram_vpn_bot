#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль тестирования скорости соединения для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import asyncio
import time
import aiohttp
import logging
from statistics import mean
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Список серверов для тестирования скорости загрузки
SPEED_TEST_SERVERS = [
    "https://speed.cloudflare.com/__down?bytes=10000000",  # 10MB файл от Cloudflare
    "https://speedtest.selectel.ru/10MB.bin",  # 10MB файл от Selectel
    "https://fra1.digitaloceanspaces.com/speedtest/10mb.bin"  # 10MB файл от DigitalOcean
]

# Список серверов для проверки пинга
PING_SERVERS = [
    "https://www.google.com",
    "https://yandex.ru",
    "https://cloudflare.com",
    "https://vk.com"
]

class SpeedTester:
    """Класс для тестирования скорости соединения"""
    
    def __init__(self):
        """Инициализация тестера скорости"""
        self.last_results = {}
    
    async def measure_ping(self, url: str, count: int = 3) -> Tuple[float, float]:
        """
        Измеряет пинг до указанного сервера
        
        Args:
            url: URL сервера для проверки пинга
            count: Количество запросов для усреднения
            
        Returns:
            Кортеж (средний_пинг, минимальный_пинг)
        """
        ping_results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for _ in range(count):
                    start_time = time.time()
                    
                    try:
                        async with session.get(url, timeout=5) as response:
                            await response.text()
                            end_time = time.time()
                            ping_time = (end_time - start_time) * 1000  # Перевод в мс
                            ping_results.append(ping_time)
                    except Exception as e:
                        logger.error(f"Ошибка при измерении пинга до {url}: {e}")
                        continue
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(0.2)
                
                if ping_results:
                    return mean(ping_results), min(ping_results)
                else:
                    return 0, 0
                    
        except Exception as e:
            logger.error(f"Ошибка при измерении пинга до {url}: {e}")
            return 0, 0
    
    async def measure_download_speed(self, url: str) -> float:
        """
        Измеряет скорость загрузки с указанного сервера
        
        Args:
            url: URL для скачивания тестового файла
            
        Returns:
            Скорость загрузки в Мбит/с
        """
        try:
            start_time = time.time()
            total_bytes = 0
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        total_bytes += len(chunk)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 0:
                # Перевод байт в биты (умножаем на 8) и затем из бит/c в Мбит/с (делим на 1_000_000)
                mbps = (total_bytes * 8) / (duration * 1_000_000)
                return mbps
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Ошибка при измерении скорости загрузки с {url}: {e}")
            return 0
    
    async def run_full_test(self) -> Dict:
        """
        Запускает полное тестирование скорости
        
        Returns:
            Словарь с результатами тестирования
        """
        results = {
            "ping": {},
            "download": {},
            "average": {
                "ping": 0,
                "download": 0
            },
            "timestamp": time.time()
        }
        
        # Тестирование пинга
        ping_tasks = []
        for server_url in PING_SERVERS:
            server_name = server_url.split("//")[1].split("/")[0]
            ping_tasks.append(self.measure_ping(server_url))
        
        ping_results = await asyncio.gather(*ping_tasks)
        
        valid_pings = []
        for i, (avg_ping, min_ping) in enumerate(ping_results):
            if avg_ping > 0:
                server_name = PING_SERVERS[i].split("//")[1].split("/")[0]
                results["ping"][server_name] = {
                    "avg": round(avg_ping, 1),
                    "min": round(min_ping, 1)
                }
                valid_pings.append(avg_ping)
        
        if valid_pings:
            results["average"]["ping"] = round(mean(valid_pings), 1)
        
        # Тестирование скорости загрузки
        download_tasks = []
        for server_url in SPEED_TEST_SERVERS:
            download_tasks.append(self.measure_download_speed(server_url))
        
        download_results = await asyncio.gather(*download_tasks)
        
        valid_speeds = []
        for i, speed in enumerate(download_results):
            if speed > 0:
                server_name = SPEED_TEST_SERVERS[i].split("//")[1].split("/")[0]
                results["download"][server_name] = round(speed, 2)
                valid_speeds.append(speed)
        
        if valid_speeds:
            results["average"]["download"] = round(mean(valid_speeds), 2)
        
        # Сохраняем результаты
        self.last_results = results
        return results
    
    def format_results(self, results: Dict = None) -> str:
        """
        Форматирует результаты тестирования в читаемый вид
        
        Args:
            results: Результаты тестирования
            
        Returns:
            Строка с результатами
        """
        if results is None:
            results = self.last_results
            
        if not results:
            return "🔴 Нет данных о тестировании скорости"
        
        text = "🚀 Результаты тестирования скорости:\n\n"
        
        # Средний пинг
        text += f"📶 Пинг: {results['average']['ping']} мс\n"
        
        # Детали пинга
        text += "\nДетали пинга:\n"
        for server, ping_data in results["ping"].items():
            text += f"  • {server}: {ping_data['avg']} мс (мин: {ping_data['min']} мс)\n"
        
        # Средняя скорость загрузки
        text += f"\n⬇️ Скорость загрузки: {results['average']['download']} Мбит/с\n"
        
        # Детали скорости загрузки
        text += "\nДетали скорости загрузки:\n"
        for server, speed in results["download"].items():
            text += f"  • {server}: {speed} Мбит/с\n"
        
        return text


# Создаем глобальный экземпляр для использования в разных частях бота
speed_tester = SpeedTester()

async def run_speed_test():
    """
    Запускает полное тестирование скорости и возвращает форматированные результаты
    
    Returns:
        Строка с результатами тестирования
    """
    results = await speed_tester.run_full_test()
    return speed_tester.format_results(results)