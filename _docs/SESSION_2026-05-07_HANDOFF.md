# Bedrock 2.0 — Session handoff 2026-05-07

Закрываю сессию, в которой Bedrock 2.0 финализировался и обзавёлся
веб-админкой. Pi на `7d9c2ec`, всё запушено в `origin/ui-rewrite`,
тег `v2.0.0`.

## TL;DR

- v2.0.0 запушен (тег + ui-rewrite ветка). Pure Kivy, единая 8dp сетка,
  две темы × light/dark, OverflowColumn auto-scroll, web admin на :8080,
  global touch-bounce filter.
- Pi (192.168.68.69) на ветке ui-rewrite, оба сервиса active:
  - `bedrock.service` — Kivy панель
  - `bedrock-admin.service` — Flask на :8080
- На клине светлой темы все 6 экранов проходят без overflow / cropping.
- Touch проблема ILITEK+MTD (моргание кнопок без перехода) решена
  глобально через `_BounceFilter` mixin в `classes/themed.py`.

## Что сделано в эту сессию

| Коммит | Что |
|---|---|
| `c331c6d` | gitignore `media/ringtones/*.wav` (mp3 источник, wav на Pi) |
| `9b82588` | Восстановили minecraft/light overlay+background PNG из 1.0.x |
| `7d37706` | **Phase 1+2:** `ui_metrics ↔ theme.layout` + semantic font_sizes (section_title/field_label/metric_value) + `themes/_template/` skeleton + README schema reference |
| `b38813f` | weather.kv пилот на ui_metrics |
| `4b13416` | minecraft/light `panel_bg` alpha 0.25 → 0.55 |
| `c5b9f71` | minecraft/dark `panel_bg` alpha 0.7 → 0.85 |
| `40bc94c` | **Phase 3:** home/alarm/schedule/pigs/settings.kv мигрированы на `app.ui_metrics` + унифицированы size_role |
| `6208ade` | `ScreenOverlay`: `overlay_opacity` (default 0.5) — приглушает декорацию под текстом |
| `afdeb52` | **OverflowColumn** — vertical BoxLayout drop-in с auto-scroll. Применён к weather/schedule/alarm/settings |
| `3e4d602` | weather top row 0.45 → 0.65 — sensors panel физически не помещался |
| `3dd43f3` | **BRANDBOOK.md** — полный гайд по созданию новых тем (~540 строк) |
| `058924b` | **Web admin** — Flask + werkzeug auth, 6 страниц + actions, systemd unit на :8080 |
| `7d9c2ec` | **Global touch-bounce filter** — `_BounceFilter` mixin для ThemedButton/ThemedToggleButton |

## Текущее состояние Pi

- IP `192.168.68.69`, hostname `bedrock`, user `pi`, ssh-key `~/.ssh/id_kidpager`
- Trixie (Debian 13), Pi 5 8GB, Python 3.13.5
- Uptime последняя проверка ~2.5 дня, temp 50°C, диск 7.5/118GB
- Сенсоры I2C 0x38 (AHT21) + 0x53 (ENS160) — реальные данные
- Audio через `pw-play` (pipewire-pulse), без zombies
- Тема в `config/user.json`: `clean` light с `auto_dark_mode=True`

## Web admin (новое)

`http://192.168.68.69:8080` — Flask app на отдельном `bedrock-admin.service`.

Bootstrap пользователя:
```bash
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "cd /home/pi/bedrock_3_0 && venv/bin/python -m admin.cli set-password admin"
```

Текущий тест-пароль на Pi: `bedrock_admin_2026` — **обязательно поменять**.

Что есть:
- Dashboard: service status, theme, alarm, weather, **live screenshot экрана**
  + 6 кнопок переключения экранов
- /themes: theme + light/dark + auto_dark_mode picker
- /alarm: time / days / ringtone / fade-in
- /schedule: raw JSON editor (на потом — grid UI)
- /pigs: слайдеры water/food/clean
- /settings: username, birthdate, lat/lon
- POST /actions/restart, /actions/screenshot, /actions/screen/<name>

