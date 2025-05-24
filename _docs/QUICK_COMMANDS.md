# 🚀 Быстрые команды Bedrock App

## 📦 Развертывание
```bash
# Полное развертывание (первый раз)
./deploy.sh

# Обновление файлов (последующие разы)
./update_bedrock.sh

# Исправление зависимостей (при проблемах)
./fix_dependencies.sh
```

## 🖥️ Проверка Fullscreen
```bash
# Быстрая проверка
./check_fullscreen.sh

# Тест fullscreen (10 секунд)
./check_fullscreen.sh test

# Перезапуск в fullscreen
./check_fullscreen.sh restart

# Просмотр логов
./check_fullscreen.sh logs
```

## 🎛️ Управление на Pi
```bash
# SSH подключение
ssh standa@192.168.1.233

# Статус приложения
./manage_bedrock.sh status

# Запуск/остановка/перезапуск
./manage_bedrock.sh start
./manage_bedrock.sh stop  
./manage_bedrock.sh restart

# Fullscreen режим
./manage_bedrock.sh fullscreen      # Тест (10с)
./manage_bedrock.sh force-full      # Принудительный

# Диагностика
./manage_bedrock.sh diagnostics     # Полная проверка
./manage_bedrock.sh display         # Проверка дисплея

# Логи
./manage_bedrock.sh logs            # Живые логи
```

## 🔧 Диагностика проблем
```bash
# Если приложение не запускается
ssh standa@192.168.1.233 './manage_bedrock.sh diagnostics'

# Если не fullscreen
./check_fullscreen.sh restart

# Если проблемы с дисплеем
ssh standa@192.168.1.233 './manage_bedrock.sh fix-display'

# Если нет звука
ssh standa@192.168.1.233 'amixer cset numid=3 2'
```

## 📊 Мониторинг
```bash
# Статус всего
./check_fullscreen.sh

# Производительность
ssh standa@192.168.1.233 'htop'

# Логи в реальном времени
ssh standa@192.168.1.233 'tail -f bedrock-app/logs/bedrock.log'
```

## ⚡ Перезагрузка
```bash
# Перезагрузка Pi
ssh standa@192.168.1.233 'sudo reboot'

# Перезапуск только приложения
ssh standa@192.168.1.233 './manage_bedrock.sh restart'

# Принудительный fullscreen перезапуск
ssh standa@192.168.1.233 './manage_bedrock.sh force-full'
```

## 🆘 Экстренное восстановление
```bash
# При критических проблемах
./fix_dependencies.sh                                    # Исправить зависимости
ssh standa@192.168.1.233 './manage_bedrock.sh stop'    # Остановить приложение
./deploy.sh                                             # Переразвернуть
ssh standa@192.168.1.233 'sudo reboot'                 # Перезагрузить Pi
```

---
**💡 Совет**: Добавьте эти команды в закладки или создайте алиасы в `.bashrc` для быстрого доступа!