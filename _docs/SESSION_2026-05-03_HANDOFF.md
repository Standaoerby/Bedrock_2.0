# Bedrock 2.0 — Handoff 2026-05-03

Сессия закрыта поздно ночью. Stan ушёл спать. Это конспект чтобы утром
не вспоминать с нуля.

## TL;DR

- Бекенд **готов**: ветка `recovery-from-0.8.2` (17 коммитов от 0.8.2), всё запушено в `origin`. Sensors реальные, alarm срабатывает, weather фетчится, deploy скрипты work, audio через ffpyplayer.
- UI **в кашe**: visual каждый раз ломается после очередного патча. Согласован план A — переписать на чистом Kivy без kivymd.
- Ветка `ui-rewrite` создана пустая от `recovery-from-0.8.2`. Завтра туда.
- Memory leak monitor крутится в фоне (background task `b6hrb7m6e`), пишет в `cache/monitor.log` каждые 25 мин, итого 4 точки за ~2 часа. Нотификация прилетит — глянуть утром.

## Где какая ветка

```
ui-rewrite                     ← пустая, завтра туда
recovery-from-0.8.2  → origin  ← всё стабильное, fallback
65164b2 (0.8.2)      ← база, бывший pi/main
origin/main          → "Soso"  ← мёртвый 1.0.x, не трогать
```

## Pi state на момент handoff

- IP `192.168.68.69`, hostname `bedrock`, user `pi`, ssh-ключ `~/.ssh/id_kidpager`
- Trixie (Debian 13), Pi 5 8GB, Python 3.13.5
- `bedrock.service` autostart enabled, X11 fullscreen 1024×600
- temp 49°C, throttled 0x50000 (под-voltage в прошлом, БП слабоват, без active throttling), 7GB/118GB
- WiFi OK, NTP synced, ping 8.8.8.8 + github OK
- I2C 0x38 (AHT21) + 0x53 (ENS160) — Climate показывает реальные данные
- Audio: pipewire+wireplumber active, `KIVY_AUDIO=ffpyplayer`, `SDL_AUDIODRIVER=pulse`, sounds mono 48kHz wav

## Что переписываем (план A — pure Kivy)

