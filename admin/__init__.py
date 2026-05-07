"""Bedrock admin web UI.

A Flask app served separately from the Kivy panel app. Reads/writes
the same `config/*.json` files Bedrock uses; Bedrock picks up changes
on its own polling cadence (alarm clock, theme switch via apply_theme,
etc) or after a service restart.

Run:
    python -m admin.server          # run dev/prod server (host 0.0.0.0:8080)
    python -m admin.cli set-password <user>   # bootstrap an admin user

The server lives in scripts/bedrock-admin.service on the Pi.
"""
