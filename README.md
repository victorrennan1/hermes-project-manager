# PM Agent — persistent project-management agent (Plow / Hermes)

A project-management agent that holds context across every organization and
project you're running — cascades each objective into Key Results you
confirm and Action Plans in 5W2H, tracks who's responsible for what, and
proactively tells you what needs attention. Talks over iMessage via Plow
Chat.

**No Mac required.** Runs in Docker on any Linux host — a VPS, WSL2 on
Windows, or plain Linux.

Built on the official [`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent)
image (Hermes Agent, Nous Research, + the Plow integration). This repo adds
only the persona and four skills: `pm-setup`, `pm-entities`,
`pm-action-plans`, `pm-crons`.

## Prerequisites

Git, Docker, Docker Compose v2. An iPhone, to receive the activation code and
talk to the agent.

## Where to run it

A VPS, not your laptop. The daily/weekly routines and the ability to respond
whenever you text are the point — an agent that only runs while your laptop
is open loses both the moment you close the lid.

## Installation

Each person running this uses their **own** Plow account — the credential is
tied to one phone line, so it can't be shared:

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"

git clone https://github.com/victorrennan1/hermes-project-manager.git
cd hermes-project-manager

plow-agents login --new-line   # texts an activation code to YOUR phone;
                                # --new-line avoids landing on a line another
                                # agent already occupies
plow-agents lines               # note the line's phone number
plow-agents mint <the-new-line> # writes ./plow-credentials
```

```sh
docker compose up --build -d
docker compose logs -f agent    # wait for "plow-init: configured ... as cht_"
```

Text the line's phone number once it's up. Say hi — onboarding takes it from
there.

To tear down and free the line:

```sh
plow-agents revoke
docker compose down -v
```

## Base image

The Dockerfile pins an immutable tag. To check for a newer one before a final
build:

```sh
token=$(curl -fsSL 'https://public.ecr.aws/token/?service=public.ecr.aws&scope=repository:e1h7x4a2/plow-cloud-agents:pull' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -fsSL -H "Authorization: Bearer $token" \
  https://public.ecr.aws/v2/e1h7x4a2/plow-cloud-agents/tags/list
```

If `docker compose up` fails pulling the base image with a 403:
`docker logout public.ecr.aws`, then retry.

## Agent Index (hackathon leaderboard)

The usage reporter ships in the Plow base image (reports every 5 min — day x
model token counts only, never conversation content) and reads its
`AGENT_ID` from `compose.yml`'s default, so every install's usage counts
toward the same agent.

Registering the page (once, as the agent's owner):

```sh
curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/main/standalone/agent_index_client.py
set -a; . ./plow-credentials; set +a
python3 agent_index_client.py --register --agent pm-second-brain \
  --name "PM Agent" \
  --blurb "Persistent project-management agent: cascades objectives into Key Results and 5W2H action plans, over chat."
```

After that, in the agent's page on `aiworthusing.com/agent-index`, click
**"Get my agent verified."**

## Repository layout

```
persona.md                          identity, guardrails, tone
skills/pm-setup/                    onboarding (user.md) + project discovery
skills/pm-entities/                 organizations, projects, people, key results
skills/pm-action-plans/             the 5W2H action-plan base
skills/pm-crons/                    owner-configurable scheduled routines
```

## Data model

```
organizations/<org_id>.md
projects/<project_id>.md      objective + Key Results live in the body
people/<person_id>.md
action_plans.md               the single base -- one line + 5W2H detail per plan
user.md                       identity from onboarding, immutable after setup
projects.md                   generated portfolio index -- never hand-edited
```

Every entity has a stable, type-prefixed id (`org_`, `project_`, `person_`,
`kr_`, `action_`) and explicit parent references, so an Action Plan always
knows which organization, project, and Key Result it serves. A guardrail
refuses to let a person responsible for one organization's work end up
responsible for another's, unless they're marked `internal`.

## Roadmap (not in this version)

- Meeting-transcript processing (propose changes from a transcript, owner
  approves, then apply)
- Outbound email chasing (blocked upstream on a Plow mailbox provisioning
  issue for this line; the code path is otherwise ready)
- A quality gate validating submitted deliverables against a template
