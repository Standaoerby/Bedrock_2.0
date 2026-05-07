# Migration: 0.5.5 → 2.0 (восстановление утерянных фич)

**Status:** v2.1.0 (uncommitted). Code review pass + 6 fixes applied. Готово к деплою на Pi.
**Started:** 2026-05-07. **Finished:** 2026-05-08.

## Code review pass (2026-05-08)

После завершения 5 этапов прошёл независимый review через subagent.
Найдено и исправлено 6 пунктов:

1. **GPIO factory pinning** (HIGH) — `main.py:build()` теперь явно ставит
   `Device.pin_factory = LGPIOFactory()` на Pi до того, как сервисы
   создают gpiozero devices. Это устраняет race при разном порядке
   инициализации SensorService (LDR на 12) и VolumeService (Buttons
   23/24) — оба теперь используют один и тот же process-shared chip
   handle. Также: `sensor_service.py` переписан с raw `lgpio` на
   `gpiozero.DigitalInputDevice` чтобы делить factory с volume.
2. **`AlarmPopup.on_snooze` direct assignment** (LOW) — добавлен
   комментарий, что это одиночный subscriber через прямую запись (не
   через Kivy property dispatch). Если когда-нибудь нужны несколько —
   переписать на `bind(on_snooze=...)`.
3. **`migrate_user_config` merge direction** (LOW) — добавлен
   комментарий, что `existing.update(user_patch)` означает: 0.5.5
   ключи overrid'ят 2.0 для общих ключей, 2.0-only keys
   (`temp_offset`, etc) сохраняются.
4. **"Birthday" vs "Birth Date"** (LOW) — KV fallback приведён к
   значению из locale (`"Birthday"`).
5. **`hasattr(app, "user_prefs")`** (LOW) — убран лишний defensive
   check в `auto_theme_service.py`.
6. **Silent sound load failures** (MEDIUM) — `print(...)` заменён на
   `logger.warning(...)` в `main.py:load_sounds()`. Теперь missing
   звуки будут видны в `journalctl` на Pi.

Финальный смок: чистый Kivy boot, никаких ERROR/Traceback, все
сервисы стартуют (`sensor service started`, `auto-theme strategy
set: ldr`, `volume service started (backend=cache, buttons=off)`).
**Source of truth (old):** `C:\_PROJECTS\bedrock.old\bedrock-app` — git `main`,
последний коммит `0dbec61 переехали на ноут`, цепочка тегов 0.5.0 → 0.5.5.
**Target (current):** `C:\_PROJECTS\Bedrock_2.0` — `ui-rewrite` `v2.0.0`.

## TL;DR

Stan нашёл реальный финал 0.5.5 — это та ветка, в которой "всё ещё работало
до того, как всё разъебали" (cm. [`cb03d0b`](../bedrock.old/bedrock-app):
«0.5.5 Stable. Последний коммит перед тем, как всё разъебать»). Ранее в
[RECOVERY.md](RECOVERY.md) описана история 1.0.x → 0.8.2 fallback и
последующего ui-rewrite — но тот recovery шёл с `0.8.2` baseline, а 0.5.5
содержала фичи, которые в 0.8.2 уже отсутствовали и в ui-rewrite не были
восстановлены: **i18n, auto-theme, volume control, snooze, light sensor,
welcome notification**.

Решение — гибридный port:
- ядро 2.0 не трогаем (ui_metrics, web admin, deploy.sh, BaseScreen,
  themed.py, OverflowColumn, BounceFilter — реальные улучшения);
- из 0.5.5 берём **смысл фич**, не код. Перенесим только ассеты дословно,
  всё остальное — переписать поверх архитектуры 2.0.

