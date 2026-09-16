---
name: pm-entities
description: Organizations, Projects (with objective and Key Results), and People. Use whenever the owner mentions an organization, a new project, a project's objective, a Key Result, or a person — "a organização X", "novo projeto em Y", "o objetivo é...", "resultado-chave:", "o João é de tal organização" — or whenever you need a person's role or email before assigning them an action plan.
---

# Entities — organizations, projects, people, key results

Four kinds of record, one markdown file each, linked by id:

    /var/lib/hermes/pm/organizations/<org_id>.md
    /var/lib/hermes/pm/projects/<project_id>.md      objective + Key Results live here
    /var/lib/hermes/pm/people/<person_id>.md
    /var/lib/hermes/pm/projects.md                    generated index -- never hand-edit

The CLI, by absolute path:

    /var/lib/hermes/skills/pm-entities/scripts/entities.py <command> [args]

**Never edit these files with your file tools.** Every field has a command.
A free-form edit is how a Key Result silently disappears or the frontmatter
breaks, and the failure shows up turns later as an empty query — not now,
where you could catch it.

## Commands

    create <organization|project|person> "<Name>" [--id <id>] [--field key=value ...]
    show <type> <id>
    set <type> <id> <field> <value>
    list [<type>] [--organization <org_id>] [--status <status>]
    related <id>                          everything that references an entity
    reindex                               regenerate projects.md from projects/*.md

    kr add <project_id> "<title>"         records an OWNER-CONFIRMED Key Result (prints its id)
    kr status <project_id> <kr_id> <not_started|in_progress|completed|dropped>
    kr list <project_id>

IDs are type-prefixed and stable: `org_<slug>`, `project_<slug>`,
`person_<slug>`, `kr_<n>`. They never change even if the name later does.

## Fields

**organization** — `name`, `metadata`, `created_at`, `updated_at`

**project** — `name`, `organization_id` (required), `objective`, `status`
(planned|active|paused|completed), `created_at`, `updated_at`

**person** — `name`, `organization_id`, `type` (internal|external), `role`,
`email`, `metadata`, `created_at`, `updated_at`. `organization_id` is
required **unless** `type=internal`.

`type=internal` means this person works across every organization — a
consultant, a PM, the owner themself. `type=external` (the default) scopes
them to one organization. This is what `pm-action-plans`' guardrail checks
before letting someone be responsible for a plan.

`email` matters even though nothing in this skill sends anything: it's what
makes a person chaseable later. Ask for it when it's missing and you're about
to need it.

## Key Results are collaborative, never invented solo

A Key Result is an outcome or state the project's objective needs to exist —
not a task. "Equipe de voluntários formada" is a Key Result. "Mandar
mensagem no grupo" is not — that is an Action Plan that serves the Key
Result above it.

**Propose, then let the owner confirm.** For a new project's objective, ask
something like: "Para alcançar <objective>, quais resultados você acredita
que precisamos atingir?" You may suggest candidates to help them think it
through, but `kr add` records what the owner agreed to, not your first draft
of it. Never populate a project's whole Key Result set unilaterally.

## Objective

`objective` is a short field, not a document — a sentence the project's Key
Results and Action Plans get judged against. If what the owner gave you is
too vague to cascade ("melhorar as coisas"), ask once for the specific
outcome before creating the project.

## Before creating

Check first: `list organization`, `list project`. A duplicate under a
slightly different slug splits the record in two — "amentoria" and
"a-mentoria" become two organizations, and half of everything filed against
one is invisible from the other.

## reindex

`projects.md` is the human-readable portfolio index the PRD calls for. It is
generated, never authored — run `reindex` after creating or changing a
project so it doesn't go stale. It is not where mutable state lives; that is
still the individual project files and `action_plans.md`.
