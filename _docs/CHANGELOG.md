# Changelog

Hand-written, top-newest. Ветка `recovery-from-0.8.2` основана на коммите
`65164b2` ("0.8.2") из `pi/main`. Всё что выше — наработка после восстановления.

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
