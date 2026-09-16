#!/usr/bin/env python3
"""Organizations, Projects, People, and each Project's Key Results.

Per the PRD's data model (§24) and hierarchy (§6-7): every entity has a
stable, type-prefixed id (org_<x>, project_<x>, person_<x>), and every child
carries explicit parent references. An organization may hold many projects,
so the organization is never a project's identity.

    /var/lib/hermes/pm/organizations/<org_id>.md
    /var/lib/hermes/pm/projects/<project_id>.md      objective + Key Results live here
    /var/lib/hermes/pm/people/<person_id>.md

The frontmatter (structured fields) and the Key Results block only change
through this CLI. The "## Project Memory" body section is free prose, and
may be edited with ordinary file tools.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

PM_DIR = Path(os.environ.get("PM_DIR", "/var/lib/hermes/pm"))

FOLDERS = {"organization": "organizations", "project": "projects", "person": "people"}
PREFIXES = {"organization": "org", "project": "project", "person": "person"}

PROJECT_STATUS = ("planned", "active", "paused", "completed")
PERSON_TYPES = ("internal", "external")  # internal crosses every organization

CAMPOS = {
    "organization": {"name": None, "metadata": None,
                      "created_at": None, "updated_at": None},
    "project": {"name": None, "organization_id": None, "objective": None,
                "status": PROJECT_STATUS, "created_at": None, "updated_at": None},
    "person": {"name": None, "organization_id": None, "type": PERSON_TYPES,
               "role": None, "email": None, "metadata": None,
               "created_at": None, "updated_at": None},
}

DEFAULTS = {
    "project": {"status": "planned"},
    "person": {"type": "external"},
}

BODY = {
    "project": "\n## Key Results\n\n## Project Memory\n\n",
    "organization": "\n## Notes\n\n",
    "person": "\n## Notes\n\n",
}

KR_LINE = re.compile(r"^- (?P<id>kr_\d+) · (?P<title>.+?) · status:(?P<status>\S+)"
                      r"(?: · created_at:(?P<created_at>\S+))?$")
KR_STATUS = ("not_started", "in_progress", "completed", "dropped")


def refuse(msg: str) -> None:
    print(f"refusing: {msg}", file=sys.stderr)
    sys.exit(1)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or refuse(f"could not build a slug from '{text}'")


def path_for(kind: str, entity_id: str) -> Path:
    if kind not in FOLDERS:
        refuse(f"unknown type '{kind}'. Use one of: {', '.join(FOLDERS)}")
    return PM_DIR / FOLDERS[kind] / f"{entity_id}.md"


def read(kind: str, entity_id: str) -> tuple[dict, str]:
    p = path_for(kind, entity_id)
    if not p.exists():
        refuse(f"{kind} '{entity_id}' does not exist. Create it first with: "
               f"entities.py create {kind} \"<Name>\"")
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        refuse(f"{p} has no frontmatter -- file is corrupted")
    _, fm, body = text.split("---\n", 2)
    data = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data, body


def write(kind: str, entity_id: str, data: dict, body: str) -> None:
    p = path_for(kind, entity_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    order = ["id"] + list(CAMPOS[kind])
    lines = ["---"]
    for k in order:
        if data.get(k):
            lines.append(f"{k}: {data[k]}")
    lines.append("---")
    content = "\n".join(lines) + "\n" + body

    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{entity_id}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def validate(kind: str, field: str, value: str) -> None:
    if field not in CAMPOS[kind]:
        refuse(f"'{field}' is not a {kind} field. Fields: {', '.join(CAMPOS[kind])}")
    allowed = CAMPOS[kind][field]
    if allowed and value not in allowed:
        refuse(f"{kind}.{field} must be one of: {', '.join(allowed)}")


def resolve_org(organization_id: str) -> dict:
    org, _ = read("organization", organization_id)
    return org


# ---------------------------------------------------------------- commands

def cmd_create(args):
    kind = args.type
    if kind not in FOLDERS:
        refuse(f"unknown type '{kind}'. Use one of: {', '.join(FOLDERS)}")
    slug = args.id or slugify(args.name)
    entity_id = f"{PREFIXES[kind]}_{slug}"
    if path_for(kind, entity_id).exists():
        refuse(f"{kind} '{entity_id}' already exists")

    data = {"name": args.name}
    data.update(DEFAULTS.get(kind, {}))
    for pair in args.field or []:
        if "=" not in pair:
            refuse(f"--field expects key=value, got '{pair}'")
        k, v = pair.split("=", 1)
        validate(kind, k, v)
        data[k] = v

    # A project always belongs to one organization. A person does too,
    # UNLESS they are internal -- internal is precisely "crosses every
    # organization", so requiring one here would contradict the field.
    needs_org = kind == "project" or (kind == "person" and data.get("type") != "internal")
    if needs_org and not data.get("organization_id"):
        refuse(f"{kind} requires --field organization_id=org_<id> "
                f"(omit only for a --field type=internal person)")
    if data.get("organization_id"):
        read("organization", data["organization_id"])  # refuses if missing

    stamp = now()
    data["created_at"] = stamp
    data["updated_at"] = stamp
    write(kind, entity_id, data, BODY.get(kind, "\n"))
    print(entity_id)


def cmd_show(args):
    data, body = read(args.type, args.id)
    for k, v in data.items():
        print(f"{k}: {v}")
    print("---")
    print(body.strip() or "(empty)")


def cmd_set(args):
    data, body = read(args.type, args.id)
    validate(args.type, args.field, args.value)
    data[args.field] = args.value
    data["updated_at"] = now()
    write(args.type, args.id, data, body)


def cmd_list(args):
    kinds = [args.type] if args.type else list(FOLDERS)
    found = False
    for kind in kinds:
        folder = PM_DIR / FOLDERS[kind]
        if not folder.exists():
            continue
        for p in sorted(folder.glob("*.md")):
            data, _ = read(kind, p.stem)
            if args.organization and data.get("organization_id") != args.organization:
                continue
            if args.status and data.get("status") != args.status:
                continue
            extra = ""
            if kind == "person":
                extra = f" · {data.get('role','')} · {data.get('email','(no email)')} · {data.get('type','')}"
            elif kind == "project":
                extra = f" · {data.get('organization_id','')} · {data.get('status','')}"
            print(f"{kind}/{p.stem} · {data.get('name','')}{extra}")
            found = True
    if not found:
        print("(nothing found)")


def cmd_related(args):
    """Everything that references this entity id -- across all files."""
    target = args.id
    found = False
    for kind, folder_name in FOLDERS.items():
        folder = PM_DIR / folder_name
        if not folder.exists():
            continue
        for p in sorted(folder.glob("*.md")):
            if p.stem == target:
                continue
            if target in p.read_text(encoding="utf-8"):
                data, _ = read(kind, p.stem)
                print(f"{kind}/{p.stem} · {data.get('name','')}")
                found = True
    action_plans = PM_DIR / "action_plans.md"
    if action_plans.exists():
        for line in action_plans.read_text(encoding="utf-8").splitlines():
            if target in line:
                print(line.strip())
                found = True
    if not found:
        print("(nothing references this entity)")


# --------------------------------------------------------------- key results

def _project_body_lines(project_id: str) -> tuple[dict, list[str]]:
    data, body = read("project", project_id)
    return data, body.splitlines()


def _write_project_body(project_id: str, lines: list[str]) -> None:
    data, _ = read("project", project_id)
    data["updated_at"] = now()
    write("project", project_id, data, "\n".join(lines).rstrip() + "\n")


def _read_krs(project_id: str) -> tuple[list[dict], list[str]]:
    _, lines = _project_body_lines(project_id)
    krs = []
    for i, line in enumerate(lines):
        m = KR_LINE.match(line.strip())
        if m:
            d = m.groupdict()
            d["line"] = i
            krs.append(d)
    return krs, lines


def cmd_kr_add(args):
    """A Key Result is a candidate until the owner confirms it -- see
    pm-setup's collaborative-definition protocol. This command records a
    Key Result the owner has already confirmed."""
    krs, lines = _read_krs(args.project)
    used = [int(k["id"].split("_")[1]) for k in krs]
    new_id = f"kr_{max(used) + 1 if used else 1}"
    anchor = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## key results"):
            anchor = i
            break
    if anchor is None:
        lines += ["", "## Key Results", ""]
        anchor = len(lines) - 2
    insert_at = krs[-1]["line"] + 1 if krs else anchor + 1
    lines.insert(insert_at, f"- {new_id} · {args.title} · status:not_started · created_at:{now()}")
    _write_project_body(args.project, lines)
    print(new_id)


def cmd_kr_status(args):
    if args.status not in KR_STATUS:
        refuse(f"key result status must be one of: {', '.join(KR_STATUS)}")
    krs, lines = _read_krs(args.project)
    for k in krs:
        if k["id"] == args.id:
            stamp = f" · created_at:{k['created_at']}" if k.get("created_at") else ""
            lines[k["line"]] = f"- {k['id']} · {k['title']} · status:{args.status}{stamp}"
            _write_project_body(args.project, lines)
            return
    refuse(f"key result '{args.id}' does not exist in {args.project}")


def cmd_kr_list(args):
    krs, _ = _read_krs(args.project)
    if not krs:
        print("(no key results yet)")
        return
    for k in krs:
        print(f"{k['id']} · {k['title']} · {k['status']}")


def cmd_reindex(args):
    """Regenerate projects.md, the human-readable portfolio index (PRD §10).

    Derived, never hand-authored: every run replaces it wholesale from the
    structured project files, so it can never drift into being someone's
    only copy of mutable state.
    """
    out = PM_DIR / "projects.md"
    folder = PM_DIR / "projects"
    lines = ["# Projects", "", "Generated from projects/*.md by "
             "`entities.py reindex` -- do not hand-edit.", ""]
    if folder.exists():
        for p in sorted(folder.glob("*.md")):
            data, _ = read("project", p.stem)
            org = frontmatter_name("organizations", data.get("organization_id", ""))
            lines.append(f"- {p.stem} · {data.get('name','')} · {org} · "
                         f"{data.get('status','')} · {data.get('objective','')}")
    if len(lines) == 4:
        lines.append("(no projects yet)")
    PM_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PM_DIR, prefix=".projects.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")
        os.replace(tmp, out)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    print(f"reindexed {out}")


def frontmatter_name(folder: str, entity_id: str) -> str:
    if not entity_id:
        return "?"
    p = PM_DIR / folder / f"{entity_id}.md"
    if not p.exists():
        return entity_id
    text = p.read_text(encoding="utf-8")
    for line in text.split("---\n", 2)[1].splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return entity_id


def build_parser():
    p = argparse.ArgumentParser(prog="entities.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("create", help="creates an entity (prints its id)")
    sp.add_argument("type", choices=list(FOLDERS))
    sp.add_argument("name")
    sp.add_argument("--id", help="slug override; default is derived from the name")
    sp.add_argument("--field", action="append", metavar="KEY=VALUE")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("show")
    sp.add_argument("type", choices=list(FOLDERS))
    sp.add_argument("id")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("set", help="changes one frontmatter field")
    sp.add_argument("type", choices=list(FOLDERS))
    sp.add_argument("id")
    sp.add_argument("field")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set)

    sp = sub.add_parser("list")
    sp.add_argument("type", nargs="?", choices=list(FOLDERS))
    sp.add_argument("--organization")
    sp.add_argument("--status")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("related", help="everything that references an entity id")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_related)

    sp = sub.add_parser("reindex", help="regenerate projects.md from projects/*.md")
    sp.set_defaults(func=cmd_reindex)

    kr = sub.add_parser("kr", help="a project's Key Results").add_subparsers(
        dest="subcommand", required=True)

    k = kr.add_parser("add", help="records an owner-confirmed Key Result (prints its id)")
    k.add_argument("project")
    k.add_argument("title")
    k.set_defaults(func=cmd_kr_add)

    k = kr.add_parser("status")
    k.add_argument("project")
    k.add_argument("id")
    k.add_argument("status")
    k.set_defaults(func=cmd_kr_status)

    k = kr.add_parser("list")
    k.add_argument("project")
    k.set_defaults(func=cmd_kr_list)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
