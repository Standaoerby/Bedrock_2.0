import os
import sys
import subprocess

# Основные папки и файлы по структуре проекта
PROJECT_STRUCTURE = [
    'main.py',
    'main.kv',
    'themes/minecraft/light/',
    'themes/minecraft/dark/',
    'assets/images/',
    'media/',
    'config/',
    'pages/',
    'services/',
]

PAGES_FILES = [
    'home.py', 'alarm.py', 'schedule.py', 'weather.py', 'pigs.py', 'settings.py'
]
SERVICES_FILES = [
    'api.py', 'sensors.py', 'notifier.py'
]

def check_and_create(path):
    if path.endswith('/'):
        if not os.path.isdir(path):
            print(f'Создаю папку: {path}')
            os.makedirs(path, exist_ok=True)
    else:
        if not os.path.isfile(path):
            print(f'Создаю файл: {path}')
            open(path, 'a', encoding='utf-8').close()

def check_project_structure():
    print('\nПроверка структуры проекта...\n')
    for item in PROJECT_STRUCTURE:
        check_and_create(item)
    # Страницы
    for fname in PAGES_FILES:
        check_and_create(os.path.join('pages', fname))
    # Сервисы
    for fname in SERVICES_FILES:
        check_and_create(os.path.join('services', fname))
    # User config
    user_json = os.path.join('config', 'user.json')
    if not os.path.isfile(user_json):
        with open(user_json, 'w', encoding='utf-8') as f:
            f.write('{}')
        print('Создаю config/user.json')

def check_python_version():
    print('\nПроверка версии Python...')
    major, minor = sys.version_info[:2]
    print(f'Python {major}.{minor}')
    if major < 3 or (major == 3 and minor < 10):
        print('❌ Требуется Python >= 3.10')
        sys.exit(1)
    print('✅ Версия Python ок')

def check_dependencies():
    print('\nПроверка зависимостей...')
    REQUIRED = ['kivy', 'kivymd', 'requests']
    missing = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
            print(f'✅ {pkg} установлен')
        except ImportError:
            print(f'❌ {pkg} не найден')
            missing.append(pkg)
    if missing:
        print('\nМожно установить недостающие пакеты командой:')
        print('pip install ' + ' '.join(missing))

if __name__ == "__main__":
    check_python_version()
    check_project_structure()
    check_dependencies()
