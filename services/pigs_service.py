"""
PigsService — three timed bars (water, food, cleaning) that drain over
time and reset to full when the user taps Done. Each bar tracks a
`last_reset` ISO-format timestamp and a `max_hours` lifetime; the bar's
"% remaining" is `100 * (1 - elapsed / max_hours)`, clamped to [0, 100].

The dict shape is preserved for backwards compatibility with on-disk
configs that already exist.
"""
import logging
from datetime import datetime

from services._jsonstore import JsonStore

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat()


def _default_config() -> dict:
    return {
        "pigs": [
            {"name": "Korovka"},
            {"name": "Karamelka"},
        ],
        "bars": {
            "water": {"label": "Water",    "max_hours": 8,  "last_reset": _now_iso()},
            "food":  {"label": "Food",     "max_hours": 6,  "last_reset": _now_iso()},
            "clean": {"label": "Cleaning", "max_hours": 12, "last_reset": _now_iso()},
        },
    }


class PigsService:
    def __init__(self, path: str = "config/pigs.json"):
        self._store = JsonStore(path, _default_config, logger=logger)
        self.config: dict = {}
        self.load()

    def load(self) -> None:
        self.config = self._store.load()

    def save(self) -> None:
        self._store.save(self.config)

    # ── Bar math ──────────────────────────────────────────────────────
    def _parse_iso(self, s: str) -> datetime:
        """Parse an ISO timestamp tolerantly. Stripping fractional-second
        and timezone suffixes lets older config writes (which used a
        narrower format) keep working."""
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            # Stdlib fromisoformat got stricter pre-3.11 — strip the bits
            # we don't need and retry.
            cleaned = s.split(".")[0].split("+")[0].rstrip("Z")
            try:
                return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S")
            except ValueError as e:
                logger.warning(f"unparseable timestamp {s!r} ({e}); treating as now")
                return datetime.now()

    def get_bar_percentage(self, key: str) -> float:
        """% of the bar's lifetime still remaining; 0 means fully drained."""
        bar = self.config.get("bars", {}).get(key, {})
        max_hours = bar.get("max_hours", 24)
        last_reset = self._parse_iso(bar.get("last_reset", _now_iso()))
        elapsed_hours = (datetime.now() - last_reset).total_seconds() / 3600
        if elapsed_hours >= max_hours:
            return 0.0
        pct = 100 - (elapsed_hours / max_hours * 100)
        return max(0.0, min(100.0, pct))

    def get_all_values(self) -> tuple[dict, float]:
        """({key: pct}, overall_status_0_to_1) — mean across all bars."""
        bars = self.config.get("bars", {})
        if not bars:
            return {}, 0.0
        result = {key: self.get_bar_percentage(key) for key in bars}
        overall = sum(result.values()) / len(result) / 100
        return result, overall

    # ── Bar reset ─────────────────────────────────────────────────────
    def reset_bar(self, key: str) -> None:
        if key not in self.config.get("bars", {}):
            logger.warning(f"reset_bar: unknown bar {key!r}")
            return
        self.config["bars"][key]["last_reset"] = _now_iso()
        self.save()
        logger.info(f"bar {key!r} reset")
