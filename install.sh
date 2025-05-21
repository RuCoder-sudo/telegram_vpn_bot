#!/bin/bash

# Скрипт установки RuCoder VPN Bot
# Автор: RUCODER (https://рукодер.рф/vpn)

echo "========================================"
echo "  Установка RuCoder VPN Bot"
echo "  Автор: RUCODER (https://рукодер.рф/vpn)"
echo "========================================"
echo

# Проверка привилегий
if [ "$(id -u)" -ne 0 ]; then
    echo "Ошибка: Скрипт должен быть запущен с правами суперпользователя (root)"
    echo "Попробуйте: sudo bash install.sh"
    exit 1
fi

# Установка необходимых пакетов
echo "Шаг 1: Установка необходимых пакетов..."
apt update
apt install -y python3 python3-pip python3-venv wireguard qrencode psutils

# Настройка WireGuard
echo
echo "Шаг 2: Настройка WireGuard..."

# Включение IP-форвардинга
echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/99-wireguard.conf
sysctl -p /etc/sysctl.d/99-wireguard.conf

# Генерация ключей для сервера
cd /etc/wireguard
if [ ! -f "server_private.key" ]; then
    wg genkey | tee server_private.key | wg pubkey > server_public.key
    echo "Ключи WireGuard созданы"
else
    echo "Ключи WireGuard уже существуют"
fi

# Создание конфигурации WireGuard
if [ ! -f "wg0.conf" ]; then
    cat > wg0.conf << EOF
[Interface]
PrivateKey = $(cat server_private.key)
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = false
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o $(ip route | grep default | awk '{print $5}') -j MASQUERADE

# Клиенты будут добавлены здесь
EOF
    echo "Конфигурация WireGuard создана"
else
    echo "Конфигурация WireGuard уже существует"
fi

# Запуск WireGuard
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Создание директории для бота
echo
echo "Шаг 3: Настройка VPN-бота..."
mkdir -p /opt/vpn_bot
cd /opt/vpn_bot

# Копирование файлов бота
echo "Копирование файлов бота..."
cp -r $(dirname "$0")/* /opt/vpn_bot/

# Создание необходимых директорий
mkdir -p /opt/vpn_bot/clients
mkdir -p /opt/vpn_bot/templates
mkdir -p /opt/vpn_bot/database/migrations

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Запрос токена бота
echo
echo "Шаг 4: Настройка переменных окружения..."
echo "Введите токен бота (получите у @BotFather в Telegram):"
read -p "BOT_TOKEN: " bot_token

echo "Введите ваш ID в Telegram (можно получить у @userinfobot):"
read -p "ADMIN_ID: " admin_id

# Определение внешнего IP
SERVER_IP=$(curl -s ifconfig.me)
echo "Определен внешний IP: $SERVER_IP"

# Создание файла .env
cat > .env << EOF
BOT_TOKEN=$bot_token
ADMIN_IDS=$admin_id
SERVER_IP=$SERVER_IP
SERVER_PORT=51820
DNS_SERVERS=8.8.8.8, 8.8.4.4
WEBSITE_URL=https://рукодер.рф/vpn
EOF

echo ".env файл создан"

# Инициализация базы данных
echo
echo "Шаг 5: Инициализация базы данных..."
python init_db.py

# Создание сервиса
echo
echo "Шаг 6: Создание сервиса автозапуска..."
cat > /etc/systemd/system/vpn-bot.service << EOF
[Unit]
Description=RuCoder Telegram VPN Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vpn_bot
Environment=PATH=/opt/vpn_bot/venv/bin
ExecStart=/opt/vpn_bot/venv/bin/python /opt/vpn_bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Активация и запуск сервиса
systemctl daemon-reload
systemctl enable vpn-bot
systemctl start vpn-bot

echo
echo "Шаг 7: Создание скриптов управления..."

# Скрипт для проверки статуса
cat > /usr/local/bin/vpnbot-status << EOF
#!/bin/bash
echo "Статус VPN-бота:"
systemctl status vpn-bot
echo
echo "Статус WireGuard:"
systemctl status wg-quick@wg0
echo
echo "Активные подключения WireGuard:"
wg show
EOF
chmod +x /usr/local/bin/vpnbot-status

# Скрипт для перезапуска
cat > /usr/local/bin/vpnbot-restart << EOF
#!/bin/bash
echo "Перезапуск VPN-бота..."
systemctl restart vpn-bot
echo "Перезапуск WireGuard..."
systemctl restart wg-quick@wg0
echo "Готово!"
EOF
chmod +x /usr/local/bin/vpnbot-restart

# Скрипт для создания резервных копий
cat > /usr/local/bin/vpnbot-backup << EOF
#!/bin/bash
BACKUP_DIR="/root/vpn_backups/\$(date +%Y-%m-%d)"
mkdir -p \$BACKUP_DIR
echo "Создание резервной копии в \$BACKUP_DIR"
cp -r /etc/wireguard \$BACKUP_DIR/
cp -r /opt/vpn_bot/clients \$BACKUP_DIR/
cp /opt/vpn_bot/vpn_bot.db \$BACKUP_DIR/
cp /opt/vpn_bot/.env \$BACKUP_DIR/
echo "Резервная копия создана!"
EOF
chmod +x /usr/local/bin/vpnbot-backup

# Настройка автоматического резервного копирования
echo "0 2 * * * root /usr/local/bin/vpnbot-backup" > /etc/cron.d/vpnbot-backup

echo
echo "========================================"
echo "  Установка RuCoder VPN Bot завершена!"
echo "========================================"
echo
echo "Бот запущен и готов к использованию."
echo "Команды для управления:"
echo "  vpnbot-status  - проверка статуса"
echo "  vpnbot-restart - перезапуск"
echo "  vpnbot-backup  - создание резервной копии"
echo
echo "Логи бота: journalctl -u vpn-bot -f"
echo
echo "Автор: RUCODER (https://рукодер.рф/vpn)"
echo "========================================"