Полный кросс-дифф файлов сохранён в memory:
[`bedrock_old_vs_2_0_audit.md`](file:///C:/Users/Standa/.claude/projects/C--Users-Standa-OneDrive----------/memory/bedrock_old_vs_2_0_audit.md).

## Что потеряно (lost features inventory)

| Фича | 0.5.5 (откуда брать смысл) | 2.0 (куда добавляется) | Сложность |
|---|---|---|---|
| i18n (en/ru) | `app/localizer.py`, `locale/{en,ru}.json` | новый `app/i18n.py` + `tr()` helper в `BedrockApp`; KV использует `app.tr("key")` | M |
| EventBus | `app/event_bus.py` (~40 LoC) | новый `app/events.py`, обёртка над Kivy `EventDispatcher` или collections | S |
| Auto theme | `services/auto_theme_service.py` (LDR digital read) | переписать с двумя стратегиями: **LDR на GPIO 12** (primary, как в 0.5.5) и `astral` sunrise/sunset (fallback/option). Выбор через `user.json: auto_theme_strategy: "ldr"\|"astral"\|"off"` | M |
| Volume control | `services/volume_service.py` (amixer + GPIO 23/24) | переписать на pipewire (`wpctl set-volume @DEFAULT_AUDIO_SINK@ N%`); GPIO опционально (см. open question) | M-L |
| Snooze | `services/alarm_clock.py:snooze_alarm(minutes)` | добавить snooze в `services/alarm_clock.py` + кнопка в `classes/alarm_popup.py` | S |
| Light sensor | `services/sensor_service.py:_read_light_sensor` (GPIO 12, digital, pull-up) | **возвращаем** — железо есть. Smoothing на 4 reading'ах + `calibrate_light_sensor(threshold_seconds)` как в 0.5.5, но без отдельного threading.Thread (через `Clock.schedule_interval` как `alarm_clock.py`) | M |
| Audio Bonnet HAT | `services/audio_service.py` (pygame + ALSA detection) | **не возвращать** — на Pi 5 / Trixie pipewire через `pw-play` уже работает (см. main.py:201) | — |
| Welcome notification + startup sound | `main.py:_on_startup_complete` | в `BedrockApp.on_start()`: `notification_service.add(welcome)` + `play_sound("startup")` | S |
| Settings: language picker | `pages/settings.py` | добавить SelectButton (ru/en) | S |
| Settings: auto-theme toggle | `pages/settings.py:toggle_auto_theme` | toggle (привязан к `auto_dark_mode` в user.json — admin уже его пишет) | S |
| Settings: volume +/- | `pages/settings.py:volume_up/down` | кнопки + value label, привязка к новому volume сервису | S |
| `confirm.ogg` + `startup.ogg` | `themes/minecraft/sounds/` | положить в `assets/sounds/` (.ogg + .wav) | S |
| `overlay_default.png` | `themes/minecraft/{light,dark}/` | положить в `themes/minecraft/{light,dark}/` для fallback экранов | S |

**Ассеты — берутся дословно** из старой ветки (overlays, backgrounds, цвета
в `theme.json` → правильные). Код — **переписать**, сохранив суть.

## Что НЕ трогаем (есть только в 2.0, оставляем как есть)

`app.ui_metrics` (DictProperty mirror of `theme.layout`), `OverflowColumn`,
`MarqueeLabel`, `_BounceFilter`, `clean` тема + `_template` + `BRANDBOOK.md`,
Flask web admin на :8080, `pw-play` через subprocess, `scripts/deploy.sh`,
`BaseScreen`, `_jsonstore.py`, sensor calibration (temp_offset/humidity_offset),
F1–F6 keyboard shortcuts, шрифты через `LabelBase`.

## План по этапам

Каждый этап — отдельный PR. Деплой/смоктест после каждого, мерж в
`ui-rewrite`. Если что-то ломается — откат одного PR, не всей серии.

### Этап 1 — инфра (`app/` skeleton) ✓ done 2026-05-07

- [x] `app/events.py` — `EventBus` (pub/sub, RLock, snapshot subscribers
      under lock so callbacks can subscribe/unsubscribe safely)
- [x] `app/i18n.py` — `Translator` с `load(lang)`, `tr(key, default)`,
      en-fallback, `available_languages()`, `merged()` для DictProperty
- [x] `locale/en.json` + `locale/ru.json` — 66 ключей each (menu, settings,
      alarm, schedule, weather, pigs)
- [x] `BedrockApp` — `language: StringProperty`, `i18n_strings: DictProperty`,
      `set_language(lang, persist=True)`, `tr(key)`. Translator init в
      `build()` сразу после `_refresh_ui_metrics`, до загрузки `main.kv`
      (иначе MenuButton text был бы blank-then-pop)
- [x] `main.kv` — 5 MenuButton'ов (Home/Alarm/School/Climate/Pigs)
      теперь читают `app.i18n_strings.get("menu_X", "Default")`. Settings
      кнопка остаётся `>` (это иконка, не label)
- [x] `_persist_user_pref(key, value)` — generic helper в BedrockApp,
      использован для language; для theme остаётся специализированный
      `_persist_theme_choice` (исторический)
- [x] `set_language` публикует `event_bus.publish("language_changed", ...)`

**Acceptance:** ✓ smoke test прошёл — Kivy main loop стартует без ошибок,
i18n инициализируется (`[INFO ] [locale loaded] en (66 keys)` в логе).
Language switch без рестарта работает потому что DictProperty
`i18n_strings` reassigned → KV bindings re-evaluate.

**Не сделано в этом этапе (отложено в Этап 5):**
- Перевод строк в `pages/settings.kv` — settings page всё равно будет
  пересобираться в Этап 2 (добавление auto-theme strategy selector) и
  Этап 3 (volume controls). Логичнее перевести вместе с переделкой UI.
- Welcome notification + startup sound — Этап 4
- `config/user.json` schema bump для `language: "en"` default — будет
  записан в Этап 5 (migrate_user_config.py), сейчас читается через
  `user_prefs.get("language", "en")`

### Этап 2 — auto-theme (LDR + astral) ✓ done 2026-05-08

LDR на BCM 12 (digital, pull-up; `0=light`, `1=dark`).

- [x] `services/sensor_service.py` — добавлены `read_light_level()`,
      `_init_ldr()` (lgpio → RPi.GPIO → MockLDR fallback), smoothing buffer
      на 4 sample'а с majority vote, `get_light_status()` для UI. На
      Windows автоматически идёт через `MockLDR` (06:00–22:00 = light).
- [x] `services/mock_sensors.py` — добавлен `MockLDR.read_digital()` +
      `set_override(True/False/None)` для dev-тестинга.
- [x] `services/auto_theme_service.py` — новый сервис со strategy pattern
      (`OffStrategy`/`LDRStrategy`/`AstralStrategy`). Никакого собственного
      `threading.Thread` — всё через `Clock.schedule_interval` на Kivy
      main thread, чтобы не повторить GPIO double-claim race из 1.0.x
      (см. [RECOVERY.md](RECOVERY.md)).
  - LDR check каждые 2s, threshold N consecutive stable reads до flip
  - Astral check раз в минуту, кэш sunrise/sunset на сутки
  - `apply_theme(..., persist=False)` — auto switch не перезаписывает
    user manual choice в config
- [x] `requirements.txt` += `astral>=3.2` (установлен в venv).
- [x] `main.py` — `BedrockApp.auto_theme_service` инициализируется в
      `build()`. Strategy резолвится из `user.json: auto_theme_strategy`,
      fallback на legacy `auto_dark_mode: bool` (true → `"ldr"`,
      false → `"off"`). Threshold из `light_sensor_threshold` (default 3).
      Stop в `on_stop`.
- [x] `pages/settings.py` — новые `auto_theme_strategy` (Spinner),
      `light_sensor_threshold` (TextInput), `auto_theme_status` (Label).
      Strategy spinner вызывает `change_auto_theme_strategy()` →
      `auto_theme_service.set_strategy()`. Live status обновляется через
      `BaseScreen.add_interval(refresh_auto_theme_status, 2)` (auto-cleanup
      на leave).
- [x] `pages/settings.kv` — добавлены два panel'а: Language picker
      (en/ru), Auto-theme (strategy spinner + threshold + status). Старые
      labels переведены через `app.i18n_strings.get(...)` (theme/dark
      mode/username/birthday/save).
- [x] `events.publish("auto_theme_strategy_changed", ...)` и
      `events.publish("theme_changed", ..., auto=True)` для подписчиков.

**Acceptance:**
- ✓ Smoke test: Kivy boot — `LDR using mock (day/night by hour)`,
  `auto-theme strategy set: ldr` (legacy `auto_dark_mode: true`).
- ✓ Unit: AstralStrategy для Camden (51.539, -0.1426) даёт корректные
  Sunrise 05:20 · Sunset 20:34 для мая, и в 00:00 локального времени
  возвращает `"dark"`.
- LDR strategy на Pi: накрытие сенсора рукой → панель уходит в dark
  в течение `threshold * 2` секунд (default ~6s) — **проверить руками**
  на Pi.
- Astral strategy: на закате панель сама уходит в dark — **проверить
  следующим вечером** на Pi.

### Этап 3 — volume control ✓ done 2026-05-08

GPIO кнопки 23/24 подключены, Audio Bonnet HAT снят.

- [x] `services/volume_service.py` — backend resolved at start():
  - `_WpctlBackend` → `wpctl set-volume @DEFAULT_AUDIO_SINK@ <0..1>` /
    `wpctl get-volume` (regex parse `Volume: 0.65`). Линукс с
    `shutil.which("wpctl")`.
  - `_CacheBackend` (Windows / no wpctl) — UI работает, system audio
    не трогается. amixer не возвращён, потому что Trixie ALSA это
    pipewire shim.
- [x] GPIO buttons через `gpiozero.Button(23 / 24, pull_up=True,
      bounce_time=0.2)`. `when_pressed = Clock.schedule_once(step_up/
      step_down)` — переход на main thread, чтобы не было race с UI.
      Опционально: если gpiozero не импортируется (Windows) или
      Button-init падает (нет железа) — service работает без кнопок.
      gpiozero на Pi 5 идёт через lgpio backend (его уже подняли в
      sensor_service) — без double-claim chip.
- [x] `requirements.txt` += `gpiozero; sys_platform == "linux"`
      (опциональный, не качается на Windows).
- [x] `main.py` — `volume_service.start()` после auto_theme,
      `volume_service.stop()` в `on_stop()`.
- [x] `pages/settings.py` — `current_volume: NumericProperty`,
      `volume_backend: StringProperty`, методы `volume_up`/`volume_down`/
      `refresh_volume_status`. Live refresh через
      `add_interval(refresh_volume_status, 1)`.
- [x] `pages/settings.kv` — Volume панель: лейбл `Volume:` + `−` /
      value label `NN%` / `+`. Использует `app.i18n_strings` для
      "Volume".
- [x] `event_bus.publish("volume_changed", {"volume": int, "source":
      "ui"|"up"|"down"|"external"})` для подписчиков.

**Step / Range:** 5%, 0..100. Internal poll каждые 5s — синхронизация
если громкость поменяли через admin UI или `wpctl` на shell'е.

**Acceptance:**
- ✓ Smoke: `volume service started (backend=cache, buttons=off,
  volume=50%)` на Windows без ошибок.
- На Pi после deploy: GPIO 23 (up) / 24 (down) меняют громкость через
  `wpctl`, значение видно в settings — **проверить руками**.
- На Pi: смена громкости через admin/web → значение в settings panel
  обновляется в течение 5s (poll interval) — **проверить руками**.

### Этап 4 — snooze + welcome + потерянные звуки ✓ done 2026-05-08

- [x] `assets/sounds/confirm.ogg` + `startup.ogg` скопированы из
      `bedrock.old/bedrock-app/themes/minecraft/sounds/`. `.wav` будут
      сгенерированы через deploy на Pi (`pw-play` любит `.wav` поверх
      pipewire).
- [x] `main.py:load_sounds()` — добавлены `confirm` + `startup` в реестр.
- [x] `main.py:on_start()` — `Clock.schedule_once(_fire_welcome, 1.2)`
      добавляет `notification_service.add(...)` с локализованным
      `"welcome_back"` (`{username}` подставляется из user.json) +
      `play_sound("startup")`. 1.2s деферр чтобы первый кадр успел
      отрисоваться до аудио.
- [x] `services/alarm_clock.py` — `snooze(minutes=5)`: отменяет
      in-flight snooze + закрывает popup + `Clock.schedule_once(_wake,
      minutes*60)`. `stop_alarm()` тоже убирает snooze. Ringtone и fadein
      берутся свежими из `alarm_service.get_alarm()` на момент snooze
      trigger (не закэшены — alarm config мог поменяться).
- [x] `classes/alarm_popup.py` — `on_snooze: ObjectProperty(None,
      allownone=True)` callback, кнопка `Snooze` рядом с `Turn Off`
      (50/50 split). `_snooze()` останавливает плеер, вызывает callback,
      dismiss'ит popup. Локализованные labels через
      `app.i18n_strings.get("alarm_snooze"/"alarm_dismiss", ...)`.
- [x] `AlarmClock.trigger_alarm()` устанавливает
      `popup.on_snooze = lambda: self.snooze(DEFAULT_SNOOZE_MINUTES)`
      перед открытием.

**Acceptance:**
- ✓ Smoke: app boots, welcome notification сохранилась в
  `config/notifications.json` (`"Welcome back, Anna-Maria!"`,
  `category=system`).
- На Pi: alarm popup → нажать Snooze → popup закрывается, через 5 мин
  снова открывается с тем же ringtone — **проверить руками**.
- На Pi: первый запуск slышен `startup.ogg` через 1–2s — **проверить
  руками** (нужно сгенерировать `startup.wav` на Pi через deploy).

### Этап 5 — assets + config migration ✓ done 2026-05-08

- [x] Сравнение overlay PNG (sha256 + size): **light уже byte-identical**
      (вся восьмёрка `light/{background,overlay_alarm,overlay_home,
      overlay_pigs,overlay_schedule,overlay_settings,overlay_weather}.png`).
      **Dark все 7 разные** — новые в 5–10× больше старых, явно из
      другого источника (вероятно 1.0.x при Recovery от 0.8.2). Заменены
      на 0.5.5 версии.
- [x] `themes/minecraft/light/overlay_default.png` скопирован из старой
      (fallback overlay для экранов без своего ключа). В dark/ старой
      его не было — оставлено отсутствующим.
- [x] `scripts/migrate_user_config.py` — `--dry-run` поддержка, key
      mapping (см. CHANGELOG):
  - `variant` → `theme_mode`
  - `birthday` → `birthdate`
  - `auto_theme_enabled` → `auto_theme_strategy` ("ldr" / "off")
  - `location.{latitude,longitude}` → top-level `lat` / `lon`
  - nested `alarm.{enabled,time,days}` → standalone `alarm.json`
  - backup `.bak` старых файлов с timestamp suffix перед перезаписью
- [x] `_docs/CHANGELOG.md` обновлён — секция `## Unreleased — ui-rewrite
      (Stage 1–5 migration from 0.5.5, uncommitted)`.
- [x] `.wav` конверсия для `confirm.ogg` / `startup.ogg` пропущена —
      `pw-play` на Pi 5/Trixie играет `.ogg` напрямую без потерь.

**Acceptance:**
- ✓ Финальный smoke (Windows): Kivy boot чист, никаких ERROR/Traceback,
  все сервисы стартуют (`sensor`, `alarm clock`, `auto-theme strategy
  set: ldr`, `volume service started`).
- ✓ Migrate dry-run на `bedrock.old/.../user_config.json`: получился
  валидный 2.0 user.json + alarm.json без потери ключей.
- На Pi после деплоя: проверить визуально dark PNG'и (background +
  6 overlays) — **проверить руками**.

