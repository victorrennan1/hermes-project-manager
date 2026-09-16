#!/usr/bin/env python3
"""As rotinas do agente: o dono escolhe quais e a que horas, por conversa.

Duas coisas que este script existe para resolver:

1. `hermes cron` grava em /var/lib/hermes/cron/jobs.json e NADA replica esse
   arquivo num rebuild. Um agente reconstruído sobe sem rotina nenhuma, e a
   falha é silenciosa -- ninguém recebe o briefing e não há erro em lugar
   algum. Por isso as rotinas moram no config, e `registrar` as replica.

2. Um job de cron dispara no fuso do CONTAINER (quase sempre UTC), e
   `hermes cron create` não aceita fuso por job. "9h" para um dono em
   America/Recife é 12:00 UTC. A conversão acontece aqui, na hora de
   registrar, a partir de `timezone` no config.

Config: /var/lib/hermes/pm/config.json
Jobs:   /var/lib/hermes/cron/jobs.json (escrito pelo hermes, lido aqui)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PM_DIR = Path(os.environ.get("PM_DIR", "/var/lib/hermes/pm"))
CONFIG = PM_DIR / "config.json"
HERMES = os.environ.get("HERMES_BIN", "/opt/hermes/bin/hermes")
JOBS_FILE = Path(os.environ.get("HERMES_JOBS", "/var/lib/hermes/cron/jobs.json"))

# O catálogo. O dono escolhe quais ligar e a que horas; o texto do prompt é
# revisado, não improvisado a cada registro.
ROTINAS = {
    "briefing-diario": {
        "descricao": "o quê está atrasado, o quê vence hoje, quem cobrar, o que priorizar",
        "skill": "pm-action-plans",
        "entrega": True,
        "padrao": "07:00",
        "cadencia": "diaria",
        "prompt": (
            "Rode o briefing diário agora. Use a skill pm-action-plans: leia "
            "`list --overdue`, `list --today` e `list --blocked`. "
            "Componha UMA mensagem curta para o dono, nesta ordem e só com as "
            "seções que tiverem conteúdo:\n"
            "🔴 Atrasadas — cada uma com responsável e dias de atraso\n"
            "📅 Para hoje — o que vence hoje, com responsável\n"
            "👥 Vale cobrar — quem tem entrega vencida ou bloqueada\n"
            "🎯 Prioridade — as três coisas que ele deveria tratar hoje, e por quê\n"
            "Escreva como um chefe de gabinete reportando, não como uma lista "
            "de tarefas: uma linha por item, sem ids técnicos, sem preâmbulo. "
            "Se não houver nada em nenhuma seção, responda apenas "
            "'Nada atrasado nem vencendo hoje.' Devolva essa mensagem como "
            "resposta final. Nunca rode setup a partir deste turno."
        ),
    },
    "radar-semanal": {
        "descricao": "o que vem na semana e como cada projeto está contra o plano",
        "skill": "pm-action-plans",
        "entrega": True,
        "padrao": "08:00",
        "cadencia": "semanal",
        "dia_semana": 1,  # segunda
        "prompt": (
            "Rode o radar semanal agora. Use a skill pm-action-plans: leia "
            "`list --week` e, para cada projeto ativo (veja pm-entities "
            "`list project --status active`), `summary --project <id>`. "
            "Componha UMA mensagem para o dono com:\n"
            "📅 A semana — o que vence nos próximos 7 dias, agrupado por projeto\n"
            "📊 Cada projeto contra o plano — planejadas concluídas, quantas "
            "emergentes surgiram, o que foi reaprazado mais de uma vez\n"
            "⚠️ O que merece pauta — o que levar para a próxima reunião de cada "
            "cliente, e por quê\n"
            "Seja analítico, não descritivo: diga o que os números significam. "
            "Devolva essa mensagem como resposta final. Nunca rode setup a "
            "partir deste turno."
        ),
    },
    "cobranca": {
        "descricao": "quem está devendo entrega, com o texto pronto para cobrar",
        "skill": "pm-action-plans",
        "entrega": True,
        "padrao": "14:00",
        "cadencia": "diaria",
        "prompt": (
            "Rode a cobrança agora. Use a skill pm-action-plans: leia "
            "`list --overdue`. Para cada pessoa com entrega vencida, leia "
            "`show <id>` para ter o 5W2H completo e o contato dela.\n"
            "Se não houver nada atrasado, responda exatamente 'NO_REPLY' e nada "
            "mais — um dia sem atraso não merece uma mensagem.\n"
            "Havendo atrasos, mande ao dono UMA mensagem: por pessoa, o que "
            "está devendo, há quantos dias, e um texto curto pronto para ele "
            "encaminhar àquela pessoa — incluindo o 'como' da demanda, para a "
            "cobrança chegar com instrução e não só com pressão. Nunca envie "
            "nada a terceiros por conta própria. Nunca rode setup a partir "
            "deste turno."
        ),
    },
}


def refuse(msg: str) -> None:
    print(f"refusing: {msg}", file=sys.stderr)
    sys.exit(1)


def ler_config() -> dict:
    if not CONFIG.exists():
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except ValueError as exc:
        refuse(f"{CONFIG} não é JSON válido ({exc}). Conserte antes de registrar.")


def gravar_config(dados: dict) -> None:
    PM_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PM_DIR, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, CONFIG)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def fuso_do_dono(config: dict) -> ZoneInfo:
    nome = (config.get("timezone") or "").strip()
    if not nome:
        refuse(
            "o config não tem `timezone`. Sem ele não dá para saber que hora "
            "é 09:00 para o dono. Defina com:\n"
            "  crons.py fuso America/Recife"
        )
    try:
        return ZoneInfo(nome)
    except ZoneInfoNotFoundError:
        refuse(f"fuso '{nome}' não existe. Use um nome IANA, ex: America/Recife")


def fuso_do_container() -> ZoneInfo:
    nome = (os.environ.get("TZ") or "UTC").strip() or "UTC"
    try:
        return ZoneInfo(nome)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def converter(hora: str, dono: ZoneInfo, container: ZoneInfo) -> tuple[int, int, int]:
    """(hora, minuto, deslocamento_de_dia) no fuso do container."""
    try:
        h, m = (int(x) for x in hora.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except ValueError:
        refuse(f"hora inválida '{hora}'. Use HH:MM, ex: 09:00")

    hoje = dt.date.today()
    local = dt.datetime(hoje.year, hoje.month, hoje.day, h, m, tzinfo=dono)
    no_container = local.astimezone(container)
    delta = (no_container.date() - local.date()).days
    return no_container.hour, no_container.minute, delta


def expressao(nome: str, rotina: dict, hora: str, config: dict) -> str:
    h, m, delta = converter(hora, fuso_do_dono(config), fuso_do_container())
    if rotina["cadencia"] == "diaria":
        return f"{m} {h} * * *"
    dia = (rotina.get("dia_semana", 1) + delta) % 7
    return f"{m} {h} * * {dia}"


# ------------------------------------------------------------------ hermes

def registrados() -> dict[str, dict]:
    """O que o hermes tem agendado, do arquivo dele.

    Um arquivo ausente é uma agenda vazia. Um arquivo ilegível NÃO é: tratar
    'não consegui ler' como 'não há nada' duplica todo job a cada execução.
    """
    if not JOBS_FILE.exists():
        return {}
    try:
        dados = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        refuse(
            f"não consegui ler {JOBS_FILE} ({exc}). Parando em vez de registrar "
            "por cima — registrar às cegas duplicaria todas as rotinas."
        )
    jobs = dados.get("jobs", dados) if isinstance(dados, dict) else dados
    if not isinstance(jobs, list):
        refuse(f"{JOBS_FILE} tem formato inesperado; não vou registrar às cegas")
    return {j["name"]: j for j in jobs if isinstance(j, dict) and j.get("name")}


def rodar(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def canal() -> str:
    valor = (os.environ.get("PLOW_HOME_CHANNEL") or "").strip()
    if not valor:
        refuse(
            "PLOW_HOME_CHANNEL está vazio neste ambiente. O primeiro boot o "
            "publica depois de perguntar ao Plow qual é a conversa do dono, e "
            "um turno herda esse ambiente do gateway — um `docker exec` direto "
            "não. Rode isto a partir de uma conversa com o agente."
        )
    return valor


# ---------------------------------------------------------------- comandos

def cmd_fuso(args):
    config = ler_config()
    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError:
        refuse(f"fuso '{args.timezone}' não existe. Use um nome IANA, ex: America/Recife")
    config["timezone"] = args.timezone
    gravar_config(config)


def cmd_definir(args):
    if args.rotina not in ROTINAS:
        refuse(f"rotina desconhecida '{args.rotina}'. Disponíveis: {', '.join(ROTINAS)}")
    config = ler_config()
    converter(args.hora, fuso_do_dono(config), fuso_do_container())  # valida cedo
    config.setdefault("rotinas", {})[args.rotina] = {"hora": args.hora, "ativa": True}
    gravar_config(config)
    print(f"{args.rotina} às {args.hora} — rode `registrar` para valer")


def cmd_desligar(args):
    config = ler_config()
    rotinas = config.get("rotinas", {})
    if args.rotina not in rotinas:
        refuse(f"'{args.rotina}' não está configurada")
    rotinas[args.rotina]["ativa"] = False
    gravar_config(config)
    print(f"{args.rotina} desligada — rode `registrar` para valer")


def cmd_listar(args):
    config = ler_config()
    escolhidas = config.get("rotinas", {})
    agendadas = registrados()
    tz = config.get("timezone", "(sem fuso definido)")
    print(f"fuso do dono: {tz} · container: {os.environ.get('TZ') or 'UTC'}")
    for nome, rotina in ROTINAS.items():
        escolha = escolhidas.get(nome)
        if not escolha:
            print(f"  {nome} — não configurada · {rotina['descricao']}")
            continue
        estado = "ativa" if escolha.get("ativa", True) else "desligada"
        no_hermes = "registrada" if nome in agendadas else "NÃO registrada"
        print(f"  {nome} — {escolha['hora']} · {estado} · {no_hermes}")


def cmd_registrar(args):
    if not shutil.which(HERMES) and not os.path.exists(HERMES):
        refuse(f"{HERMES} não existe — rode isto dentro do container do agente")

    config = ler_config()
    escolhidas = config.get("rotinas", {})
    if not escolhidas:
        refuse("nenhuma rotina configurada. Use `definir <rotina> <HH:MM>` primeiro.")
    fuso_do_dono(config)
    agendadas = registrados()
    alvo = canal()
    falhou = False

    for nome, escolha in escolhidas.items():
        rotina = ROTINAS.get(nome)
        if rotina is None:
            print(f"  {nome}: não está no catálogo, ignorando")
            continue

        quer = escolha.get("ativa", True)
        tem = nome in agendadas
        expr = expressao(nome, rotina, escolha["hora"], config) if quer else None

        if not quer:
            if tem:
                r = rodar([HERMES, "cron", "remove", agendadas[nome].get("id", nome)])
                print(f"  {nome}: removida" if r.returncode == 0
                      else f"  {nome}: FALHOU ao remover — {r.stderr.strip()}")
                falhou |= r.returncode != 0
            else:
                print(f"  {nome}: desligada, nada agendado")
            continue

        if tem:
            atual = agendadas[nome].get("schedule", "")
            if atual == expr:
                pausada = agendadas[nome].get("paused_at") or not agendadas[nome].get("enabled", True)
                if pausada:
                    print(f"  {nome}: registrada mas PAUSADA — reative com `hermes cron resume`")
                    falhou = True
                else:
                    print(f"  {nome}: já registrada em {expr}")
                continue
            # O horário mudou: `cron create` não altera uma linha existente.
            r = rodar([HERMES, "cron", "remove", agendadas[nome].get("id", nome)])
            if r.returncode != 0:
                print(f"  {nome}: FALHOU ao remover a versão antiga — {r.stderr.strip()}")
                falhou = True
                continue
            print(f"  {nome}: horário mudou ({atual} → {expr}), recriando")

        argv = [HERMES, "cron", "create", expr, rotina["prompt"], "--name", nome,
                "--skill", rotina["skill"]]
        if rotina["entrega"]:
            argv += ["--deliver", f"plow_chat:{alvo}"]
        r = rodar(argv)
        if r.returncode == 0:
            print(f"  {nome}: registrada em {expr} ({escolha['hora']} do dono)")
        else:
            print(f"  {nome}: FALHOU — {r.stderr.strip()}")
            falhou = True

    if falhou:
        sys.exit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="crons.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="comando", required=True)

    sp = sub.add_parser("fuso", help="define o fuso do dono (IANA)")
    sp.add_argument("timezone")
    sp.set_defaults(func=cmd_fuso)

    sp = sub.add_parser("definir", help="liga uma rotina num horário")
    sp.add_argument("rotina", choices=list(ROTINAS))
    sp.add_argument("hora", help="HH:MM no fuso do dono")
    sp.set_defaults(func=cmd_definir)

    sp = sub.add_parser("desligar")
    sp.add_argument("rotina", choices=list(ROTINAS))
    sp.set_defaults(func=cmd_desligar)

    sp = sub.add_parser("listar", help="o que está configurado e o que está agendado")
    sp.set_defaults(func=cmd_listar)

    sp = sub.add_parser("registrar", help="aplica o config no agendador do hermes")
    sp.set_defaults(func=cmd_registrar)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
