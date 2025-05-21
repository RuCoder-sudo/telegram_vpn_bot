#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль генерации QR-кодов для VPN-бота
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import logging
import qrcode
import tempfile
from io import BytesIO

logger = logging.getLogger(__name__)

async def generate_qr_from_text(text, error_correction=qrcode.constants.ERROR_CORRECT_M):
    """
    Генерирует QR-код из текста
    
    Args:
        text: Текст для кодирования
        error_correction: Уровень коррекции ошибок
        
    Returns:
        Путь к временному файлу с QR-кодом или None в случае ошибки
    """
    try:
        # Создаем объект QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=10,
            border=4,
        )
        
        # Добавляем данные
        qr.add_data(text)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение во временный файл
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода: {e}")
        return None

async def generate_qr_from_config(config_path):
    """
    Генерирует QR-код из конфигурационного файла WireGuard
    
    Args:
        config_path: Путь к конфигурационному файлу
        
    Returns:
        Путь к временному файлу с QR-кодом или None в случае ошибки
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(config_path):
            logger.error(f"Файл конфигурации не найден: {config_path}")
            return None
        
        # Читаем конфигурацию
        with open(config_path, 'r') as f:
            config_text = f.read()
        
        # Генерируем QR-код
        return await generate_qr_from_text(config_text)
    except Exception as e:
        logger.error(f"Ошибка при генерации QR-кода из конфигурации: {e}")
        return None

async def get_qr_as_bytes(text_or_config):
    """
    Получает QR-код в виде байтов для отправки в Telegram
    
    Args:
        text_or_config: Текст или путь к конфигурационному файлу
        
    Returns:
        BytesIO объект с QR-кодом или None в случае ошибки
    """
    try:
        # Определяем, является ли input файлом или текстом
        if os.path.exists(text_or_config):
            with open(text_or_config, 'r') as f:
                text = f.read()
        else:
            text = text_or_config
        
        # Создаем объект QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        
        # Добавляем данные
        qr.add_data(text)
        qr.make(fit=True)
        
        # Создаем изображение
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохраняем изображение в память
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        
        return img_io
    except Exception as e:
        logger.error(f"Ошибка при получении QR-кода в виде байтов: {e}")
        return None
