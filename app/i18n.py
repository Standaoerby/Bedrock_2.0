"""Translation loader.

Locale files live in `locale/<lang>.json` as flat key→value dicts. The
loader keeps the active language and falls back to English for missing
keys. KV consumers should read through `app.i18n_strings` (a DictProperty
on BedrockApp) so KV bindings re-evaluate on language switch — the
`tr()` method here is for Python callers only.
"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LOCALE_DIR = Path("locale")
DEFAULT_LANG = "en"


class Translator:
    def __init__(self, locale_dir: Path = LOCALE_DIR) -> None:
        self.locale_dir = Path(locale_dir)
        self.language = DEFAULT_LANG
        self.strings: dict[str, str] = {}
        self._fallback: dict[str, str] = {}

    def load(self, language: str) -> None:
        self.language = language
        self.strings = self._load_json(self.locale_dir / f"{language}.json")
        if language != DEFAULT_LANG:
            self._fallback = self._load_json(self.locale_dir / f"{DEFAULT_LANG}.json")
        else:
            self._fallback = {}
        logger.info("locale loaded: %s (%d keys)", language, len(self.strings))

    @staticmethod
    def _load_json(path: Path) -> dict[str, str]:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.warning("locale load failed: %s — %s", path, e)
            return {}

    def tr(self, key: str, default: str | None = None) -> str:
        if key in self.strings:
            return self.strings[key]
        if key in self._fallback:
            return self._fallback[key]
        return default if default is not None else key

    def available_languages(self) -> list[str]:
        if not self.locale_dir.is_dir():
            return [DEFAULT_LANG]
        langs = []
        for entry in os.listdir(self.locale_dir):
            if entry.endswith(".json"):
                langs.append(entry[:-5])
        return sorted(langs) or [DEFAULT_LANG]

    def merged(self) -> dict[str, str]:
        """All keys with active-language preference and en-fallback for misses."""
        out = dict(self._fallback)
        out.update(self.strings)
        return out
