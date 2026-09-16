---
name: pm-action-plans
description: The single Action Plan base -- 5W2H tasks anchored to a project and a Key Result, with a responsible person and a due date. Use whenever the owner talks about a task, commitment, or delivery -- "fulano ficou de", "preciso cobrar", "isso ficou pronto", "o que está atrasado", "o que tenho pra hoje", "o que está pendente com X", "adia para", "passa para outra pessoa", "cancela isso", "como está o projeto Y" -- or when the daily/weekly cron fires.
---

# Action Plans — the 5W2H base

One file, one line per plan plus an indented detail block:
`/var/lib/hermes/pm/action_plans.md`. There is no per-project list — this is
the single base the PRD calls for; every view is a filter over it.

**Never edit this file.** Everything goes through the CLI, by absolute path
(a cron turn's working directory is not this skill's):

    /var/lib/hermes/skills/pm-action-plans/scripts/action_plans.py <command> [args]

Mutating commands print nothing on success except `add` (prints the new id)
and `reschedule` (prints the new count). Failure is `refusing: ...` on
stderr with a non-zero exit — read it, it says what's valid.

## The 5W2H

    add "<what>" --responsible <person_id> --project <project_id> \
        --due-date <YYYY-MM-DD> [--key-result <kr_id>] [--organization <org_id>] \
        [--why "..."] [--who "..."] [--when "..."] [--where "..."] \
        [--how "..."] [--how-much "..."] [--origin plan|meeting|request|internal]

Seven prose dimensions (`what` is the title; `why/who/when/where/how/how_much`
are the detail block) plus two structured, queryable fields that drive every
view: `--responsible` (a real person id) and `--due-date` (a real date).
`--who` and `--when` are elaboration, not substitutes — "João, com apoio do
grupo de jovens" in `--who` says more than the id alone, but the id is what
the guardrail and the views actually use.

**`--how` is not optional in practice.** It's what a chase message sends the
responsible person; without it they get an order with no instruction. If the
owner didn't describe one, propose one from what they told you and confirm —
a suggestion they correct beats an empty field.

`--origin` separates what was in the plan from what came up during
execution, and feeds `summary`. Default is `internal`; use `plan` for
anything that was scoped from the start, `meeting` for what a conversation
produced.

## The views

    list --responsible <person_id>     what's open with one person
    list --overdue                     past due, not done
    list --today / --week
    list --blocked
    list --emergent                    origin != plan
    list --key-result <kr_id>
    list --project <project_id>
    list --rescheduled 2               moved 2+ times
    show <id>                          the full 5W2H, with the person's contact
    summary --project <project_id>     planned vs. completed vs. emergent

## The mutations

    complete <id> [--evidence "<what the owner said>"]
    cancel <id>
    status <id> not_started|in_progress|blocked|completed|cancelled
    reschedule <id> <YYYY-MM-DD>        new due date AND increments the counter
    reassign <id> <person_id>
    edit <id> [--what/--why/--who/--when/--where/--how/--how-much/--evidence/--key-result ...]

**Never change a due date with `edit`.** `reschedule` exists because how many
times something moved is itself a signal — "this has been pushed back three
times" is exactly what the owner needs surfaced, and only the counter tracks
it.

## Resolving a natural-language progress report

"O João me entregou a lista de voluntários" is an update, not a new task.
Before writing anything:

1. `list --responsible <person>` to see their open plans.
2. If exactly one plausible match, that's the target — resolve it, don't
   ask for confirmation on the obvious case.
3. **If more than one open plan could match, stop and ask.** Never guess
   between them. "O João tem duas ações em aberto no projeto Sopão. Você
   está falando da definição dos locais ou da confirmação da equipe?" A
   wrong guess marks the wrong thing done and hides the real one as still
   pending.
4. Once resolved, `complete` (or the right status) with `--evidence` set to
   what the owner actually said — not your paraphrase of it.

## The responsible-person guardrail

`--responsible` must be a person who is `type=internal`, or whose
`organization_id` matches the project's. The CLI refuses on its own — one
organization's person can never end up responsible for another
organization's work.

**When it refuses, do not route around it.** Don't switch the project,
invent a new person, or change someone's type just to get past the check.
Explain the rule to the owner and ask who the responsible person actually
should be. If that person isn't registered yet, create them with
`pm-entities` and retry.

An action plan for an unregistered person is refused the same way, with the
exact creation command in the error — use it rather than guessing an id.

## Every turn that touches an action plan

1. `list` or `show` with the closest matching view — **read before writing**,
   never invent an id.
2. A question: answer from the result and stop. Change nothing.
3. A mutation: apply it, confirm in one line what changed.
4. Keep it short. The owner is on a phone, between things — don't dump the
   whole base when they asked about one thing.

## What requires approval first

Changes proposed from a meeting transcript are never applied directly — that
protocol belongs to whichever skill processes transcripts, not this one. A
direct instruction from the owner ("marca a action_12 como concluída") is the
owner deciding — apply it and confirm, no extra confirmation needed.
