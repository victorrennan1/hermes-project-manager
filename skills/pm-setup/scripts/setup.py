#!/usr/bin/env python3
"""The owner's identity, from onboarding: /var/lib/hermes/pm/user.md.

Per the PRD (§3.3): created once during onboarding, and never altered by
ordinary project-management operations. `init` refuses if it already exists,
on purpose -- the only way to change these fields afterward is `update`, a
separate, deliberate command, never a side effect of some other request.

Timezone is NOT computed here. The PRD's purpose for `user_location` is
deriving a timezone, but geocoding needs a network call this offline script
does not make. That conversion belongs to the model itself (it already knows
world geography) via pm-crons: read `user_location`, decide the IANA zone,
then call `crons.py fuso <IANA>`. This script only stores what the owner said.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path

PM_DIR = Path(os.environ.get("PM_DIR", "/var/lib/hermes/pm"))
USER_FILE = PM_DIR / "user.md"

FIELDS = ("user_name", "user_location", "language")
LANGUAGES = ("pt-BR", "en")


def refuse(msg: str) -> None:
    print(f"refusing: {msg}", file=sys.stderr)
    sys.exit(1)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read() -> dict | None:
    if not USER_FILE.exists():
        return None
    text = USER_FILE.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        refuse(f"{USER_FILE} has no frontmatter -- file is corrupted")
    _, fm, _ = text.split("---\n", 2)
    data = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data


def save(data: dict) -> None:
    PM_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for k in ("user_name", "user_location", "language", "created_at", "updated_at"):
        if data.get(k):
            lines.append(f"{k}: {data[k]}")
    lines.append("---")
    fd, tmp = tempfile.mkstemp(dir=PM_DIR, prefix=".user.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, USER_FILE)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def validate(field: str, value: str) -> None:
    if field not in FIELDS:
        refuse(f"'{field}' is not a user field. Fields: {', '.join(FIELDS)}")
    if field == "language" and value not in LANGUAGES:
        refuse(f"language must be one of: {', '.join(LANGUAGES)}")
    if not value.strip():
        refuse(f"{field} cannot be empty")


# ---------------------------------------------------------------- commands

def cmd_show(args):
    data = read()
    if data is None:
        print("(no user.md yet -- onboarding has not run)")
        return
    for k, v in data.items():
        print(f"{k}: {v}")


def cmd_init(args):
    if read() is not None:
        refuse("user.md already exists. Onboarding runs once. "
               "To change a field afterward, use: setup.py user update <field> <value>")
    for field, value in (("user_name", args.name), ("user_location", args.location),
                         ("language", args.language)):
        validate(field, value)
    stamp = now()
    save({"user_name": args.name, "user_location": args.location,
          "language": args.language, "created_at": stamp, "updated_at": stamp})


def cmd_update(args):
    data = read()
    if data is None:
        refuse("no user.md yet -- run 'init' first, not 'update'")
    validate(args.field, args.value)
    data[args.field] = args.value
    data["updated_at"] = now()
    save(data)


def build_parser():
    p = argparse.ArgumentParser(prog="setup.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    u = sub.add_parser("user").add_subparsers(dest="subcommand", required=True)

    s = u.add_parser("show")
    s.set_defaults(func=cmd_show)

    s = u.add_parser("init", help="onboarding only -- refuses if user.md already exists")
    s.add_argument("--name", required=True)
    s.add_argument("--location", required=True)
    s.add_argument("--language", required=True, choices=LANGUAGES)
    s.set_defaults(func=cmd_init)

    s = u.add_parser("update", help="deliberate settings change, any time")
    s.add_argument("field", choices=FIELDS)
    s.add_argument("value")
    s.set_defaults(func=cmd_update)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
