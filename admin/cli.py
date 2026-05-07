"""Bootstrap CLI for the admin web UI.

Usage:
    python -m admin.cli set-password <username>      # interactive
    python -m admin.cli set-password <username> -p PWD   # non-interactive
    python -m admin.cli list-users
"""
from __future__ import annotations
import argparse
import getpass
import sys

from . import auth
from .config_io import read_json
from .paths import ADMIN_CONFIG


def cmd_set_password(args: argparse.Namespace) -> int:
    username = args.username.strip()
    if not username:
        print("Username cannot be empty", file=sys.stderr)
        return 1
    if args.password is not None:
        password = args.password
    else:
        password = getpass.getpass(f"Password for {username}: ")
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("Passwords don't match", file=sys.stderr)
            return 1
    if len(password) < 8:
        print("Password must be at least 8 characters", file=sys.stderr)
        return 1
    auth.set_password(username, password)
    print(f"Password set for '{username}'.")
    print(f"Stored at {ADMIN_CONFIG}")
    return 0


def cmd_list_users(_args: argparse.Namespace) -> int:
    cfg = read_json(ADMIN_CONFIG, default={})
    users = sorted((cfg.get("users") or {}).keys())
    if not users:
        print("(no users)")
    else:
        for u in users:
            print(u)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="admin.cli", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("set-password", help="Set/replace a user's password")
    sp.add_argument("username")
    sp.add_argument("-p", "--password", help="non-interactive password (prompts if omitted)")
    sp.set_defaults(func=cmd_set_password)

    lu = sub.add_parser("list-users", help="List configured admin usernames")
    lu.set_defaults(func=cmd_list_users)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