**Зачем:**
- KivyMD 1.2 deprecated, в каждый log warning
- `<ThemedLabel@Label>` template binds `color: app.theme_config["font_color"]` — перетирает per-instance overrides. Это корень shadow-white-on-dark и других подобных багов
- main.py в build() мутирует `theme_config["font_sizes"]` in-place — theme.json игнорируется на Pi
- pages/*.kv: hardcoded font sizes вперемешку с theme lookups, overlay block дуплицирован 6 раз, layouts overlap'ят на 1024×600
- scale_size/scale_font с ui_scale=0.9 на Pi работает непредсказуемо

**Цели:**
- `App` вместо `MDApp`, `ScreenManager` вместо `MDScreenManager`
- Свои `ThemedLabel/Button/Panel` БЕЗ binding color в правиле — color через per-instance default или `color_role` property
- Базовый `BaseScreen(Screen)` — overlay layer + cleanup общий
- `<ScreenOverlay@Image>` reusable rule (одно место вместо 6)
- Всё из theme.json через `.get(key, default)`, никаких hardcoded color/size в KV
- Layouts проектируем под нативные 1024×600 (не масштабируем)
- Каждый `pages/<name>.kv` self-contained, единая структура

**Что НЕ трогаем (стабильно):**
- `services/` — alarm_service, alarm_clock, weather_service, schedule_service, pigs_service, notifications_service, sensor_service
- `classes/alarm_popup.py` (ModalView, popup открывается, ringtone играет)
- `classes/marquee.py` (Translate реализация без `clear()` per frame)
- `scripts/` — setup-pi.sh, deploy.sh, bedrock.service
- `themes/minecraft/{light,dark}/theme.json` — JSON ассеты
- `assets/sounds/*.wav` — mono 48k
- `config/*.json`

## Порядок шагов утром

1. **Запустить Plan agent** — попросил уже план, но был interrupted. См. бывший prompt — кратко: dependency check (что от kivymd используется), theme system design (как избежать binding war), file structure, migration order, 6 screen detailed plan, test strategy, risks.
2. Получить детальный roadmap.
3. Реализовать base — main.py minimal + new ThemedWidget classes + main.kv.
4. **Home как pilot** — переписать целиком, deploy на Pi, визуально проверить.
5. Если Home OK по визуалу — продолжать остальные 5 экранов.
6. Если что-то не так — поправить в base, не патчить.

## Подводные камни (запомни)

- **ThemedLabel template binding** — НЕ binds color в `<ThemedLabel@Label>:`. Если color должен быть из темы — делать через explicit `color: app.theme_config.get(...)` per-instance, или color_role mechanism.
- **MDScreen `on_pre_enter` semantics** vs vanilla `Screen` — могут отличаться. Проверить что `on_pre_enter`/`on_leave` работают одинаково.
- **`Window.fullscreen`** — Config.set должна быть ДО `from kivy.core.window import Window`. Уже сделано в main.py — НЕ ломать порядок.
- **Theme switching** — `theme_config` это `DictProperty`, бинды re-evaluate когда переприсваивается dict. `dict.update()` — НЕ fires event, нужен реассайн.
- **F1-F6 dev shortcuts** — есть в `on_start` для быстрого переключения экранов в headless tests.
- **`use_kivy_settings = False`** в App — без этого F1 откроет Kivy-built-in Settings panel.

## Pi-deploy специфика

- `setup-pi.sh` запускать только однажды (или после wipe SD). Прокидывает SSH-ключ через plink, ставит apt deps, делает venv с `--system-site-packages`, ставит systemd unit.
- `deploy.sh` — для каждого push. Авто-sync `bedrock.service` если он изменился в repo (после фикса в `a3959f6`). Smoke test перед restart, rollback при fail.
- Логи: `sudo journalctl _SYSTEMD_USER_UNIT=bedrock.service -f` (Trixie user-scope журнал по дефолту пустой).
- Для теста кликов — `xdotool key --window <WID> F1..F6` (F1=home, F2=alarm, F3=schedule, F4=weather, F5=pigs, F6=settings). Получить WID через `xdotool getactivewindow`.
- Pi panel + pcmanfm respawn'ятся после reboot — для true kiosk добавить `ExecStartPre=/usr/bin/pkill -f "lxpanel|pcmanfm.*--desktop"` в unit (не сделано пока).

## Memory monitor — что смотреть утром

Файл `cache/monitor.log` — 5 snapshots (T+0, +25, +50, +75, +100 min):
- **RSS rost** — если >10MB за 100 минут → утечка осталась
- **CPU avg** — должно быть ~3%, если >10% — что-то крутит
- **warn count last 30m** — если растёт между точками → новые ошибки появляются
- **temp** — должно быть 45-55°C, >70 — overheating
- **mmc errors** — если >0 → SD card проблемы

Если всё в норме — фиксы памяти/perf работают (Home interval cancel, marquee Translate, sensor logger.debug, play_sound reuse), переходим к UI rewrite.

Если RSS течёт — найти источник через `py-spy` или `tracemalloc` snapshot.

## User feedback (из сегодня)

- Прямой стиль, без воды. Когда patch over patch не работает — сразу framing "это не работает" + 3-4 numbered options + рекомендация. Не ждать разрешения, делать предложение, дать выбрать.
- Когда выбирает rewrite — кратко подтвердить план и стартовать.
- На фотках/скринах ловит мелочи — преview уменьшенный, я могу пропустить детали. Перепроверять в zoomed crop.
- "На сладкое" = на потом. "Ебашь" = делай сразу.

## Open questions для утра

- Какие именно visual проблемы у пользователя на физическом экране что не видно мне? Нужно сфоткать на телефон или описать словами по экранам.
- Хочет ли true kiosk (lxpanel + pcmanfm killed)? Есть ли использование desktop-mode когда не bedrock?
- KivyMD 1.x → 2.x migration — нужен в этом цикле или можно отложить навсегда (мы дропаем kivymd целиком в плане A).

## Команды-чит-лист

```bash
# Деплой после правок
cd /c/_PROJECTS/Bedrock_2.0 && scripts/deploy.sh

# Логи в реальном времени
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 "sudo journalctl _SYSTEMD_USER_UNIT=bedrock.service -f"

# Рестарт сервиса
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 "systemctl --user restart bedrock"

# Скриншот текущего экрана Bedrock
ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority timeout 6 import -window \$(DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool getactivewindow) /tmp/s.png"
scp -i ~/.ssh/id_kidpager pi@192.168.68.69:/tmp/s.png cache/s.png

# Цикл по 6 экранам через F-keys
WID=$(ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool getactivewindow")
for i in 1 2 3 4 5 6; do
  ssh -i ~/.ssh/id_kidpager pi@192.168.68.69 "DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority xdotool key --window $WID F$i; sleep 1; DISPLAY=:0 XAUTHORITY=/home/pi/.Xauthority timeout 6 import -window $WID /tmp/scr_$i.png"
done

# Локальный smoke (Windows)
cd /c/_PROJECTS/Bedrock_2.0 && timeout 7 venv/Scripts/python.exe main.py
```
