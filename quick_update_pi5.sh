#!/bin/bash
# Быстрое обновление кода без полного деплоя

PI_HOST="192.168.1.234"
PI_USER="standa"  
PI_PASS="crossover"

echo "🔄 Быстрое обновление Bedrock на Pi 5..."

# Остановить приложение безопасно
sshpass -p "$PI_PASS" ssh "$PI_USER@$PI_HOST" "
    pkill -f 'python.*main.py' 2>/dev/null || true
    ~/bedrock_control.sh stop 2>/dev/null || true
"

# Синхронизировать только изменённые файлы
rsync -avz --checksum \
    --exclude="__pycache__" --exclude="*.pyc" --exclude=".git" --exclude="venv" --exclude="logs/*.log" \
    -e "sshpass -p $PI_PASS ssh" \
    ./ "$PI_USER@$PI_HOST:~/bedrock-app/"

echo "✅ Код обновлён. Приложение перезапустится автоматически через 10 секунд..."
