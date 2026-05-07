# Recovery: 1.0.x → 0.8.2

> **Update 2026-05-07:** Этот recovery шёл от `0.8.2` baseline. Позже выяснилось,
> что **отдельная ветка `0.5.5`** в репо `Standaoerby/bedrock-app` (локально
> `C:\_PROJECTS\bedrock.old\bedrock-app`) содержала рабочие фичи, не дошедшие
> ни до 0.8.2, ни до текущего ui-rewrite: i18n, snooze, auto-theme, volume
> controls, welcome notification. План восстановления —
> [MIGRATION_FROM_0_5_5.md](MIGRATION_FROM_0_5_5.md).

## Что произошло

После релиза `0.8.2` (commit `65164b2`) на Pi пошли в ветку 1.0.x. Целью была
"полировка": разделили SoundService и VolumeService, добавили `ThemeManager` и
`bedrock_launcher.py`, попытались сделать автопереключение темы по датчику
освещения. По дороге всё отвалилось:

| Симптом | Где |
|---|---|
| Тема не выбирается на старте | `main.py:_simple_theme_init` стрелял через 3 сек до того, как сенсор реально стартовал в daemon-потоке. Считывал дефолт `light_level=True` → всегда выбирал light. |
| Тень часов «halo» в dark | `themes/minecraft/dark/theme.json` shadow=`[0.9,0.9,0.9,0.3]` — светлая тень на тёмном фоне. Логика «инвертируем тень» концептуально неверна. |
| Сломан фулскрин | 5 разных layered-методов force-fullscreen в main.py + `bedrock_launcher.py`. `Window.size = (1024,600)` фактически выводит из fullscreen. |
| Будильник может попап-ить дважды | Polling 30s, alarm_time precision до минуты — без guard. |
| GPIO double-claim | `sensor_service.py` и `volume_service.py` оба `lgpio.gpiochip_open(0)` без координации. На Pi5 ронит. |

В коммитах это видно по сообщениям: `Volume Issues` → `Theme Colors` →
`SHIT` → `Не работает фулскрин, сломалась тень часов` → `Тема не выбирается на
старте, тень под часами, сломан фулскрин` → `Soso`. 17 коммитов попыток "ещё
один слой защиты сверху", каждый раз делая хуже.

## Решение

Новая ветка `recovery-from-0.8.2` от `pi/main` (`65164b2`). Все 52 коммита
1.0.x игнорируем — за этот промежуток ничего годного не появилось, только
больше force-методов поверх настоящих багов.

`origin/main` (Soso) оставлен как есть для истории. **Не использовать.**

## Сравнение архитектуры

|  | 0.8.2 (current) | 1.0.x (broken) |
|---|---|---|
| `main.py` LOC | 275 | 554 |
| Fullscreen | 1 строка `Config.set` | 5 layered force-методов |
| Тема на старте | синхронно из JSON, мгновенно | scheduled +3s, race с sensor thread |
| Тень часов | хардкод `[0,0,0,0.5]` (всегда тёмная) | привязана к теме, инвертится в dark |
| `utils/` | пусто | `theme_manager`, `common`, `error_handler`, `theme_debug` |
| `services/` | без `sound_service`, `volume_service` | с ними |
| `bedrock_launcher.py` | нет | есть, конфликтует с main.py |
| `health_check.py` | нет | 370 строк auto-fix скрипт |

## Что НЕ перенесено из 1.0.x

Ни строчки. Если позже захотим:

- **Auto-theme by light sensor** — нужен LDR на GPIO12, в железе сейчас не
  установлен. Логика была сделана плохо, переписывать с нуля.
- **Volume buttons GPIO 23/24** — не было в 0.8.2, в 1.0.x было через
  `volume_service.py` с GPIO double-claim. Полностью заново.
- **SoundService с очередью** — на 0.8.2 `app.play_sound()` это 10 строк
  прямо в main.py. Если станет нужно дебаунсить большие потоки звуков —
  выделить отдельно.
- **Health check / autostart** — отсутствует. Сделать systemd unit, простая
  `/etc/systemd/system/bedrock.service` с `ExecStart=/path/to/python main.py`.

См. [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md) для полного списка.
