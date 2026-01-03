#!/bin/bash

# ===========================================
# Скрипт розгортання бота на Ubuntu VPS
# ===========================================

set -e

echo "🚀 Розгортання бота доставки води..."

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Перевірка root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустіть скрипт від імені root: sudo ./deploy.sh${NC}"
    exit 1
fi

# Оновлення системи
echo -e "${YELLOW}📦 Оновлення системи...${NC}"
apt update && apt upgrade -y

# Встановлення залежностей
echo -e "${YELLOW}📦 Встановлення Python та інших пакетів...${NC}"
apt install python3 python3-pip python3-venv git -y

# Створення користувача
if id "botuser" &>/dev/null; then
    echo -e "${GREEN}✓ Користувач botuser вже існує${NC}"
else
    echo -e "${YELLOW}👤 Створення користувача botuser...${NC}"
    useradd -m -s /bin/bash botuser
fi

# Визначення директорії
BOT_DIR="/home/botuser/water_delivery_bot"

# Копіювання файлів
if [ -d "$BOT_DIR" ]; then
    echo -e "${YELLOW}📁 Оновлення файлів бота...${NC}"
    cp -r ./* "$BOT_DIR/"
else
    echo -e "${YELLOW}📁 Копіювання файлів бота...${NC}"
    mkdir -p "$BOT_DIR"
    cp -r ./* "$BOT_DIR/"
fi

# Встановлення прав
chown -R botuser:botuser "$BOT_DIR"

# Створення віртуального середовища та встановлення залежностей
echo -e "${YELLOW}🐍 Налаштування Python...${NC}"
su - botuser -c "cd $BOT_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"

# Перевірка .env
if [ ! -f "$BOT_DIR/.env" ]; then
    echo -e "${YELLOW}⚙️ Створення .env файлу...${NC}"
    cp "$BOT_DIR/env.example" "$BOT_DIR/.env"
    chown botuser:botuser "$BOT_DIR/.env"
    echo -e "${RED}❗ ВАЖЛИВО: Відредагуйте файл $BOT_DIR/.env${NC}"
    echo -e "${RED}   Додайте BOT_TOKEN та ADMIN_IDS${NC}"
fi

# Встановлення systemd сервісу
echo -e "${YELLOW}⚙️ Налаштування systemd...${NC}"
cp "$BOT_DIR/water-bot.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable water-bot

echo ""
echo -e "${GREEN}✅ Розгортання завершено!${NC}"
echo ""
echo -e "${YELLOW}Наступні кроки:${NC}"
echo "1. Відредагуйте конфігурацію:"
echo "   nano $BOT_DIR/.env"
echo ""
echo "2. Запустіть бота:"
echo "   systemctl start water-bot"
echo ""
echo "3. Перевірте статус:"
echo "   systemctl status water-bot"
echo ""
echo "4. Перегляд логів:"
echo "   journalctl -u water-bot -f"
echo ""

