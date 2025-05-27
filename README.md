# 🎮 BEDROCK 2.0

**Мультимедийная панель управления для Raspberry Pi 5 с сенсорным экраном 1024×600**

---

## 🚀 ОСОБЕННОСТИ

- **🖥️ Fullscreen Kiosk Mode** - Полноэкранный режим киоска для Pi 5
- **🎨 Dynamic Themes** - Автопереключение светлой/темной темы по датчику освещенности
- **⏰ Smart Alarm Clock** - Будильник с настраиваемыми мелодиями и fade-in
- **🌤️ Weather Dashboard** - Прогноз погоды + показания внутренних датчиков
- **📅 Schedule Manager** - Отображение недельного расписания
- **🐷 Pet Care Tracker** - Трекер ухода за питомцами с индикаторами
- **🔊 Hardware Volume Control** - Физические кнопки громкости
- **📱 Touch-Optimized UI** - Интерфейс оптимизирован для сенсорного ввода

---

## 🔧 СИСТЕМНЫЕ ТРЕБОВАНИЯ

### Raspberry Pi 5
- **ОС:** Raspberry Pi OS Bookworm (64-bit Desktop)
- **RAM:** 4GB+ рекомендуется
- **Дисплей:** 1024×600 touchscreen
- **Датчики:** ENS160 (воздух), AHT21 (температура/влажность), LDR (свет)
- **GPIO:** Кнопки громкости на пинах 23, 24

### Windows 11 (Разработка)
- **WSL2** для деплоя
- **VS Code** рекомендуется
- **Python 3.10+**

---

## ⚡ БЫСТРЫЙ СТАРТ

### 1. Клонирование проекта
```bash
git clone <your-repo> /mnt/c/_PROJECTS/Bedrock_2.0
cd /mnt/c/_PROJECTS/Bedrock_2.0
```

### 2. Настройка конфигурации деплоя
Отредактируй IP и данные для подключения в `deploy.sh`:
```bash
PI_HOST="192.168.1.243"        # IP твоего Pi
PI_USER="standa"               # Имя пользователя
PI_PASS="crossover"            # Пароль
```

### 3. Проверка проекта
```bash
python health_check.py --fix
```

### 4. Деплой на Pi 5
```bash
./deploy.sh
```

### 5. Готово! 🎉
Приложение автоматически запустится на Pi в fullscreen режиме.

---

## 🎛️ УПРАВЛЕНИЕ

### На Windows (разработка):
```bash
./deploy.sh                     # Полный деплой
./update.sh                     # Быстрое обновление
python health_check.py --fix    # Диагностика
```

### На Raspberry Pi:
```bash
./manage_bedrock.sh start       # Запуск
./manage_bedrock.sh stop        # Остановка
./manage_bedrock.sh restart     # Перезапуск
./manage_bedrock.sh status      # Статус
./manage_bedrock.sh logs        # Логи
./manage_bedrock.sh health      # Диагностика
```

---

## 📱 ИНТЕРФЕЙС

### Экраны приложения:
- **🏠 Home** - Часы, дата, погода, уведомления, статус будильника
- **⏰ Alarm** - Настройка будильника с мелодиями и днями недели
- **📅 School** - Недельное расписание занятий
- **🌤️ Climate** - Погода + показания датчиков воздуха
- **🐷 Pigs** - Трекер ухода за питомцами (кормление, поение, уборка)
- **⚙️ Settings** - Настройки тем, пользователя, датчиков

### Функции управления:
- **Touch Navigation** - Сенсорная навигация между экранами
- **Volume Buttons** - Физические кнопки громкости (GPIO 23/24)
- **Auto Theme** - Переключение темы по освещению
- **Sound Feedback** - Звуковая обратная связь

---

## 🎨 ТЕМЫ

### Minecraft Theme
- **Light Mode** - Светлая дневная тема
- **Dark Mode** - Темная ночная тема  
- **Auto Switch** - Автопереключение по датчику освещенности
- **Pixel Art Style** - Стиль в духе Minecraft

### Кастомизация:
```
themes/minecraft/
├── light/
│   ├── theme.json          # Конфигурация
│   ├── background.png      # Фон
│   └── overlay_*.png       # Overlay для экранов
└── dark/
    └── ...                 # Аналогично
```

---

## 🔌 ДАТЧИКИ И HARDWARE

### Поддерживаемые датчики:
- **ENS160** - Качество воздуха (CO2, TVOC, AQI)
- **AHT21** - Температура и влажность
- **LDR** - Датчик освещенности (GPIO 12)

### GPIO распиновка:
- **GPIO 12** - Датчик света (LDR)
- **GPIO 23** - Кнопка увеличения громкости
- **GPIO 24** - Кнопка уменьшения громкости

