"""
Audio smoke tests. Loads each sound file via Kivy SoundLoader and the
configured audio provider (env: KIVY_AUDIO=ffpyplayer on Pi).

Returns (name, ok, info) per test.
"""
import os


SOUND_FILES = [
    "assets/sounds/click.wav",
    "assets/sounds/success.wav",
    "assets/sounds/error.wav",
    "assets/sounds/notification.wav",
]
RINGTONES = [
    "media/ringtones/morning.wav",
    "media/ringtones/morning.mp3",
]


def t_files_present():
    missing = [p for p in SOUND_FILES if not os.path.exists(p)]
    ok = not missing
    return "audio files exist", ok, ("ok" if ok else f"missing: {missing}")


def t_ringtone_present():
    available = [p for p in RINGTONES if os.path.exists(p)]
    ok = bool(available)
    return ("ringtone present (wav or mp3)", ok,
            ("ok: " + ", ".join(available)) if ok else "no ringtone in media/ringtones/")


def t_load_each_sound():
    from kivy.core.audio import SoundLoader
    failed = []
    for path in SOUND_FILES:
        if not os.path.exists(path):
            continue
        s = SoundLoader.load(path)
        if s is None:
            failed.append(path)
    ok = not failed
    return ("load every sound", ok,
            ("ok" if ok else f"failed: {failed}"))


def t_provider_active():
    from kivy.core.audio import SoundLoader
    classes = SoundLoader._classes
    if not classes:
        return ("audio provider registered", False,
                "no audio backends loaded — KIVY_AUDIO env wrong?")
    return ("audio provider registered", True,
            f"providers: {[c.__name__ for c in classes]}")


def run():
    return [t_files_present(), t_ringtone_present(),
            t_provider_active(), t_load_each_sound()]
