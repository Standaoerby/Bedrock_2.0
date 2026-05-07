# Changelog

Hand-written, top-newest. Ветка `recovery-from-0.8.2` основана на коммите
`65164b2` ("0.8.2") из `pi/main`. Всё что выше — наработка после восстановления.

## v2.1.0 — Stage 1–5 migration from 0.5.5 (2026-05-08, uncommitted)

Восстановление функционала из ветки 0.5.5 (`bedrock.old/bedrock-app`),
который не дошёл ни до 0.8.2, ни до текущего ui-rewrite. Полный план и
acceptance — [MIGRATION_FROM_0_5_5.md](MIGRATION_FROM_0_5_5.md).

### Stage 1 — i18n + event bus
- `app/events.py` — thread-safe pub/sub.
- `app/i18n.py` — `Translator` (en + ru, en-fallback). KV reads
  `app.i18n_strings.get(...)` so DictProperty reassignment on
  `set_language()` re-evaluates bindings.
- `locale/en.json` + `locale/ru.json` (66 keys each).
- `main.kv`: 5 menu buttons via `app.i18n_strings.get(...)`.

### Stage 2 — auto-theme (LDR + astral)
- `services/sensor_service.py`: `read_light_level()` on BCM 12 with
  smoothing buffer (4 samples, majority vote). Backend resolved at
  start: `lgpio` → `RPi.GPIO` → `MockLDR` (day/night by hour for
  Windows/CI).
- `services/auto_theme_service.py`: strategy pattern
  (`OffStrategy`/`LDRStrategy`/`AstralStrategy`). All on Kivy main
  thread via `Clock.schedule_interval` — no extra threading layer to
  GPIO-double-claim like 1.0.x. LDR uses N-sample stability threshold
  (default 3) before flipping. Astral caches sunrise/sunset for the
  day. Auto switches via `apply_theme(..., persist=False)` so manual
  preference stays the source of truth in user.json.
- Legacy compat: `auto_dark_mode: bool` (the orphan key the admin web
  UI was already writing) maps to `auto_theme_strategy="ldr"`.
- `requirements.txt` += `astral>=3.2`.
- `pages/settings.py` + `.kv`: language picker + auto-theme strategy
  spinner + threshold input + live status label.

### Stage 3 — volume control
- `services/volume_service.py`: `_WpctlBackend` on Linux (pipewire
  via `wpctl set-volume @DEFAULT_AUDIO_SINK@`), `_CacheBackend`
  fallback (Windows). amixer not revived — Trixie ALSA is a pipewire
  shim.
- GPIO buttons on BCM 23 (up) / 24 (down) via `gpiozero.Button`,
  `Clock.schedule_once` to bring callbacks back to main thread.
  Optional: skipped if `gpiozero` import fails (Windows) or button
  init fails (no hardware).
- `requirements.txt` += `gpiozero; sys_platform == "linux"`.
- `pages/settings.py` + `.kv`: `−` / value `NN%` / `+` panel.
- 5s poll interval for external changes (admin web UI / shell `wpctl`).

### Stage 4 — snooze + welcome + restored sounds
- `assets/sounds/confirm.ogg` + `startup.ogg` copied from 0.5.5
  (`themes/minecraft/sounds/`). `main.py:load_sounds()` registers
  them.
- `BedrockApp.on_start()` + 1.2s deferred `_fire_welcome()`:
  `notification_service.add(...)` with i18n `"welcome_back"` template
  (`{username}` substitution from user.json), then
  `play_sound("startup")`.
- `services/alarm_clock.py:snooze(minutes=5)`: cancels in-flight
  snooze, dismisses popup, schedules `_wake` via
  `Clock.schedule_once`. Ringtone/fadein resolved at fire-time from
  alarm_service (not cached). `stop_alarm()` cancels snooze too.
- `classes/alarm_popup.py`: `on_snooze: ObjectProperty` callback,
  `Snooze` button beside `Turn Off` (50/50 split). Uses i18n labels.

