"""
AudioPlayer — cross-platform start/stop/loop sound playback with explicit
process-group kill for the looping case.

Why not Kivy SoundLoader: on the Pi target (Trixie + Kivy 2.3 + py3.13)
both audio_sdl2 and audio_ffpyplayer are unusable for our flow —
audio_sdl2 hangs at SDL_mixer init, and audio_ffpyplayer's abuffersink
rejects the channel-layout reformat ("Channel layout change is not
supported"), so the sound reports state='play' but no audio reaches the
device. We work around it by shelling out to pw-play (which talks to
pipewire-pulse directly and has been verified to play the WAVs / MP3s).

On Windows, Kivy's SoundLoader (audio_sdl2 path) works fine, so we keep
that branch.

Stateful — one player tracks one currently-playing sound. Calling
play() while another sound is playing stops the previous one first.
"""
import logging
import os
import platform
import signal
import subprocess

logger = logging.getLogger(__name__)

_IS_PI = platform.system() != "Windows"


class AudioPlayer:
    def __init__(self):
        self._proc: subprocess.Popen | None = None       # Pi only
        self._kivy_sound = None                          # Windows only

    # ── Public API ────────────────────────────────────────────────────
    def play(self, path: str, loop: bool = False, volume: float = 1.0) -> bool:
        """Start playing `path`. Returns True if playback was kicked off,
        False on missing file or backend init failure. Stops any sound
        already playing on this player first."""
        if not os.path.exists(path):
            logger.warning(f"audio_player: missing {path}")
            return False
        self.stop()
        if _IS_PI:
            return self._play_pi(path, loop, volume)
        return self._play_kivy(path, loop, volume)

    def stop(self) -> None:
        """Kill any in-flight playback. Safe to call on a fresh / already-
        stopped player."""
        if self._proc is not None:
            try:
                # Loop case wraps pw-play in `bash -c 'while true; ...'`
                # — killing just the bash leaves the running pw-play
                # child playing out the rest of the file. Kill the whole
                # process group at once.
                os.killpg(self._proc.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError) as e:
                logger.debug(f"audio_player: stop(): {e}")
            self._proc = None
        if self._kivy_sound is not None:
            try:
                self._kivy_sound.stop()
            except Exception as e:
                # Kivy's audio backends throw a variety of platform-
                # specific exceptions on stop after error states; we just
                # want the player back to a clean state.
                logger.debug(f"audio_player: kivy stop(): {e}")
            self._kivy_sound = None

    @property
    def is_playing(self) -> bool:
        if _IS_PI and self._proc is not None:
            return self._proc.poll() is None
        if self._kivy_sound is not None:
            return getattr(self._kivy_sound, "state", "stop") == "play"
        return False

    # ── Backends ──────────────────────────────────────────────────────
    def _play_pi(self, path: str, loop: bool, volume: float) -> bool:
        v = max(0.0, min(1.0, volume))
        if loop:
            # pw-play has no --loop; use a shell loop. start_new_session
            # gives us a process group we can kill atomically.
            cmd = f'while true; do pw-play --volume={v:.2f} "{path}"; done'
            self._proc = subprocess.Popen(
                ["bash", "-c", cmd],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        else:
            self._proc = subprocess.Popen(
                ["pw-play", f"--volume={v:.2f}", path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return True

    def _play_kivy(self, path: str, loop: bool, volume: float) -> bool:
        # Lazy import — avoids paying the Kivy audio init cost on Pi
        # where we never go through this branch.
        from kivy.core.audio import SoundLoader
        self._kivy_sound = SoundLoader.load(path)
        if self._kivy_sound is None:
            logger.warning(f"audio_player: SoundLoader.load returned None for {path}")
            return False
        self._kivy_sound.loop = loop
        self._kivy_sound.volume = volume
        self._kivy_sound.play()
        return True
