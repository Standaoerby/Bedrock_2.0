"""Atomic JSON read/write for the configs Bedrock + admin share.

Atomic write semantics matter because Bedrock polls these files on its
own clock — a half-written file could land mid-poll and crash the
service. We write to a temp file in the same dir and os.replace().
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    """Load a JSON file. Returns `default` if file missing or unparsable."""
    if not path.exists():
        return default if default is not None else {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def write_json(path: Path, data: Any) -> None:
    """Atomic JSON write — temp file in same dir, then os.replace().
    Raises OSError on disk errors; caller decides how to surface."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        # Best-effort cleanup of the temp file if replace failed
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