### Stage 5 — assets + config migration
- `themes/minecraft/dark/{background,overlay_*}.png` (7 files)
  replaced with the correct 0.5.5 versions. The previously checked-in
  dark PNGs were 5–10× larger and likely came from a wrong source
  (probably 1.0.x) — light theme PNGs were already byte-identical.
- `themes/minecraft/light/overlay_default.png` added (fallback overlay
  for screens without a dedicated key in theme.json).
- `scripts/migrate_user_config.py` — one-shot 0.5.5 →2.0:
  `user_config.json` → `user.json` with key remapping
  (`variant`→`theme_mode`, `birthday`→`birthdate`,
  `auto_theme_enabled`→`auto_theme_strategy`,
  `location.latitude/longitude`→`lat`/`lon`); nested `alarm` block
  → standalone `alarm.json`. Backup of overwritten files. Dry-run
  via `--dry-run`.

## Unreleased — recovery branch

### `0f1e225` — Wire AlarmClock + dup-trigger guard, marquee perf, drop dead margin

- **`main.py`**: инстанциируется `AlarmClock` в `build()` и останавливается в
  `on_stop`. Раньше класс существовал, но никто его не создавал — будильник
  не срабатывал.
- **`services/alarm_clock.py`**: track `_last_trigger_key` (date + HH:MM) —
  polling 30s больше не фарит alarm дважды в одной минуте.
- **`classes/marquee.py`**: PushMatrix/Translate/PopMatrix создаются один раз
  в `__init__`, далее меняется только `Translate.x` через `scroll_x`.
  Раньше canvas.before/after очищались на каждом кадре (30Hz) — заметная
  нагрузка на GPU Pi5.
- **`pages/alarm.kv`**: убрана мёртвая директива `margin: [...]` на BoxLayout
  (Kivy её игнорирует, у BoxLayout нет такого свойства).

### `f2b5ff7` — Runtime theme switching + Home interval cleanup

- **`main.py`**: `theme_name`/`theme_mode`/`theme_config` стали Kivy
  properties — KV-биндинги перекрашиваются при смене темы. Добавлены
  `app.load_theme_config()` (метод) и `app.apply_theme(theme, mode, persist=True)`
  — грузит, реассайнит property, сохраняет в `config/user.json`.
- При старте `build()` читает сохранённую тему из `config/user.json` — dark
  mode переживает рестарт.
- Удалён мёртвый импорт `MDTimePickerInput` (есть только в kivymd 2.x).
- **`pages/settings.py`**: `save_all_settings`/`change_theme`/`toggle_dark_mode`
  идут через `app.apply_theme` — все экраны реально перекрашиваются. Раньше
  было `screen_manager.current = "settings"` — это просто переход в settings,
  остальные экраны оставались в старой теме.
- **`pages/settings.kv`**: добавлен **CheckBox** для dark mode (раньше был
  только label-обманка). Убран `on_text_validate: root.save_username(...)` —
  метод `save_username` не существовал, Enter в username крашил.
- **`pages/home.py`**: четыре `Clock.schedule_interval` теперь трекаются в
  `self._intervals` и убиваются в `on_leave`. Раньше утекали на каждом
  заходе на Home.

### `d9cf143` — Bug fixes on 0.8.2 baseline

- **`themes/minecraft/dark/theme.json`**: `colors.font_highdark` → `font_highlight`
  (typo, schedule highlight color пропадал в dark).
- **`pages/alarm.kv`**: убраны дублирующиеся `font_size: "48sp"` под
  `huge: "180sp"` — большие цифры часов/минут теперь действительно большие.
- **`requirements.txt`**: заменены неверные сенсорные пакеты
  (`bme280`/`ccs811`) на реально используемые (`ens160`/`ahtx0`).
  `kivymd` запинен `<2.0.0` (1.x — это что main.py импортирует через
  `kivymd.uix.screen.MDScreen`).
- **`services/{schedule,notifications}_service.py`**: `json.load()` обёрнут
  в try/except — битый JSON больше не крашит старт приложения.

## `65164b2` — 0.8.2 (база recovery)

Последняя стабильная версия от `pi/main`. Архитектура простая, без
layered-fullscreen и без auto-theme. Известные дефекты на этом коммите
описаны в [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md), большинство исправлены
выше.
