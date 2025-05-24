# Bedrock App - Обновленное руководство по развертыванию

## 🚀 Быстрый старт (обновленная версия)

### 1. Развертывание приложения
```bash
# В WSL на Windows
cd /mnt/c/_PROJECTS/Bedrock_2.0
chmod +x *.sh

# Полное развертывание с исправлениями зависимостей
./deploy.sh
```

### 2. Проверка fullscreen режима
```bash
# Проверка с Windows (WSL)
./check_fullscreen.sh

# Дополнительные команды проверки:
./check_fullscreen.sh test      # Тест fullscreen на 10 сек
./check_fullscreen.sh restart   # Перезапуск в fullscreen
./check_fullscreen.sh logs      # Просмотр логов
```

### 3. Управление на Raspberry Pi
```bash
# Подключитесь к Pi
ssh standa@192.168.1.233

# Используйте расширенный скрипт управления
./manage_bedrock.sh status          # Статус + дисплей
./manage_bedrock.sh fullscreen      # Тест fullscreen (10 сек)
./manage_bedrock.sh force-full      # Принудительный fullscreen
./manage_bedrock.sh display         # Проверка дисплея
./manage_bedrock.sh diagnostics     # Полная диагностика
```

## ✨ Новые возможности

### 🖥️ Расширенная поддержка Fullscreen
- **Автоматическая настройка** разрешения 1024x600
- **Принудительный полноэкранный режим** без рамок окна
- **Отключение курсора мыши** через unclutter
- **Настройка X11** для kiosk режима
- **Тесты fullscreen** режима

### 🔧 Улучшенная установка зависимостей
- **Поэтапная установка** с обработкой ошибок
- **Fallback на системные пакеты** при сбое pip
- **Проверка каждого модуля** после установки
- **Автоматическое исправление** проблем компиляции

### 📊 Расширенная диагностика
- **Проверка дисплея** и разрешения экрана  
- **Тестирование fullscreen** возможностей
- **Мониторинг производительности** приложения
- **Анализ логов** запуска и работы

## 📋 Команды управления

### Из WSL (Windows):
```bash
./deploy.sh                    # Полное развертывание
./update_bedrock.sh           # Обновление файлов
./check_fullscreen.sh         # Проверка fullscreen
./check_fullscreen.sh test    # Тест на 10 секунд
./check_fullscreen.sh restart # Перезапуск в fullscreen
```

### На Raspberry Pi:
```bash
./manage_bedrock.sh start           # Запуск
./manage_bedrock.sh stop            # Остановка
./manage_bedrock.sh restart         # Перезапуск
./manage_bedrock.sh status          # Расширенный статус
./manage_bedrock.sh fullscreen      # Тест fullscreen (10с)
./manage_bedrock.sh force-full      # Принудительный fullscreen
./manage_bedrock.sh display         # Проверка дисплея  
./manage_bedrock.sh fix-display     # Исправление дисплея
./manage_bedrock.sh diagnostics     # Полная диагностика
./manage_bedrock.sh logs            # Просмотр логов
```

## 🖥️ Настройки Fullscreen

### Автоматические настройки:
- ✅ Разрешение экрана: **1024x600**
- ✅ Полноэкранный режим: **Без рамок окна**
- ✅ Курсор мыши: **Скрыт**
- ✅ Отключение энергосбережения экрана
- ✅ HDMI аудиовыход
- ✅ Автозапуск при загрузке

### Переменные окружения:
```bash
export KIVY_GL_BACKEND=sdl2
export KIVY_WINDOW=sdl2
export SDL_VIDEO_FULLSCREEN_HEAD=0
export SDL_VIDEODRIVER=x11
```

### Конфигурация /boot/firmware/config.txt:
```ini
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 3 0 0 0
hdmi_drive=2
gpu_mem=128
disable_overscan=1
```

## 🔍 Диагностика проблем

### Проблема: Приложение не в fullscreen
```bash
# Проверка с Windows
./check_fullscreen.sh

# Принудительный restart
./check_fullscreen.sh restart

# Или на Pi
ssh standa@192.168.1.233 './manage_bedrock.sh force-full'
```

### Проблема: Неправильное разрешение
```bash
# На Pi проверьте дисплей
./manage_bedrock.sh display

# Исправление
./manage_bedrock.sh fix-display

# Ручная проверка
DISPLAY=:0 xrandr
```

### Проблема: Не работает звук
```bash
# Проверка аудио
amixer cset numid=3 2    # Переключение на HDMI
aplay -l                 # Список устройств
```

## 📊 Мониторинг работы

### Просмотр логов:
```bash
# Основные логи приложения
tail -f /home/standa/bedrock-app/logs/bedrock.log

# Логи запуска
tail -f /home/standa/bedrock-app/logs/startup.log

# Вывод приложения
tail -f /home/standa/bedrock-app/logs/app.log

# Системные логи
journalctl -u bedrock.service -f
```

### Проверка производительности:
```bash
# Использование ресурсов
./manage_bedrock.sh status

# Полная диагностика
./manage_bedrock.sh diagnostics

# Удаленная проверка
./check_fullscreen.sh
```

## 🔄 Обновления

### Обновление кода:
```bash
# Из WSL - быстрое обновление
./update_bedrock.sh

# На Pi - перезапуск с обновлением
./manage_bedrock.sh update
```

### Обновление зависимостей:
```bash
# При проблемах с зависимостями
./fix_dependencies.sh

# Или на Pi
cd /home/standa/bedrock-app
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## 📱 Автозапуск

### Настроенные методы:
1. **Desktop Autostart** (основной):
   - `/home/standa/.config/autostart/bedrock.desktop`
   
2. **Systemd Service** (резервный):
   - `sudo systemctl enable bedrock.service`

### Управление автозапуском:
```bash
# Отключить автозапуск
sudo systemctl disable bedrock.service
rm /home/standa/.config/autostart/bedrock.desktop

# Включить автозапуск
sudo systemctl enable bedrock.service
```

## ⚡ Быстрые команды

```bash
# Проверить всё
./check_fullscreen.sh

# Перезапустить в fullscreen
ssh standa@192.168.1.233 './manage_bedrock.sh force-full'

# Посмотреть что происходит
ssh standa@192.168.1.233 './manage_bedrock.sh status'

# Полная диагностика
ssh standa@192.168.1.233 './manage_bedrock.sh diagnostics'

# Обновить код
./update_bedrock.sh

# Тест fullscreen на 10 секунд
./check_fullscreen.sh test
```

## 🎯 Рекомендации

1. **После развертывания** обязательно перезагрузите Pi:
   ```bash
   ssh standa@192.168.1.233 'sudo reboot'
   ```

2. **Проверьте fullscreen** через 2-3 минуты после загрузки:
   ```bash
   ./check_fullscreen.sh
   ```

3. **При проблемах** используйте диагностику:
   ```bash
   ssh standa@192.168.1.233 './manage_bedrock.sh diagnostics'
   ```

4. **Для отладки** временно отключите автозапуск и запускайте вручную:
   ```bash
   ./manage_bedrock.sh stop
   cd /home/standa/bedrock-app && source venv/bin/activate && python main.py
   ```

Все скрипты теперь содержат улучшенную обработку ошибок и подробные логи для упрощения диагностики!