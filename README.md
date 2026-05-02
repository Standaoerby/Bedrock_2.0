# Bedrock 2.0

Мультимедийная панель управления для Raspberry Pi 5 с touchscreen 1024×600.
Часы, будильник, погода, расписание, трекер ухода за свинками. Kivy + KivyMD,
Minecraft-style темы (light/dark), мок-сенсоры на Windows для разработки.

## Версии

- **`pi/main` ⇒ `0.8.2`** — последняя стабильная, крутится на Pi5 (192.168.1.233)
- **`origin/main` ⇒ `Soso`** — устаревшая попытка 1.0.x, оставлена для истории, **не использовать**
- **`recovery-from-0.8.2`** — текущая рабочая ветка, основана на 0.8.2, исправления см. [_docs/CHANGELOG.md](_docs/CHANGELOG.md)

См. [_docs/RECOVERY.md](_docs/RECOVERY.md) — почему откатились с 1.0.x.

## Запуск

### Локально (Windows / dev)

```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
python main.py
```

Сенсоры автоматически переключаются на mock на не-Linux платформах.

### На Pi 5

```bash
ssh standa@192.168.1.233
cd ~/git-repos/bedrock-app
git fetch origin
git checkout recovery-from-0.8.2
sudo apt install python3-lgpio python3-blinka  # GPIO + I2C
pip install -r requirements.txt
python main.py
```

## Структура

```
main.py            — точка входа, BedrockApp(MDApp)
main.kv            — корневой layout, темовые widget-rule (ThemedLabel/Panel/Button)
pages/             — экраны: home, alarm, schedule, weather, pigs, settings
services/          — бизнес-логика: alarm_clock, weather, sensor, schedule, pigs, notifications
classes/           — переиспользуемые виджеты: marquee, alarm_popup
themes/minecraft/  — light/ и dark/ — JSON конфиг + PNG ассеты
config/            — пользовательские настройки (user.json, alarm.json и т.п.)
_docs/             — заметки и история проекта
assets/            — шрифты, звуки, картинки
media/ringtones/   — мелодии для будильника
```

## Архитектура темы

`theme_config` теперь Kivy `DictProperty` (см. [main.py](main.py)) — KV-биндинги
типа `app.theme_config["font_color"]` пересчитываются при смене темы. Переключение
идёт через `app.apply_theme(theme, mode)` — он грузит JSON, реассайнит property
(чтобы dispatch event firенулся), сохраняет выбор в `config/user.json`.

При старте `build()` читает сохранённую тему из `config/user.json` и применяет её
сразу — dark mode выживает рестарт.

## Hardware (Pi 5)

- **Display:** 1024×600 touch
- **Сенсоры:** ENS160 (CO2/TVOC) @ I2C 0x53, AHT21 (temp/humidity) @ I2C 0x38
- **GPIO:** не используется в текущей версии (LDR/volume buttons вырезаны вместе с 1.0.x)

## TODO

См. [_docs/AUDIT_FINDINGS.md](_docs/AUDIT_FINDINGS.md) — оставшиеся пункты для
следующих заходов (визуал, фичи, perf на Pi5).
