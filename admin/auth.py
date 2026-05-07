"""Password-based session auth. Single user list lives in
config/admin.json; passwords are hashed via werkzeug.security
(pbkdf2-sha256 by default — no native deps to compile on Pi)."""
from __future__ import annotations
import os
from functools import wraps
from typing import Optional

from flask import request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash

from .config_io import read_json, write_json
from .paths import ADMIN_CONFIG


def _load_admin_cfg() -> dict:
    return read_json(ADMIN_CONFIG, default={}) or {}


def _save_admin_cfg(cfg: dict) -> None:
    write_json(ADMIN_CONFIG, cfg)


def get_secret_key() -> str:
    """Return Flask session secret key, generating one on first run."""
    cfg = _load_admin_cfg()
    key = cfg.get("secret_key")
    if not key:
        key = os.urandom(32).hex()
        cfg["secret_key"] = key
        _save_admin_cfg(cfg)
    return key


def verify(username: str, password: str) -> bool:
    """True if the supplied password matches the stored hash for username."""
    cfg = _load_admin_cfg()
    users = cfg.get("users", {}) or {}
    hashed = users.get(username)
    if not hashed:
        return False
    return check_password_hash(hashed, password)


def has_any_user() -> bool:
    cfg = _load_admin_cfg()
    return bool(cfg.get("users"))


def set_password(username: str, password: str) -> None:
    """Create or update a user's password hash."""
    cfg = _load_admin_cfg()
    cfg.setdefault("users", {})[username] = generate_password_hash(password)
    _save_admin_cfg(cfg)


def current_user() -> Optional[str]:
    return session.get("user")


def login_required(fn):
    """Redirect unauthenticated requests to the login page, preserving
    the original target as ?next=."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper
