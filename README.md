# Bedrock 2.0

Мультимедийная панель управления для Raspberry Pi 5 с touchscreen 1024×600.
Часы, будильник, погода, расписание, трекер ухода за свинками. Pure Kivy 2.3
(без kivymd), две темы (`minecraft` + `clean`) × light/dark, mock-сенсоры на
Windows для разработки. Веб-админка на отдельном Flask-сервисе.

## Текущая версия

- **`v2.0.0`** на ветке `ui-rewrite` — полный rewrite UI с 0.8.x на pure Kivy,
  единая 8dp-сетка через `app.ui_metrics`, две темы с light/dark, OverflowColumn
  для авто-скролла переполняющихся контейнеров, веб-админка на `:8080`.
- **`recovery-from-0.8.2`** — fallback с рабочим бэкендом на kivymd, не трогаем.
- **`origin/main`** — старый "Soso" 1.0.x, заброшен.

## Pi

- **IP:** `192.168.68.69` (`pi@bedrock`, ssh-key `~/.ssh/id_kidpager`)
- **Repo path:** `/home/pi/bedrock_3_0`
- **Сервисы:**
  - `bedrock.service` — Kivy панель, fullscreen X11, систем audio через `pw-play`
  - `bedrock-admin.service` — Flask на `:8080`, веб-админка
- **OS:** Trixie (Debian 13), Pi 5 8GB, Python 3.13

## Запуск (dev)

```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
python main.py            # Kivy панель (windowed на Windows, fullscreen на Pi)
python -m admin.server    # Flask админка на http://localhost:8080
```

Сенсоры автоматически на mock на Windows. Перед первым запуском админки:

```bash
python -m admin.cli set-password admin
```

## Деплой на Pi

```bash
scripts/deploy.sh
```

push'ит ветку → fetch на Pi → rsync конфигов → re-install requirements при их
изменении → переустановка systemd unit'ов → smoke test → restart обоих сервисов
(rollback при failure). Всё в одной команде.

## Структура

```
main.py            — точка входа, BedrockApp(App)
main.kv            — корневой layout, MenuButton rule
pages/             — экраны: home, alarm, schedule, weather (Climate), pigs, settings
services/          — alarm/weather/schedule/pigs/sensor/notifications
classes/
    themed.py        — ThemedLabel/Button/Spinner/Panel + ScreenOverlay + ShadowLabel
                       + _BounceFilter mixin (touch debounce для ILITEK + MTD)
    overflow.py      — OverflowColumn (drop-in BoxLayout vertical с auto-scroll)
    marquee.py       — scrolling notification strip
    alarm_popup.py   — modal alarm fire-time popup
    audio_player.py  — pw-play обёртка для Pi
    base_screen.py   — общий каркас экрана
themes/
    minecraft/       — пиксельный стиль, оверлеи (волки/свинки)
    clean/           — современный, без оверлеев
    _template/       — пустой шаблон + README.md (схема) + BRANDBOOK.md (гайд)
config/            — user/alarm/schedule/pigs.json (admin.json в gitignore)
admin/             — Flask web UI (server.py, cli.py, templates/, static/)
scripts/           — deploy.sh, setup-pi.sh, *.service systemd units
assets/            — шрифты (Minecraftia, DejaVuSans=Symbols), звуки, картинки
media/ringtones/   — .mp3 (commited) → .wav (производные, на Pi)
_docs/             — заметки, handoffs, аудит
```

## Темы и сетка

`theme.json` ↔ `app.ui_metrics` (DictProperty с полным `theme.layout`)
↔ KV (`app.ui_metrics["padding_md"]`). Один источник правды для отступов.

- Сетка: 8dp (`grid_unit`), padding/spacing `xs=4 sm=8 md=16 lg=24`,
  widget heights `sm=32 md=48 lg=64`.
- Семантические font roles: `section_title`, `field_label`, `metric_value`
  (плюс канонические `tiny..huge`).
- Оверлеи диммируются глобально через `theme.overlay_opacity` (default 0.5).

Полный гайд по созданию новой темы — [themes/_template/BRANDBOOK.md](themes/_template/BRANDBOOK.md).
Схема ключей — [themes/_template/README.md](themes/_template/README.md).

## Админка (web UI)

`http://192.168.68.69:8080` после `bedrock-admin.service` запущен. Логин
admin/<password> (bootstrap через `python -m admin.cli set-password`).

Страницы: dashboard (статус + live screenshot + screen-cycle кнопки), themes,
alarm, schedule (raw JSON пока), pigs, settings. Actions: restart Bedrock,
переключить экран, screenshot.

Всё пишется в те же `config/*.json` что Bedrock читает — изменения
подхватываются на следующем poll'е или после `Restart Bedrock`.

## Hardware (Pi 5)

- **Display:** 1024×600 touch (ILITEK + Kivy MTD provider)
- **Сенсоры:** ENS160 (CO2/TVOC) @ I2C 0x53, AHT21 (temp/humidity) @ I2C 0x38
- **Audio:** pipewire/pulse через `pw-play` (sdl2 audio висит на Trixie)

## Touch quirks

ILITEK + MTD иногда генерирует два touch sequence на один физический тап
("моргает кнопка, переход не происходит"). `_BounceFilter` mixin в
`classes/themed.py` глобально проглатывает второй `touch_down` в течение
300ms — закрывает все ThemedButton/ThemedToggleButton разом.
