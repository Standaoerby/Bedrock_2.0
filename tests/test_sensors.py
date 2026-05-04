"""
Sensor smoke tests.

On Pi: real ENS160 (0x53) + AHT21 (0x38) over /dev/i2c-1.
On Windows: built-in mock sensors via DummyENS160 / DummyAHTx0.

Each test returns (name, ok: bool, info: str).
"""
import time


def t_import():
    try:
        import services.sensor_service as ss  # noqa
        return "sensor_service import", True, "ok"
    except Exception as e:
        return "sensor_service import", False, repr(e)


def t_constants():
    try:
        from services.sensor_service import ENS160_ADDRESS, AHTX0_ADDRESS
        ok = ENS160_ADDRESS == 0x53 and AHTX0_ADDRESS == 0x38
        return ("sensor I2C addresses", ok,
                f"ENS160=0x{ENS160_ADDRESS:02x} AHT21=0x{AHTX0_ADDRESS:02x}")
    except Exception as e:
        return "sensor I2C addresses", False, repr(e)


def t_start_and_read():
    from services.sensor_service import SensorService
    svc = SensorService()
    try:
        svc.start()
        time.sleep(1.5)  # let bg thread populate
        r = svc.get_readings()
        keys_ok = set(r.keys()) == {
            "temperature", "humidity", "co2", "tvoc", "air_quality"}
        if not keys_ok:
            return ("sensor readings keys", False,
                    f"got keys: {set(r.keys())}")
        # Sanity ranges (works for both real and mock)
        ranges_ok = (
            -20 <= float(r["temperature"]) <= 80
            and 0 <= float(r["humidity"]) <= 100
            and 0 <= int(r["co2"]) <= 5000
            and 0 <= int(r["tvoc"]) <= 65535
        )
        return ("sensor reading sanity", ranges_ok,
                f"t={r['temperature']:.1f}C h={r['humidity']:.1f}% "
                f"CO2={r['co2']}ppm TVOC={r['tvoc']}ppb AQ={r['air_quality']}")
    finally:
        svc.stop()


def t_thread_safety():
    """Hammer get_readings from many threads while bg loop writes — should
    never raise."""
    from services.sensor_service import SensorService
    import threading
    svc = SensorService()
    svc.start()
    errors = []

    def loop():
        for _ in range(200):
            try:
                svc.get_readings()
            except Exception as e:
                errors.append(repr(e))

    threads = [threading.Thread(target=loop) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    svc.stop()
    return ("sensor thread safety (8×200 reads)", not errors,
            f"errors: {len(errors)}")


def run():
    return [t_import(), t_constants(), t_start_and_read(), t_thread_safety()]
