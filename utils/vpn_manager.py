#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль управления WireGuard VPN
Автор: RUCODER (https://рукодер.рф/vpn)
"""

import os
import subprocess
import logging
import re
import tempfile
import ipaddress
import secrets
import base64
from datetime import datetime

from config import (
    WG_CONFIG_PATH,
    WG_SERVER_PRIVKEY_PATH,
    WG_SERVER_PUBKEY_PATH,
    SERVER_IP,
    SERVER_PORT,
    DNS_SERVERS,
    CLIENTS_DIR
)

logger = logging.getLogger(__name__)

class VPNManager:
    def __init__(self):
        # Убедимся, что директория для клиентов существует
        os.makedirs(CLIENTS_DIR, exist_ok=True)
    
    def get_server_public_key(self):
        """Получает публичный ключ сервера"""
        try:
            with open(WG_SERVER_PUBKEY_PATH, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Файл публичного ключа сервера не найден: {WG_SERVER_PUBKEY_PATH}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при чтении публичного ключа сервера: {e}")
            return None
    
    def generate_keypair(self):
        """Генерирует пару ключей WireGuard"""
        try:
            # Генерация приватного ключа
            private_key_proc = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True,
                check=True
            )
            private_key = private_key_proc.stdout.strip()
            
            # Генерация публичного ключа на основе приватного
            public_key_proc = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            )
            public_key = public_key_proc.stdout.strip()
            
            return private_key, public_key
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при генерации ключей WireGuard: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Неизвестная ошибка при генерации ключей: {e}")
            return None, None
    
    def get_next_available_ip(self):
        """Получает следующий доступный IP-адрес для клиента"""
        try:
            # Чтение конфигурации сервера
            with open(WG_CONFIG_PATH, 'r') as f:
                config = f.read()
            
            # Поиск всех используемых IP-адресов клиентов
            ip_pattern = re.compile(r'AllowedIPs\s*=\s*10\.0\.0\.(\d+)/32')
            used_ips = set(int(match.group(1)) for match in ip_pattern.finditer(config))
            
            # Поиск следующего доступного IP
            for i in range(2, 255):  # 10.0.0.1 зарезервирован для сервера
                if i not in used_ips:
                    return f"10.0.0.{i}/32"
            
            raise ValueError("Нет доступных IP-адресов в подсети")
        except Exception as e:
            logger.error(f"Ошибка при поиске доступного IP: {e}")
            return None
    
    def create_client_config(self, client_name, client_ip, client_private_key, client_public_key):
        """Создает конфигурационный файл для клиента"""
        try:
            server_public_key = self.get_server_public_key()
            if not server_public_key:
                return None
            
            # Получаем IP-адрес без маски подсети
            client_ip_clean = client_ip.split('/')[0]
            
            # Формируем конфигурацию клиента
            client_config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}
DNS = {DNS_SERVERS}

[Peer]
PublicKey = {server_public_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {SERVER_IP}:{SERVER_PORT}
PersistentKeepalive = 25
"""
            
            # Создаем директорию для конфигурации клиента, если её нет
            client_dir = os.path.join(CLIENTS_DIR, client_name)
            os.makedirs(client_dir, exist_ok=True)
            
            # Сохраняем конфигурацию в файл
            config_path = os.path.join(client_dir, f"{client_name}.conf")
            with open(config_path, 'w') as f:
                f.write(client_config)
            
            return config_path
        except Exception as e:
            logger.error(f"Ошибка при создании конфигурации клиента: {e}")
            return None
    
    def add_client_to_server_config(self, client_name, client_public_key, client_ip):
        """Добавляет клиента в конфигурацию сервера"""
        try:
            # Проверяем, существует ли конфигурация сервера
            if not os.path.exists(WG_CONFIG_PATH):
                logger.error(f"Конфигурация сервера не найдена: {WG_CONFIG_PATH}")
                return False
            
            # Формируем конфигурацию клиента для сервера
            client_config = f"""
# Клиент: {client_name} - добавлен {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
[Peer]
PublicKey = {client_public_key}
AllowedIPs = {client_ip}
"""
            
            # Добавляем конфигурацию клиента в конфигурацию сервера
            with open(WG_CONFIG_PATH, 'a') as f:
                f.write(client_config)
            
            # Применяем изменения с помощью команды wg-quick
            subprocess.run(['systemctl', 'restart', 'wg-quick@wg0'], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при применении конфигурации сервера: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при добавлении клиента в конфигурацию сервера: {e}")
            return False
    
    def remove_client_from_server_config(self, client_name, client_public_key):
        """Удаляет клиента из конфигурации сервера"""
        try:
            # Проверяем, существует ли конфигурация сервера
            if not os.path.exists(WG_CONFIG_PATH):
                logger.error(f"Конфигурация сервера не найдена: {WG_CONFIG_PATH}")
                return False
            
            # Читаем текущую конфигурацию
            with open(WG_CONFIG_PATH, 'r') as f:
                config_lines = f.readlines()
            
            # Ищем и удаляем секцию клиента
            new_config_lines = []
            skip_lines = False
            
            for line in config_lines:
                if f"# Клиент: {client_name}" in line:
                    skip_lines = True
                    continue
                
                if skip_lines and "[Peer]" in line:
                    continue
                
                if skip_lines and "PublicKey" in line and client_public_key in line:
                    continue
                
                if skip_lines and "AllowedIPs" in line:
                    skip_lines = False
                    continue
                
                new_config_lines.append(line)
            
            # Записываем обновленную конфигурацию
            with open(WG_CONFIG_PATH, 'w') as f:
                f.writelines(new_config_lines)
            
            # Применяем изменения с помощью команды wg-quick
            subprocess.run(['systemctl', 'restart', 'wg-quick@wg0'], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при применении конфигурации сервера: {e}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении клиента из конфигурации сервера: {e}")
            return False
    
    def get_active_connections(self):
        """Получает список активных подключений"""
        try:
            # Выполняем команду wg show
            wg_show = subprocess.run(
                ['wg', 'show'],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = wg_show.stdout
            
            # Парсим вывод команды
            connections = []
            current_peer = None
            
            for line in output.splitlines():
                line = line.strip()
                
                if line.startswith("peer:"):
                    current_peer = {"public_key": line.split("peer:")[1].strip()}
                elif line.startswith("endpoint:") and current_peer:
                    current_peer["endpoint"] = line.split("endpoint:")[1].strip()
                elif line.startswith("allowed ips:") and current_peer:
                    current_peer["allowed_ips"] = line.split("allowed ips:")[1].strip()
                elif line.startswith("latest handshake:") and current_peer:
                    current_peer["latest_handshake"] = line.split("latest handshake:")[1].strip()
                elif line.startswith("transfer:") and current_peer:
                    transfer_parts = line.split("transfer:")[1].strip().split("received,")
                    if len(transfer_parts) == 2:
                        current_peer["received"] = transfer_parts[0].strip()
                        current_peer["sent"] = transfer_parts[1].strip()
                    
                    # Добавляем пира в список и сбрасываем текущего пира
                    connections.append(current_peer)
                    current_peer = None
            
            return connections
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при получении активных подключений: {e}")
            return []
        except Exception as e:
            logger.error(f"Неизвестная ошибка при получении активных подключений: {e}")
            return []
    
    def check_wireguard_status(self):
        """Проверяет статус службы WireGuard"""
        try:
            status = subprocess.run(
                ['systemctl', 'status', 'wg-quick@wg0'],
                capture_output=True,
                text=True
            )
            
            is_active = "Active: active" in status.stdout
            
            return {
                "is_active": is_active,
                "status_text": status.stdout,
                "error": status.stderr if status.returncode != 0 else None
            }
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса WireGuard: {e}")
            return {
                "is_active": False,
                "status_text": None,
                "error": str(e)
            }
    
    def restart_wireguard(self):
        """Перезапускает службу WireGuard"""
        try:
            subprocess.run(['systemctl', 'restart', 'wg-quick@wg0'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при перезапуске WireGuard: {e}")
            return False
        except Exception as e:
            logger.error(f"Неизвестная ошибка при перезапуске WireGuard: {e}")
            return False
    
    def create_client(self, client_name):
        """Создает нового клиента VPN"""
        try:
            # Генерируем ключи
            private_key, public_key = self.generate_keypair()
            if not private_key or not public_key:
                return None
            
            # Получаем доступный IP-адрес
            client_ip = self.get_next_available_ip()
            if not client_ip:
                return None
            
            # Создаем конфигурацию клиента
            config_path = self.create_client_config(client_name, client_ip, private_key, public_key)
            if not config_path:
                return None
            
            # Добавляем клиента в конфигурацию сервера
            if not self.add_client_to_server_config(client_name, public_key, client_ip):
                # Удаляем созданную конфигурацию клиента в случае ошибки
                os.remove(config_path)
                return None
            
            return {
                "name": client_name,
                "private_key": private_key,
                "public_key": public_key,
                "ip_address": client_ip,
                "config_path": config_path
            }
        except Exception as e:
            logger.error(f"Ошибка при создании клиента VPN: {e}")
            return None
    
    def delete_client(self, client_name, client_public_key):
        """Удаляет клиента VPN"""
        try:
            # Удаляем клиента из конфигурации сервера
            if not self.remove_client_from_server_config(client_name, client_public_key):
                return False
            
            # Удаляем файлы конфигурации клиента
            client_dir = os.path.join(CLIENTS_DIR, client_name)
            if os.path.exists(client_dir):
                config_path = os.path.join(client_dir, f"{client_name}.conf")
                if os.path.exists(config_path):
                    os.remove(config_path)
                
                # Удаляем директорию клиента, если она пуста
                try:
                    os.rmdir(client_dir)
                except OSError:
                    # Директория не пуста, оставляем её
                    pass
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении клиента VPN: {e}")
            return False
    
    def update_client_config(self, client_name, client_ip=None, allowed_ips=None):
        """Обновляет конфигурацию клиента"""
        try:
            client_dir = os.path.join(CLIENTS_DIR, client_name)
            config_path = os.path.join(client_dir, f"{client_name}.conf")
            
            # Проверяем, существует ли конфигурация клиента
            if not os.path.exists(config_path):
                logger.error(f"Конфигурация клиента не найдена: {config_path}")
                return False
            
            # Читаем текущую конфигурацию
            with open(config_path, 'r') as f:
                config_lines = f.readlines()
            
            # Обновляем конфигурацию
            new_config_lines = []
            for line in config_lines:
                if client_ip and line.startswith("Address = "):
                    new_config_lines.append(f"Address = {client_ip}\n")
                elif allowed_ips and line.startswith("AllowedIPs = "):
                    new_config_lines.append(f"AllowedIPs = {allowed_ips}\n")
                else:
                    new_config_lines.append(line)
            
            # Записываем обновленную конфигурацию
            with open(config_path, 'w') as f:
                f.writelines(new_config_lines)
            
            # Обновляем конфигурацию сервера, если изменился IP
            if client_ip:
                # Получаем публичный ключ клиента из конфигурации
                public_key = None
                with open(config_path, 'r') as f:
                    config = f.read()
                    match = re.search(r'\[Peer\].*?PublicKey\s*=\s*(\S+)', config, re.DOTALL)
                    if match:
                        public_key = match.group(1)
                
                if public_key:
                    # Удаляем клиента из конфигурации сервера
                    self.remove_client_from_server_config(client_name, public_key)
                    
                    # Добавляем клиента с новым IP
                    self.add_client_to_server_config(client_name, public_key, client_ip)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении конфигурации клиента: {e}")
            return False
