"""
Backend service smoke tests — alarm, schedule, pigs, notifications, weather.
Read-only where possible; exercises load + getter contracts.
"""
import os


def t_alarm_service():
    from services.alarm_service import AlarmService
    svc = AlarmService()
    a = svc.get_alarm()
    if not isinstance(a, dict):
        return "alarm_service.get_alarm() returns dict", False, f"got {type(a).__name__}"
    required = {"time", "enabled", "repeat", "ringtone", "fadein"}
    missing = required - set(a.keys())
    return ("alarm_service contract",
            not missing,
            ("ok: " + ", ".join(f"{k}={a[k]!r}" for k in sorted(required)))
            if not missing else f"missing keys: {missing}")


def t_schedule_service():
    from services.schedule_service import ScheduleService
    svc = ScheduleService()
    if not isinstance(svc.schedule, dict):
        return ("schedule_service.schedule is dict", False,
                f"got {type(svc.schedule).__name__}")
    days = sorted(svc.schedule.keys())
    expected = [str(d) for d in range(1, 8)]
    ok = set(days) == set(expected)
    counts = {d: len(svc.schedule[d]) for d in expected}
    return ("schedule_service has days 1..7", ok,
            f"lessons per day: {counts}")


def t_pigs_service():
    from services.pigs_service import PigsService
    svc = PigsService()
    vals, integral = svc.get_all_values()
    keys_ok = set(vals.keys()) == {"water", "food", "clean"}
    range_ok = all(0 <= float(v) <= 100 for v in vals.values())
    int_ok = 0 <= float(integral) <= 1
    return ("pigs_service values + ranges",
            keys_ok and range_ok and int_ok,
            f"vals={ {k: round(v, 1) for k, v in vals.items()} } integral={integral:.2f}")


def t_notifications_service():
    from services.notifications_service import NotificationService
    svc = NotificationService()
    ok = isinstance(svc.notifications, list)
    return ("notification_service.notifications is list", ok,
            f"count={len(svc.notifications) if ok else 'n/a'}")


def t_weather_service_load():
    from services.weather_service import WeatherService
    # Use fake coords so we don't fire a real HTTP call here — just exercise load.
    svc = WeatherService(lat=51.5390, lon=-0.1426)
    ok = isinstance(svc.weather, dict)
    return ("weather_service loads cache", ok,
            f"keys: {sorted(svc.weather.keys())}")


def run():
    return [t_alarm_service(), t_schedule_service(), t_pigs_service(),
            t_notifications_service(), t_weather_service_load()]
