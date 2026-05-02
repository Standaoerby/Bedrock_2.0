# Audit findings — что осталось

Срез на ветке `recovery-from-0.8.2` после трёх восстановительных коммитов.
Сгруппировано по приоритету, с file:line ссылками. Что фикс`ить — реши,
исходя из того, какие проблемы реально проявляются на железе.

## Visual / UI (требуют тестирования на 1024×600)

Не правил без живой проверки на Pi5 — на десктопе в окошке масштаб другой,
есть риск сделать хуже.

- **`pages/alarm.kv:17`** — `size_hint: 0.9, 0.8` + `pos_hint: center_y: 0.48`.
  Внутренний BoxLayout стэк секций (96+48+48+64+48 dp + spacing 64 ≈ 368 dp),
  при контейнере ~408 dp. Близко к границе, особенно с `font_scale > 1`.
  Save button может пересекаться с верхним меню.
- **`pages/schedule.kv:17,244`** — `size_hint: 0.9, 0.75` + toggle button
  `center_y: 0.08`. Возможный overlap по нижнему краю.
- **`pages/weather.kv:155-161`** — хардкод
  `Color: rgba: [0.15, 0.15, 0.15, 0.3]` для панели — обходит тему, в обоих
  режимах одна и та же тёмно-серая подложка.
- **`pages/weather.kv:53`** — `color: ... if float(self.text.split('°')[0]) < 15`.
  Если text станет чем-то без `°` (например `"N/A"`), KV крашит силент.
  Нужен safe parse.
- **`pages/settings.kv:60`** — текст "Dark Mode (9PM-7AM)" — врёт, никакого
  расписания нет, тогл ручной. Заменить на просто "Dark Mode".

## Bugs (low/medium priority, не блокируют)

- **`pages/pigs.py:59`** — `print()` debug в цикле каждые 20 минут. На Pi
  забивает journald. Заменить на logger.debug.
- **`pages/alarm.py:42-44`** — пустой `ringtone_list` + selected_ringtone не
  существует → silent fail при play.
- **`services/weather_service.py:218`** — `data["hourly"]["precipitation_probability"][0]`
  может оказаться `None` (Open-Meteo иногда возвращает null), потом крашит
  KV биндинг на home.
- **`services/sensor_service.py`** — нет readiness-сигнала. Если решим вернуть
  auto-theme — нужен event "sensor ready" чтобы не читать дефолт.
- **`main.py: app.play_sound`** — каждый play создаёт `SoundLoader.load(sound.source)`
  заново, плюс `Clock.schedule_once(... sound.length + 0.1)` накапливает
  колбэки. На рапид-кликах memleak. Минорно, но есть.

## Pi5-specific (проверить на железе)

- **kivymd 1.2.0 deprecation warning** — kivymd >=2.0 переехал классы. Если
  захотим обновиться, надо будет менять `from kivymd.uix.screen import MDScreen`
  на новый путь.
- **`requirements.txt`** — `adafruit-blinka` нужен для `import board, busio`.
  На Pi должен быть `python3-blinka` через apt; pip-версия тоже работает,
  но требует прав I2C (`sudo usermod -aG i2c $USER`).
- **AlarmPopup** — использует `pygame` напрямую (через kivy.core.audio.SoundLoader).
  Если на Pi5 audio backend gstreamer/SDL2 — звук может стартовать с задержкой
  1-2 сек. Проверить на боевом железе.
- **Touch input** — на 0.8.2 не было особых настроек для touchscreen. Если
  есть проблемы со scroll/долгим нажатием — добавить `Config.set("input", ...)`.

## Архитектурные смутности (refactor opportunities)

- **`pages/*.py:get_app()`** — каждый файл импортирует App локально, дублируется.
  Можно вынести в общий `utils/app.py` (но это будет тащить за собой `utils/`).
- **Темы хардкодят пути PNG** — `themes/minecraft/light/background.png` и т.п.
  Если когда-нибудь добавим вторую тему — тяжело будет рефакторить пути.
- **`config/user.json`** — schema не валидируется. Можно добавить лёгкий
  pydantic/jsonschema чек.
- **Нет тестов** — `_tests/` папки нет, smoke-тесты делал inline в bash.
  Минимум полезен `pytest test_theme.py` — проверка load + apply theme.

## Фичи на потом (нужно решение)

- **systemd unit для autostart** на Pi.
  ```
  [Unit]
  Description=Bedrock 2.0
  After=graphical.target
  [Service]
  ExecStart=/path/to/venv/bin/python /path/to/main.py
  WorkingDirectory=/path/to/Bedrock_2.0
  Restart=on-failure
  User=standa
  [Install]
  WantedBy=graphical.target
  ```
- **Auto-theme by sunset/sunrise** — если LDR не возвращать, можно сделать
  по часам через astral lib. Локация уже есть (Лондон/Камден).
- **Volume buttons GPIO** — если физические кнопки нужны, делать через
  `gpiozero.Button(23)` и `pygame.mixer` — короче и надёжнее, чем lgpio low-level.
- **Dark theme — нет ручного перевода всех PNG** — overlay картинки
  `themes/minecraft/dark/overlay_*.png` существуют, но визуально проверить
  на Pi5 не лишне.
