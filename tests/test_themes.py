"""
Theme schema tests — every theme.json under themes/ must parse and have
the canonical font_sizes / colors / layout keys.

`_template` and `.`/`_` prefixed dirs are scanned too (template should
parse), but only non-underscore themes are required to have a working
background_image.
"""
import json
import os


REQUIRED_FONT_SIZES = {"tiny", "small", "default", "medium", "large", "xlarge", "huge"}
REQUIRED_COLORS = {
    "font_default", "font_secondary", "font_highlight", "font_disabled",
    "active", "inactive", "shadow_light", "shadow_dark",
    "trend_up", "trend_down",
}
REQUIRED_LAYOUT = {
    "grid_unit", "padding_sm", "padding_md",
    "spacing_sm", "spacing_md",
    "widget_height_md", "menu_height",
}


def _theme_files():
    out = []
    if not os.path.isdir("themes"):
        return out
    for name in os.listdir("themes"):
        nd = os.path.join("themes", name)
        if not os.path.isdir(nd):
            continue
        for mode in ("light", "dark"):
            p = os.path.join(nd, mode, "theme.json")
            if os.path.exists(p):
                out.append((name, mode, p))
    return out


def t_all_parse():
    files = _theme_files()
    if not files:
        return "any theme.json found", False, "themes/ is empty"
    bad = []
    for name, mode, p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            bad.append(f"{name}/{mode}: {e}")
    return ("all theme.json parse", not bad,
            ("ok: " + str(len(files)) + " files") if not bad else f"errors: {bad}")


def t_required_keys():
    files = _theme_files()
    bad = []
    for name, mode, p in files:
        if name.startswith(("_", ".")):
            continue
        try:
            cfg = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        missing = []
        if not REQUIRED_FONT_SIZES <= set(cfg.get("font_sizes", {}).keys()):
            missing.append("font_sizes:" + ",".join(REQUIRED_FONT_SIZES - set(cfg.get("font_sizes", {}).keys())))
        if not REQUIRED_COLORS <= set(cfg.get("colors", {}).keys()):
            missing.append("colors:" + ",".join(REQUIRED_COLORS - set(cfg.get("colors", {}).keys())))
        if not REQUIRED_LAYOUT <= set(cfg.get("layout", {}).keys()):
            missing.append("layout:" + ",".join(REQUIRED_LAYOUT - set(cfg.get("layout", {}).keys())))
        if missing:
            bad.append(f"{name}/{mode} missing {missing}")
    return ("required keys present", not bad,
            "ok" if not bad else f"errors: {bad}")


def t_color_format():
    """Each color must be a 4-element [r,g,b,a] in 0..1."""
    files = _theme_files()
    bad = []
    for name, mode, p in files:
        try:
            cfg = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        for k, v in (cfg.get("colors", {}) or {}).items():
            if k.startswith("_"):
                continue
            if not (isinstance(v, list) and len(v) == 4
                    and all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in v)):
                bad.append(f"{name}/{mode}.colors.{k} = {v}")
    return ("color values are RGBA 0..1", not bad,
            "ok" if not bad else f"bad: {bad[:3]}")


def t_background_files():
    """Non-template themes should have an existing background_image."""
    files = _theme_files()
    bad = []
    for name, mode, p in files:
        if name.startswith(("_", ".")):
            continue
        try:
            cfg = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        bg = cfg.get("background_image", "")
        if bg and not os.path.exists(bg):
            bad.append(f"{name}/{mode}: missing {bg}")
    return ("background_image files exist", not bad,
            "ok" if not bad else f"missing: {bad}")


def run():
    return [t_all_parse(), t_required_keys(), t_color_format(),
            t_background_files()]
