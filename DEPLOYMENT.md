# 🚀 BEDROCK 2.0 - DEPLOYMENT GUIDE

Полное руководство по развертыванию Bedrock 2.0 на Raspberry Pi 5

---

## 📋 СИСТЕМНЫЕ ТРЕБОВАНИЯ

### Raspberry Pi 5
- **Модель:** Raspberry Pi 5 (4GB/8GB RAM)
- **ОС:** Raspberry Pi OS Bookworm (64-bit, Desktop)
- **Дисплей:** 1024x600 touchscreen
- **Хранилище:** microSD 32GB+ (Class 10)
- **Сеть:** Wi-Fi или Ethernet

### Windows 11 (Разработка)
- **WSL2** установлен и настроен
- **VS Code** с Python расширением
- **Git** для версионного контроля

---

## 🔧 АРХИТЕКТУРА РЕШЕНИЯ

### Ключевые компоненты:
- **`bedrock_launcher.py`** - Единый лаунчер с fullscreen конфигурацией
- **`health_check.py`** - Автоматическая диагностика системы
- **`manage_bedrock.sh`** - Управление приложением на Pi
- **`deploy.sh`** - Полный деплой на Pi 5
- **`update.sh`** - Быстрое обновление кода

### Структура приложения:
```
Bedrock_2.0/
├── main.py                     # Основное приложение (MDApp)
├── bedrock_launcher.py         # Лаунчер для Pi 5
├── health_check.py             # Диагностика системы
├── manage_bedrock.sh           # Управление на Pi
├── deploy.sh                   # Скрипт деплоя
├── update.sh                   # Быстрое обновление
├── utils/
│   ├── theme_manager.py        # Управление темами
│   ├── common.py               # Общие утилиты
│   └── error_handler.py        # Обработка ошибок
├── services/                   # Сервисы приложения
├── pages/                      # Экраны приложения
├── themes/minecraft/           # Светлая и темная темы
└── config/                     # Конфигурационные файлы
```

---

## 🛠️ ПРЕДВАРИТЕЛЬНАЯ НАСТРОЙКА

### 1. Подготовка Raspberry Pi 5

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Включение SSH
sudo systemctl enable ssh
sudo systemctl start ssh

# Настройка часового пояса
sudo timedatectl set-timezone Europe/London

# Включение I2C для датчиков
sudo raspi-config nonint do_i2c 0
```

### 2. Настройка Windows 11 + WSL2

```bash
# В WSL2:
sudo apt update
sudo apt install -y sshpass rsync openssh-client git

# Клонирование проекта
git clone <your-repo> /mnt/c/_PROJECTS/Bedrock_2.0
cd /mnt/c/_PROJECTS/Bedrock_2.0
```

---

## 🚀 ПРОЦЕСС ДЕПЛОЯ

### Шаг 1: Настройка SSH ключей (опционально)
```bash
cd _preq/
./setup_ssh_keys.sh
```

### Шаг 2: Конфигурация деплоя
Отредактируй переменные в начале `deploy.sh`:
```bash
PI_HOST="192.168.1.243"        # IP адрес твоего Pi
PI_USER="standa"               # Имя пользователя на Pi
PI_PASS="crossover"            # Пароль (если не используешь SSH ключи)
LOCAL_PROJECT_PATH="/mnt/c/_PROJECTS/Bedrock_2.0"
REMOTE_APP_PATH="/home/standa/bedrock-app"
```

### Шаг 3: Полный деплой
```bash
# Запуск полного деплоя
./deploy.sh

# Или с помощью:
chmod +x deploy.sh
./deploy.sh
```

### Что делает деплой:
1. ✅ Проверяет prerequisites (SSH, tools)
2. ✅ Создает backup существующей версии
3. ✅ Устанавливает системные зависимости для Pi 5
4. ✅ Настраивает hardware (I2C, GPIO, audio, display)
5. ✅ Синхронизирует код проекта
6. ✅ Создает Python virtual environment
7. ✅ Устанавливает Python зависимости
8. ✅ Настраивает автозапуск
9. ✅ Тестирует установку
10. ✅ Создает management скрипты

---

## ⚡ БЫСТРОЕ ОБНОВЛЕНИЕ

После внесения изменений в код:

```bash
# Быстрая синхронизация измененных файлов
./update.sh

# Или с принудительным перезапуском:
./update.sh --restart

# Проверка статуса:
./update.sh --status

# Просмотр логов:
./update.sh --logs
```

---

## 🎛️ УПРАВЛЕНИЕ НА RASPBERRY PI

После деплоя доступны команды управления:

### Основные команды:
```bash
ssh standa@192.168.1.234
cd bedrock-app

# Управление приложением
./manage_bedrock.sh start        # Запуск
./manage_bedrock.sh stop         # Остановка
./manage_bedrock.sh restart      # Перезапуск
./manage_bedrock.sh status       # Статус

# Диагностика
./manage_bedrock.sh health       # Проверка здоровья
./manage_bedrock.sh health --fix # С автоисправлениями
./manage_bedrock.sh logs 20      # Последние 20 строк логов

# Специальные функции
./manage_bedrock.sh force-full   # Принудительный fullscreen
./manage_bedrock.sh test-theme   # Тест переключения тем
```

### Статус приложения:
```bash
./manage_bedrock.sh status
```

Покажет:
- Статус процесса (Running/Stopped)
- PID и время работы
- Использование памяти
- Температуру CPU
- Путь к файлам

---

## 🔍 ДИАГНОСТИКА И TROUBLESHOOTING

### Health Check
```bash
# Базовая проверка
python health_check.py

# С автоисправлениями
python health_check.py --fix
```

Проверяет:
- ✅ Структуру конфигурационных файлов
- ✅ Доступность тем (light/dark)
- ✅ Структуру директорий
- ✅ Критические файлы
- ✅ Конфликты autostart

### Часто встречающиеся проблемы:

**1. Приложение не запускается:**
```bash
./manage_bedrock.sh logs
# Проверь ошибки в логах
```

**2. Нет fullscreen режима:**
```bash
./manage_bedrock.sh force-full
# Принудительный запуск в fullscreen
```

**3. Проблемы с темами:**
```bash
./manage_bedrock.sh test-theme
# Тест переключения тем
```

**4. Конфликты autostart:**
```bash
ls ~/.config/autostart/bedrock*.desktop
# Должен быть только один файл: bedrock.desktop
```

### Логи и отладка:
```bash
# Основные логи
tail -50 logs/app.log           # Главный лог приложения
tail -20 logs/launcher.log      # Лог лаунчера
tail -20 logs/autostart.log     # Лог автозапуска
tail -10 logs/startup_error.log # Ошибки запуска
```

---

## 🔄 АВТОЗАПУСК

### Как работает автозапуск:
1. **Desktop Entry:** `~/.config/autostart/bedrock.desktop`
2. **Delay:** 15 секунд после загрузки рабочего стола
3. **Environment:** Активация venv + настройка DISPLAY
4. **Logging:** Все выводы в `logs/autostart.log`

### Управление автозапуском:
```bash
# Отключить автозапуск
rm ~/.config/autostart/bedrock.desktop

# Включить автозапуск
# (файл создается автоматически при деплое)

# Проверить статус
ls ~/.config/autostart/bedrock*.desktop
```

---

## 🎨 ТЕМЫ И КАСТОМИЗАЦИЯ

### Структура тем:
```
themes/minecraft/
├── light/
│   ├── theme.json              # Конфигурация светлой темы
│   ├── background.png          # Фон
│   ├── overlay_*.png           # Overlay для каждого экрана
│   └── button*.png             # Кнопки
└── dark/
    ├── theme.json              # Конфигурация темной темы
    └── ...                     # Аналогичные файлы
```

### Автопереключение тем:
- **Датчик освещенности:** Автоматическое переключение light/dark
- **Настройка:** Через экран Settings
- **Задержка:** Настраиваемая (1-5 секунд)

---

## 📊 МОНИТОРИНГ И ОБСЛУЖИВАНИЕ

### Регулярные проверки:
```bash
# Еженедельно
./manage_bedrock.sh health --fix
./manage_bedrock.sh status

# Ежемесячно  
sudo apt update && sudo apt upgrade -y
./deploy.sh  # Полное обновление

# При проблемах
./manage_bedrock.sh logs 50
python health_check.py --fix
```

### Backup конфигурации:
```bash
# Создается автоматически при каждом деплое
ls bedrock-app_backup_*

# Ручной backup
cp -r bedrock-app bedrock-app_backup_$(date +%Y%m%d_%H%M%S)
```

---

## 🔒 БЕЗОПАСНОСТЬ

### Рекомендации:
- ✅ Настрой SSH ключи вместо паролей
- ✅ Измени стандартные пароли на Pi
- ✅ Используй firewall (ufw) если Pi доступен из интернета
- ✅ Регулярно обновляй систему

### SSH ключи:
```bash
# Настройка автоматическая
cd _preq/
./setup_ssh_keys.sh
```

---

## 📞 ПОДДЕРЖКА

### При проблемах:
1. Запусти `python health_check.py --fix`
2. Проверь логи `./manage_bedrock.sh logs`
3. Попробуй `./manage_bedrock.sh restart`
4. В крайнем случае - полный редеплой: `./deploy.sh`

### Сбор информации для отладки:
```bash
# Создай диагностический отчет
./manage_bedrock.sh status > diagnostic_report.txt
./manage_bedrock.sh logs 100 >> diagnostic_report.txt
python health_check.py >> diagnostic_report.txt
```

---

## 🎉 ГОТОВО!

После успешного деплоя у тебя будет:
- ✅ Стабильно работающее приложение на Pi 5
- ✅ Автоматический запуск при загрузке
- ✅ Fullscreen режим 1024x600
- ✅ Удобные инструменты управления
- ✅ Автоматическая диагностика
- ✅ Простое обновление кода

**Bedrock 2.0 готов к использованию! 🚀**