Все формы пишут в те же `config/*.json` что Bedrock читает — атомарно
(`tempfile + os.replace`), Bedrock не словит half-written file.

## Что НЕ сделано / на потом

- **Schedule grid editor** в админке (сейчас только raw JSON)
- **Theme editor** — поменять цвета/font_sizes из UI без редактирования JSON
- **Live logs** в админке (streaming endpoint для journalctl)
- **CSRF tokens** на POST формы
- **Загрузка PNG ассетов** через UI (background, overlays, button graphics)
- **Smoke test runner** в deploy.sh для admin (сейчас только bedrock import)
- **mp3 → wav конвертер** в deploy.sh для ringtones (сейчас .wav кладёт юзер)

## Гид по новой теме

См. [themes/_template/BRANDBOOK.md](../themes/_template/BRANDBOOK.md) — полная
дизайн-философия + step-by-step "build a forest theme" tutorial + validation
checklist. Schema reference — `themes/_template/README.md`.

Короткий путь:
```bash
cp -r themes/_template themes/forest
mkdir themes/forest/{light,dark}
mv themes/forest/theme.json themes/forest/light/theme.json
cp themes/forest/light/theme.json themes/forest/dark/theme.json
# редактируй colors/font_name; кидай background.png + overlay_*.png в каждую папку
# Settings → Theme в Bedrock или /themes в админке — новая тема появится в списке
```

## Подводные камни (запомни)

- **Touch bounce.** ILITEK + MTD иногда выдаёт два touch sequence на один тап.
  Глобально пойман в `_BounceFilter`, 300ms окно. Если где-то button "моргает,
  но не реагирует" — проверь что класс наследует ThemedButton/ThemedToggleButton,
  а не голый Button.
- **`text_size: self.size` + крупный font.** На clean theme секционные
  заголовки (30sp) обрезались в `widget_height_md` (48dp). Use `widget_height_lg`
  для headings.
- **OverflowColumn** routing: `add_widget`/`clear_widgets` форвардятся на
  внутренний BoxLayout, но KV ids сидят на оригинальных дочерних виджетах
  (Kivy сканирует всё дерево). `self.ids.today_label` находит как раньше.
- **panel_bg alpha vs overlay_opacity** — два разных рычага. Поднял panel_bg
  alpha → панель плотнее. Уменьшил overlay_opacity → артворк глуше под всеми
  панелями. Вместе они перекрывают читаемость.
- **Admin secrets.** `config/admin.json` в gitignore. Каждая инсталляция
  bootstrap'ит свой через CLI. Дефолтный пароль на Pi сейчас слабый — поменять.
- **deploy.sh** сейчас рестартует **оба** сервиса при любом push'е. Если меняешь
  только KV/admin templates — это OK (быстро). Если хочешь только admin —
  `systemctl --user restart bedrock-admin.service` руками.

## Команды-чит-лист

```bash
# Деплой после правок
cd /c/_PROJECTS/Bedrock_2.0 && scripts/deploy.sh

# Логи Bedrock в реалтайме
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "sudo journalctl _SYSTEMD_USER_UNIT=bedrock.service -f"

# Логи admin в реалтайме
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "sudo journalctl _SYSTEMD_USER_UNIT=bedrock-admin.service -f"

# Рестарт только админки
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "systemctl --user restart bedrock-admin.service"

# Скриншот текущего экрана панели
WID=$(ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool getactivewindow")
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority timeout 6 import -window $WID /tmp/s.png"
scp -i ~/.ssh/id_kidpager pi@192.168.68.69:/tmp/s.png cache/s.png

# Цикл по 6 экранам через F-keys
WID=$(ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
  "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool getactivewindow")
for i in 1 2 3 4 5 6; do
  ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
    "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool key --window $WID F$i"
  sleep 1
  ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 \
    "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority timeout 6 import -window $WID /tmp/scr_$i.png"
done

# Локальный smoke (Windows)
cd /c/_PROJECTS/Bedrock_2.0 && timeout 7 venv/Scripts/python.exe main.py
# Admin локально
cd /c/_PROJECTS/Bedrock_2.0 && venv/Scripts/python.exe -m admin.server
# → http://localhost:8080
```