## Что дальше

- **Закоммитить серию из 5 PR** (или одним squash, если решим).
  Suggested split:
  1. `app/{events,i18n}.py` + `locale/` + main.kv menu i18n
  2. sensor LDR + auto_theme_service + settings UI auto-theme
  3. volume_service + settings UI volume
  4. snooze + welcome + sounds restore
  5. dark PNGs replace + migrate_user_config.py + CHANGELOG
- **Деплой на Pi**: `scripts/deploy.sh` (он уже push'ит ветку и
  rsync'ит). Проверить:
  - LDR backend = `lgpio` (не mock)
  - Volume backend = `wpctl`, GPIO `buttons=on`
  - Snooze button работает + через 5 мин popup возвращается
  - Welcome notification + startup chime на старте
- **Заменить orphan `auto_dark_mode` на `auto_theme_strategy` в
  admin/templates/themes.html** — отдельный PR (admin UI имеет старый
  toggle, теперь legacy mapping в settings page его читает).
- **Перевод оставшихся KV-страниц** (home/alarm/schedule/weather/pigs)
  на `app.i18n_strings` — отдельный косметический PR.

## Decisions (resolved 2026-05-07)

1. **RU локализация:** делаем оба (en + ru), как в 0.5.5. Можно срезать позже,
   если ru не понадобится.
2. **GPIO кнопки громкости 23/24:** **подключены**. Этап 3 через
   `gpiozero.Button(23/24)` (компактнее `lgpio` low-level из 0.5.5).
3. **LDR на GPIO 12:** **подключён**. Auto-theme через strategy pattern
   (ldr / astral / off), см. Этап 2.
4. **Audio Bonnet HAT:** **снят**. Только pipewire через `pw-play`,
   `audio_service.py` из 0.5.5 не возвращаем.

## Pointers

- Memory: [`bedrock_2_0_state.md`](file:///C:/Users/Standa/.claude/projects/C--Users-Standa-OneDrive----------/memory/bedrock_2_0_state.md)
- Memory: [`bedrock_old_vs_2_0_audit.md`](file:///C:/Users/Standa/.claude/projects/C--Users-Standa-OneDrive----------/memory/bedrock_old_vs_2_0_audit.md)
- Текущий handoff: [SESSION_2026-05-07_HANDOFF.md](SESSION_2026-05-07_HANDOFF.md)
- Старый recovery context: [RECOVERY.md](RECOVERY.md), [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md)
