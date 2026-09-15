#!/usr/bin/env python3
"""CLI para o estado de um projeto de consultoria (skill pm-memory).

Uso: pm_state.py <slug-do-projeto> <comando> [args]

Um arquivo JSON por projeto em /var/lib/hermes/pm/<slug>.json. Escrita
atômica (arquivo temporário + rename) para nunca deixar o estado
corrompido no meio de uma escrita.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

STATE_DIR = Path("/var/lib/hermes/pm")
VALID_STATUS = {"pendente", "em-andamento", "concluido", "atrasado"}


def refuse(msg: str) -> None:
    print(f"refusing: {msg}", file=sys.stderr)
    sys.exit(1)


def state_path(slug: str) -> Path:
    return STATE_DIR / f"{slug}.json"


def load(slug: str) -> dict:
    path = state_path(slug)
    if not path.exists():
        refuse(f"projeto '{slug}' não existe. Use 'init' primeiro.")
    return json.loads(path.read_text(encoding="utf-8"))


def save(slug: str, data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(slug)
    fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, prefix=f".{slug}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def next_kr_id(data: dict) -> str:
    return f"kr{len(data['key_results']) + 1}"


def next_action_id(kr: dict) -> str:
    return f"{kr['id']}-a{len(kr['actions']) + 1}"


def find_kr(data: dict, kr_id: str) -> dict:
    for kr in data["key_results"]:
        if kr["id"] == kr_id:
            return kr
    refuse(f"resultado-chave '{kr_id}' não encontrado")


def find_action(data: dict, action_id: str):
    for kr in data["key_results"]:
        for a in kr["actions"]:
            if a["id"] == action_id:
                return kr, a
    refuse(f"ação '{action_id}' não encontrada")


def cmd_show(args):
    print(json.dumps(load(args.slug), ensure_ascii=False, indent=2))


def cmd_init(args):
    if state_path(args.slug).exists():
        refuse(f"projeto '{args.slug}' já existe")
    save(args.slug, {
        "slug": args.slug,
        "scope": args.scope,
        "objective": args.objective,
        "key_results": [],
        "emergent_demands": [],
    })


def cmd_add_key_result(args):
    data = load(args.slug)
    kr_id = next_kr_id(data)
    data["key_results"].append({
        "id": kr_id, "text": args.text, "priority": "normal", "actions": [],
    })
    save(args.slug, data)
    print(kr_id)


def cmd_add_action(args):
    data = load(args.slug)
    kr = find_kr(data, args.kr_id)
    action_id = next_action_id(kr)
    kr["actions"].append({
        "id": action_id,
        "what": args.what, "who": args.who, "when": args.when,
        "how": args.how, "where": args.where, "why": args.why,
        "how_much": args.how_much,
        "status": "pendente",
    })
    save(args.slug, data)
    print(action_id)


def cmd_update_status(args):
    if args.status not in VALID_STATUS:
        refuse(f"status inválido '{args.status}'. Use um de: {', '.join(sorted(VALID_STATUS))}")
    data = load(args.slug)
    _, action = find_action(data, args.action_id)
    action["status"] = args.status
    save(args.slug, data)


def cmd_log_emergent(args):
    data = load(args.slug)
    data["emergent_demands"].append(args.text)
    save(args.slug, data)


def cmd_reprioritize(args, level):
    data = load(args.slug)
    find_kr(data, args.kr_id)["priority"] = level
    save(args.slug, data)


def build_parser():
    p = argparse.ArgumentParser(prog="pm_state.py")
    p.add_argument("slug", help="identificador do projeto")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("show").set_defaults(func=cmd_show)

    sp = sub.add_parser("init")
    sp.add_argument("--scope", required=True)
    sp.add_argument("--objective", required=True)
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add-key-result")
    sp.add_argument("text")
    sp.set_defaults(func=cmd_add_key_result)

    sp = sub.add_parser("add-action")
    sp.add_argument("kr_id")
    sp.add_argument("--what", required=True)
    sp.add_argument("--who", required=True)
    sp.add_argument("--when", required=True)
    sp.add_argument("--how", default="")
    sp.add_argument("--where", default="")
    sp.add_argument("--why", default="")
    sp.add_argument("--how-much", dest="how_much", default="")
    sp.set_defaults(func=cmd_add_action)

    sp = sub.add_parser("update-status")
    sp.add_argument("action_id")
    sp.add_argument("status")
    sp.set_defaults(func=cmd_update_status)

    sp = sub.add_parser("log-emergent")
    sp.add_argument("text")
    sp.set_defaults(func=cmd_log_emergent)

    sp = sub.add_parser("prioritize")
    sp.add_argument("kr_id")
    sp.set_defaults(func=lambda a: cmd_reprioritize(a, "alta"))

    sp = sub.add_parser("deprioritize")
    sp.add_argument("kr_id")
    sp.set_defaults(func=lambda a: cmd_reprioritize(a, "baixa"))

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