### I2C адреса:
- **0x53** - ENS160 (качество воздуха)
- **0x38** - AHT21 (температура/влажность)

---

## 📊 АРХИТЕКТУРА

### Ключевые компоненты:
- **`main.py`** - Главное MDApp приложение
- **`bedrock_launcher.py`** - Лаунчер с настройками Pi 5
- **`utils/theme_manager.py`** - Управление темами
- **`utils/common.py`** - Общие утилиты и BasePage
- **`services/`** - Сервисы (погода, датчики, звук, будильник)
- **`pages/`** - Экраны приложения

### Особенности архитектуры:
- **ConfigManager** - Централизованное управление конфигурацией
- **ThemeManager** - Динамическое переключение тем
- **BasePage** - Базовый класс для всех экранов
- **Service Architecture** - Модульные сервисы для разных функций

---

## 🔧 РАЗРАБОТКА

### Локальная разработка:
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py
```

### Основные зависимости:
- **Kivy 2.3+** - GUI фреймворк
- **KivyMD 2.0+** - Material Design компоненты
- **pygame** - Звуковая поддержка
- **requests** - HTTP запросы для погоды
- **rpi-lgpio** - GPIO для Pi 5

### Тестирование:
```bash
python health_check.py      # Проверка конфигурации
python health_check.py --fix # С автоисправлениями
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
Bedrock_2.0/
├── 🚀 deploy.sh                    # Основной скрипт деплоя
├── ⚡ update.sh                    # Быстрое обновление
├── 🎯 bedrock_launcher.py          # Лаунчер для Pi 5
├── 🔍 health_check.py              # Диагностика системы
├── 🎛️ manage_bedrock.sh            # Управление на Pi
├── 📱 main.py                      # Главное приложение
├── 🎨 main.kv                      # UI разметка
├── 📦 requirements.txt             # Зависимости Python
├── 📁 utils/
│   ├── theme_manager.py           # Управление темами
│   ├── common.py                  # Общие утилиты
│   └── error_handler.py           # Обработка ошибок
├── 🔧 services/                   # Сервисы приложения
├── 📱 pages/                      # Экраны (Home, Alarm, etc.)
├── 🎨 themes/minecraft/           # Светлая/темная темы
├── ⚙️ config/                     # Конфигурационные файлы
├── 📊 _preq/                      # Вспомогательные скрипты
└── 📚 docs/                       # Документация
```

---

## 🔍 ДИАГНОСТИКА

### Health Check:
```bash
python health_check.py --fix
```
Проверяет и исправляет:
- ✅ Конфигурационные файлы
- ✅ Структуру тем
- ✅ Критические файлы
- ✅ Autostart конфликты

### Логи:
```bash
./manage_bedrock.sh logs 50    # Последние 50 строк
```

Доступные логи:
- `logs/app.log` - Основной лог приложения
- `logs/launcher.log` - Лог лаунчера
- `logs/autostart.log` - Лог автозапуска
- `logs/startup_error.log` - Ошибки запуска

---

## 🆘 TROUBLESHOOTING

### Частые проблемы:

**🔴 Приложение не запускается:**
```bash
./manage_bedrock.sh logs
./manage_bedrock.sh health --fix
```

**🔴 Нет fullscreen режима:**
```bash
./manage_bedrock.sh force-full
```

**🔴 Проблемы с темами:**
```bash
./manage_bedrock.sh test-theme
python health_check.py --fix
```

**🔴 Конфликты autostart:**
```bash
ls ~/.config/autostart/bedrock*.desktop
# Должен быть только bedrock.desktop
```

### Переустановка:
```bash
./deploy.sh  # Полная переустановка
```

---

## 📄 ДОКУМЕНТАЦИЯ

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Подробное руководство по деплою
- **[Инструкции по консолидации](consolidation_instructions.md)** - Миграция на новую архитектуру
- **[Touch_UI_Pipeline.md](Touch_UI_Pipeline.md)** - Принципы разработки UI

---

## 🤝 КОНТРИБУЦИЯ

1. Fork проекта
2. Создай feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Открой Pull Request

---

## 📜 ЛИЦЕНЗИЯ

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для деталей.

---

## 👨‍💻 АВТОР

**Создано для Raspberry Pi 5 с любовью к Minecraft стилю и удобному UI! 🎮**

---

## 🎯 СТАТУС ПРОЕКТА

**✅ Stable Release 2.0**
- Полностью рабочая версия для Pi 5
- Консолидированная архитектура  
- Автоматический деплой и управление
- Подробная документация

**🎉 Готово к использованию!**