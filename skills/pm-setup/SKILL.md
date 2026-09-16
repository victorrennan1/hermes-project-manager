---
name: pm-setup
description: One-time onboarding (name, location, language) and the project-discovery conversation that follows it. Use on the very first message ever, whenever /var/lib/hermes/pm/user.md does not exist yet -- and use the discovery half whenever the owner wants to add a new project or organization later ("tenho mais um projeto", "esqueci de mencionar um projeto", "novo projeto:"). Never re-run onboarding once user.md exists; that half is one-time only.
---

# Setup: identity, then projects

Two phases, run once each per owner, plus a reusable discovery loop.

## Phase 1 — Onboarding (once, ever)

Check first: `/var/lib/hermes/skills/pm-setup/scripts/setup.py user show`. If it
prints real fields, onboarding already happened — skip straight to Phase 2
only if there are zero projects yet (`entities.py list project`), otherwise
this skill is not the right one for the current message.

If it says "no user.md yet," ask these three, in order, **one at a time,
never as a list**:

1. Name — "Qual é o seu nome?"
2. Location — "De onde você está falando?" (city is enough; used only to set
   your timezone, not as small talk)
3. Language — "Prefere que eu fale em português ou inglês?" → store exactly
   `pt-BR` or `en`

When all three are answered:

    /var/lib/hermes/skills/pm-setup/scripts/setup.py user init \
      --name "<name>" --location "<location>" --language <pt-BR|en>

Then, **in the same turn**, derive the IANA timezone yourself from the
location they gave (you know world geography; this script does not call any
geocoding service) and register it:

    /var/lib/hermes/skills/pm-crons/scripts/crons.py fuso <IANA-zone>

`user.md` is written once. Never call `init` a second time — it refuses on
purpose. A later change to name, location, or language is a deliberate
settings action, not part of any normal conversation:

    setup.py user update user_name "<new value>"
    setup.py user update user_location "<new value>"   # also re-run crons.py fuso
    setup.py user update language <pt-BR|en>

Immediately after `init`, move to Phase 2 in the same reply — do not wait for
the owner to ask.

## Phase 2 — Project discovery

Ask exactly: **"No que você está trabalhando hoje?"** (or its English form,
per `language`). Let them answer in free text — never a form.

From their answer, extract what you can and ask only for what's missing, one
question at a time:

- **Organization** — "Em qual organização esse projeto está sendo
  realizado?" Reuse an existing one (`entities.py list organization`) rather
  than creating a near-duplicate; ask which they mean if a name is close but
  not exact.
- **Project name** — "Qual é o nome específico desse projeto?"
- **Objective** — "Qual é o objetivo específico que você quer alcançar com
  ele?" Push back once, gently, if it is too vague to plan against ("reduzir
  o tempo de atendimento" is specific enough; "melhorar as coisas" is not).

Once you have all three:

    entities.py create organization "<name>"        # only if it doesn't exist yet
    entities.py create project "<name>" \
      --field organization_id=<org_id> --field objective="<objective>"
    entities.py reindex

Then ask: **"Você tem mais algum projeto?"** On yes, repeat this whole
discovery block for the next one. On no, move to selection:

> "Perfeito. Podemos começar pelo projeto <first project captured>?"

Start cascading that project unless the owner names a different one. "First
captured" means the first one this loop created, not the most recently
discussed.

## Handing off to the cascade

Once a project is selected, Key Results and Action Plans are **not** this
skill's job — see `pm-entities` for the collaborative Key Result protocol and
`pm-action-plans` for 5W2H. This skill's work ends at "which project do we
start with."

## What this is not

Not a form, not a survey with a progress bar the owner sees. One question
per message, answer what they actually said before asking the next thing,
and never re-ask something already on file. If an answer covers two
questions at once ("Estou tocando um projeto de organograma na AMentoria"
supplies both project and organization), accept it and skip the question you
already have the answer to.

Never narrate the mechanics ("ok, salvando isso", "agora vou perguntar
sobre..."). Ask the next thing or acknowledge what landed — nothing about
the process itself reaches the owner.
