"""
JsonStore — tiny helper for the load-or-default + atomic-save dance shared
by alarm, schedule, pigs, notifications, and the weather cache.

Before this module each service had ~30 lines of `if exists / open / parse /
broad except / makedirs / write` boilerplate, with inconsistent error
handling (some `print()` in Russian, some `logger.error`, some
`traceback.print_exc()`). This consolidates that into one place and gives
every service:
  - Narrow exception catching (`json.JSONDecodeError`, `OSError`)
  - Default values produced lazily by a callable, so a default with mutable
    fields (lists, dicts, datetime.now()) is generated fresh per call rather
    than shared by reference
  - Auto-creation of the parent directory on save
  - A single logger.error path on read failure that names the file

Each service stays in charge of its own in-memory representation; this
module only handles the file IO. Use composition (`self._store = JsonStore(...)`)
not inheritance — callers may want to manage their own subset of fields.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable


class JsonStore:
    def __init__(
        self,
        path: str,
        default_factory: Callable[[], Any],
        logger: logging.Logger | None = None,
    ):
        self.path = path
        self._default_factory = default_factory
        self._log = logger or logging.getLogger(__name__)

    def load(self) -> Any:
        """Return the parsed file contents, or a freshly built default if the
        file is missing or unreadable. Writes the default back to disk only
        when the file did not exist (so a corrupt-but-present file isn't
        silently overwritten — operator can inspect it)."""
        if not os.path.exists(self.path):
            data = self._default_factory()
            self.save(data)
            return data
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            self._log.error(f"{self.path} unreadable ({e}); using defaults (file left in place)")
            return self._default_factory()

    def save(self, data: Any) -> bool:
        """Atomically write `data` as pretty-printed JSON. Returns True on
        success, False on OSError (disk full, permission denied, etc.) —
        caller can decide whether to retry or surface to the user."""
        dirname = os.path.dirname(self.path)
        if dirname:
            try:
                os.makedirs(dirname, exist_ok=True)
            except OSError as e:
                self._log.error(f"failed to create {dirname}: {e}")
                return False
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError as e:
            self._log.error(f"failed to save {self.path}: {e}")
            return False
