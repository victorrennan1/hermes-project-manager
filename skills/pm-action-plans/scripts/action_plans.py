#!/usr/bin/env python3
"""The single Action Plan base -- one line per plan, many views over it.

Schema follows the PRD (§14, §24): full 5W2H as prose (what/why/who/when/
where/how/how_much) plus the structured, queryable fields the views and the
guardrail actually use (responsible_id, due_date, status). Every plan carries
its full parent chain (organization_id, project_id, key_result_id) per the
PRD's context-collision guardrail (§7).

Guardrail (extends §7, not in the PRD's schema but required by the same
principle): responsible_id must be a person whose organization_id matches
the project's organization_id, OR a person of type "internal" (crosses every
organization -- the PM/consultant case). This is what stops a person from one
organization ending up responsible for another organization's action plan.

Beyond the PRD: `origin` (plan/meeting/request/internal) and a reschedule
counter survive from the source system this was modeled on. They cost nothing
the PRD asks for and `summary` is what turns them into the
planned-vs-actual-vs-emergent report.

Arquivo: /var/lib/hermes/pm/action_plans.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import tempfile
from pathlib import Path

PM_DIR = Path(os.environ.get("PM_DIR", "/var/lib/hermes/pm"))
ACTION_PLANS = PM_DIR / "action_plans.md"

STATUS = ("not_started", "in_progress", "blocked", "completed", "cancelled")
ORIGINS = ("plan", "meeting", "request", "internal")
DETAIL_FIELDS = ("organization_id", "key_result_id", "why", "who", "when",
                  "where", "how", "how_much", "origin", "rescheduled_count",
                  "evidence", "created_at", "updated_at", "completed_at")

HEADER = """# Action Plans

The single base. One line per plan; views are queries over this file.
Edited only by scripts/action_plans.py -- never by hand.
"""

LINE = re.compile(
    r"^- \[(?P<mark>[ x])\] (?P<id>action_\d+) · (?P<what>.+?) · "
    r"responsible:(?P<responsible_id>\S+) · project:(?P<project_id>\S+)"
    r"(?: due_date:(?P<due_date>\S+))? status:(?P<status>\S+)$"
)
DETAIL = re.compile(r"^ {6}(?P<key>[a-z_]+): (?P<value>.*)$")


def refuse(msg: str) -> None:
    print(f"refusing: {msg}", file=sys.stderr)
    sys.exit(1)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> dt.date:
    return dt.date.today()


def parse_date(value: str, field: str) -> str:
    if value in ("", "-", None):
        return ""
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        refuse(f"{field} must be an ISO date (YYYY-MM-DD), got '{value}'")


# ----------------------------------------------------- entities (guardrail)

def frontmatter(folder: str, entity_id: str) -> dict | None:
    p = PM_DIR / folder / f"{entity_id}.md"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    _, fm, _ = text.split("---\n", 2)
    data = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data


def check_responsible(responsible_id: str, project_id: str) -> None:
    """responsible_id must be internal, or share the project's organization.

    Refuses rather than warns: an action plan assigned to the wrong
    organization's person leaks one client's work into another's, and a
    warning in output nobody reads does not prevent that.
    """
    person = frontmatter("people", responsible_id)
    if person is None:
        refuse(
            f"person '{responsible_id}' is not registered. Create it first:\n"
            f"  entities.py create person \"<Name>\" --id {responsible_id} "
            f"--field organization_id=<org_id> --field type=<internal|external>"
        )
    project = frontmatter("projects", project_id)
    if project is None:
        refuse(
            f"project '{project_id}' is not registered. Create it first:\n"
            f"  entities.py create project \"<Name>\" --id {project_id} "
            f"--field organization_id=<org_id>"
        )

    if person.get("type") == "internal":
        return

    person_org = person.get("organization_id", "")
    project_org = project.get("organization_id", "")
    if not project_org:
        refuse(f"project '{project_id}' has no organization_id; cannot validate the responsible person")
    if person_org != project_org:
        refuse(
            f"'{responsible_id}' belongs to {person_org or '?'} and project "
            f"'{project_id}' belongs to {project_org}. Only someone internal, "
            f"or from the project's own organization, can be responsible for it."
        )


# ----------------------------------------------------------------- io

def read() -> tuple[list[dict], list[str]]:
    if not ACTION_PLANS.exists():
        return [], []
    lines = ACTION_PLANS.read_text(encoding="utf-8").splitlines()
    plans, current = [], None
    for i, line in enumerate(lines):
        m = LINE.match(line)
        if m:
            d = m.groupdict()
            d.pop("mark")
            d["line"] = i
            d["end"] = i
            for key in DETAIL_FIELDS:
                d[key] = ""
            d["rescheduled_count"] = "0"
            plans.append(d)
            current = d
            continue
        md = DETAIL.match(line)
        if md and current is not None and md.group("key") in DETAIL_FIELDS:
            current[md.group("key")] = md.group("value")
            current["end"] = i
        elif line.strip():
            current = None
    return plans, lines


def block(d: dict) -> list[str]:
    mark = "x" if d["status"] == "completed" else " "
    head = (f"- [{mark}] {d['id']} · {d['what']} · responsible:{d['responsible_id']} · "
            f"project:{d['project_id']}")
    if d.get("due_date"):
        head += f" due_date:{d['due_date']}"
    head += f" status:{d['status']}"
    lines = [head]
    for key in DETAIL_FIELDS:
        v = d.get(key)
        if v and not (key == "rescheduled_count" and v == "0"):
            lines.append(f"      {key}: {v}")
    return lines


def save(lines: list[str]) -> None:
    PM_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PM_DIR, prefix=".action_plans.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")
        os.replace(tmp, ACTION_PLANS)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def replace(d: dict, lines: list[str]) -> None:
    d["updated_at"] = now()
    lines[d["line"]:d["end"] + 1] = block(d)
    save(lines)


def find(plans: list[dict], plan_id: str) -> dict:
    for d in plans:
        if d["id"] == plan_id:
            return d
    refuse(f"action plan '{plan_id}' not found")


def next_id(plans: list[dict]) -> str:
    used = [int(d["id"].split("_")[1]) for d in plans]
    return f"action_{max(used) + 1 if used else 1}"


def overdue(d: dict) -> bool:
    return bool(d["due_date"]) and dt.date.fromisoformat(d["due_date"]) < today()


def one_line(d: dict) -> str:
    flag = " OVERDUE" if overdue(d) and d["status"] not in ("completed", "cancelled") else ""
    resched = f" rescheduled:{d['rescheduled_count']}x" if d.get("rescheduled_count", "0") != "0" else ""
    return (f"{d['id']} · {d['what']} · {d['responsible_id']} · {d['project_id']} · "
            f"{d['due_date'] or 'no due date'} · {d['status']}{resched}{flag}")


# ---------------------------------------------------------------- commands

def cmd_add(args):
    plans, lines = read()
    if args.status not in STATUS:
        refuse(f"status must be one of: {', '.join(STATUS)}")
    if args.origin and args.origin not in ORIGINS:
        refuse(f"origin must be one of: {', '.join(ORIGINS)}")

    check_responsible(args.responsible, args.project)

    stamp = now()
    d = {
        "id": next_id(plans), "what": args.what,
        "responsible_id": args.responsible, "project_id": args.project,
        "due_date": parse_date(args.due_date or "", "due_date"),
        "status": args.status,
        "organization_id": args.organization or "",
        "key_result_id": args.key_result or "",
        "why": args.why or "", "who": args.who or "", "when": args.when or "",
        "where": args.where or "", "how": args.how or "", "how_much": args.how_much or "",
        "origin": args.origin or "internal", "rescheduled_count": "0",
        "evidence": "",
        "created_at": stamp, "updated_at": stamp, "completed_at": "",
    }
    if not lines:
        lines = HEADER.splitlines() + [""]
    lines.extend(block(d))
    save(lines)
    print(d["id"])


def cmd_show(args):
    plans, _ = read()
    d = find(plans, args.id)
    print(f"{d['id']} · {d['what']}")
    print(f"  who (responsible): {d['responsible_id']}")
    person = frontmatter("people", d["responsible_id"])
    if person:
        print(f"       {person.get('name','')} · {person.get('role','')} · "
              f"{person.get('email','(no email)')}")
    print(f"  where (project): {d['project_id']}" +
          (f" · key_result:{d['key_result_id']}" if d["key_result_id"] else ""))
    print(f"  when (due): {d['due_date'] or 'no due date'}" +
          (f" · rescheduled {d['rescheduled_count']}x" if d.get("rescheduled_count", "0") != "0" else "") +
          (" · OVERDUE" if overdue(d) and d["status"] not in ("completed", "cancelled") else ""))
    for label, key in (("why", "why"), ("who (detail)", "who"), ("when (detail)", "when"),
                        ("where (detail)", "where"), ("how", "how"), ("how much", "how_much")):
        print(f"  {label}: {d[key] or '(not set)'}")
    print(f"  status: {d['status']} · origin: {d['origin']}")
    if d.get("evidence"):
        print(f"  evidence: {d['evidence']}")


def cmd_complete(args):
    plans, lines = read()
    d = find(plans, args.id)
    d["status"] = "completed"
    d["completed_at"] = now()
    if args.evidence:
        d["evidence"] = args.evidence
    replace(d, lines)


def cmd_cancel(args):
    plans, lines = read()
    d = find(plans, args.id)
    d["status"] = "cancelled"
    replace(d, lines)


def cmd_status(args):
    if args.status not in STATUS:
        refuse(f"status must be one of: {', '.join(STATUS)}")
    plans, lines = read()
    d = find(plans, args.id)
    d["status"] = args.status
    if args.status == "completed":
        d["completed_at"] = now()
    replace(d, lines)


def cmd_reschedule(args):
    plans, lines = read()
    d = find(plans, args.id)
    new_date = parse_date(args.due_date, "due_date")
    if new_date == d["due_date"]:
        refuse(f"{args.id} already has due_date {new_date}")
    d["due_date"] = new_date
    d["rescheduled_count"] = str(int(d.get("rescheduled_count", "0") or "0") + 1)
    replace(d, lines)
    print(f"{args.id} rescheduled {d['rescheduled_count']}x")


def cmd_reassign(args):
    plans, lines = read()
    d = find(plans, args.id)
    check_responsible(args.responsible, d["project_id"])
    d["responsible_id"] = args.responsible
    replace(d, lines)


def cmd_edit(args):
    plans, lines = read()
    d = find(plans, args.id)
    for field in ("what", "why", "who", "when", "where", "how", "how_much",
                  "evidence", "key_result"):
        v = getattr(args, field)
        if v is not None:
            d["key_result_id" if field == "key_result" else field] = v
    replace(d, lines)


def cmd_list(args):
    plans, _ = read()
    if not args.include_completed:
        plans = [d for d in plans if d["status"] not in ("completed", "cancelled")]
    if args.responsible:
        plans = [d for d in plans if d["responsible_id"] == args.responsible]
    if args.project:
        plans = [d for d in plans if d["project_id"] == args.project]
    if args.key_result:
        plans = [d for d in plans if d["key_result_id"] == args.key_result]
    if args.organization:
        plans = [d for d in plans if d["organization_id"] == args.organization]
    if args.overdue:
        plans = [d for d in plans if overdue(d)]
    if args.today:
        plans = [d for d in plans if d["due_date"] == today().isoformat()]
    if args.week:
        end = today() + dt.timedelta(days=7)
        plans = [d for d in plans
                 if d["due_date"] and today() <= dt.date.fromisoformat(d["due_date"]) <= end]
    if args.blocked:
        plans = [d for d in plans if d["status"] == "blocked"]
    if args.emergent:
        plans = [d for d in plans if d["origin"] != "plan"]
    if args.rescheduled:
        plans = [d for d in plans if int(d.get("rescheduled_count", "0") or "0") >= args.rescheduled]

    plans.sort(key=lambda d: (d["due_date"] or "9999-99-99", d["id"]))
    if not plans:
        print("(no action plans)")
        return
    for d in plans:
        print(one_line(d))


def cmd_summary(args):
    plans, _ = read()
    if args.project:
        plans = [d for d in plans if d["project_id"] == args.project]
    if not plans:
        print("(no action plans)")
        return
    planned = [d for d in plans if d["origin"] == "plan"]
    emergent = [d for d in plans if d["origin"] != "plan"]
    planned_done = [d for d in planned if d["status"] == "completed"]
    late = [d for d in plans if d["status"] not in ("completed", "cancelled") and overdue(d)]
    rescheduled = [d for d in plans if int(d.get("rescheduled_count", "0") or "0") >= 2]

    print(f"planned: {len(planned_done)}/{len(planned)} completed")
    print(f"emergent: {len(emergent)} (not in the original plan)")
    print(f"overdue: {len(late)}")
    for d in late:
        days = (today() - dt.date.fromisoformat(d["due_date"])).days
        print(f"  {d['id']} · {d['what']} · {d['responsible_id']} · {days}d overdue")
    if rescheduled:
        print(f"rescheduled 2x or more: {len(rescheduled)}")
        for d in rescheduled:
            print(f"  {d['id']} · {d['what']} · {d['responsible_id']} · {d['rescheduled_count']}x")


def build_parser():
    p = argparse.ArgumentParser(prog="action_plans.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("add", help="creates an action plan in 5W2H (prints its id)")
    sp.add_argument("what")
    sp.add_argument("--responsible", required=True, help="person id")
    sp.add_argument("--project", required=True, help="project id")
    sp.add_argument("--organization", help="organization id (defaults from the project if omitted)")
    sp.add_argument("--key-result", dest="key_result", help="key result id this plan serves")
    sp.add_argument("--due-date", dest="due_date")
    sp.add_argument("--why")
    sp.add_argument("--who", help="prose elaboration beyond the responsible id")
    sp.add_argument("--when", help="prose elaboration beyond the due date")
    sp.add_argument("--where")
    sp.add_argument("--how")
    sp.add_argument("--how-much", dest="how_much")
    sp.add_argument("--status", default="not_started")
    sp.add_argument("--origin", default="internal")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("show", help="the full 5W2H of one action plan")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("complete")
    sp.add_argument("id")
    sp.add_argument("--evidence", help="what the owner said that confirms this is done")
    sp.set_defaults(func=cmd_complete)

    sp = sub.add_parser("cancel")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_cancel)

    sp = sub.add_parser("status")
    sp.add_argument("id")
    sp.add_argument("status")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("reschedule", help="new due date; increments the counter")
    sp.add_argument("id")
    sp.add_argument("due_date")
    sp.set_defaults(func=cmd_reschedule)

    sp = sub.add_parser("reassign")
    sp.add_argument("id")
    sp.add_argument("responsible")
    sp.set_defaults(func=cmd_reassign)

    sp = sub.add_parser("edit")
    sp.add_argument("id")
    sp.add_argument("--what")
    sp.add_argument("--why")
    sp.add_argument("--who")
    sp.add_argument("--when")
    sp.add_argument("--where")
    sp.add_argument("--how")
    sp.add_argument("--how-much", dest="how_much")
    sp.add_argument("--evidence")
    sp.add_argument("--key-result", dest="key_result")
    sp.set_defaults(func=cmd_edit)

    sp = sub.add_parser("list", help="the views")
    sp.add_argument("--responsible")
    sp.add_argument("--project")
    sp.add_argument("--key-result", dest="key_result")
    sp.add_argument("--organization")
    sp.add_argument("--overdue", action="store_true")
    sp.add_argument("--today", action="store_true")
    sp.add_argument("--week", action="store_true")
    sp.add_argument("--blocked", action="store_true")
    sp.add_argument("--emergent", action="store_true")
    sp.add_argument("--rescheduled", type=int)
    sp.add_argument("--include-completed", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("summary", help="planned vs. completed vs. emergent")
    sp.add_argument("--project")
    sp.set_defaults(func=cmd_summary)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
