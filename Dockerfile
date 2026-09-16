# PM Agent -- persistent project-management agent, built on the official
# Plow base image. Pin by immutable sha; check for a newer tag with the
# command in README.md > "Base image" before the final build.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-8088c7f77f5ffd536a80c9dc302ebdb39e6be1d2@sha256:26d69e81faebc584a4d819f68f756e2d4917938409b0f8ff98488c93bdd34b78

# Identity: plow-init recomposes SOUL.md on every boot from the base persona
# plus this file. Never write /var/lib/hermes/SOUL.md directly -- overwritten at boot.
COPY --chmod=0644 persona.md /opt/hermes/plow-seed/persona.md

# Skills, outside any home -- the runtime reconciles them into the agent's
# home at boot, and an image update reaches a skill the owner never customized.
COPY skills/pm-setup/        /opt/hermes/skills/pm-setup/
COPY skills/pm-entities/     /opt/hermes/skills/pm-entities/
COPY skills/pm-action-plans/ /opt/hermes/skills/pm-action-plans/
COPY skills/pm-crons/        /opt/hermes/skills/pm-crons/
RUN find /opt/hermes/skills/pm-setup /opt/hermes/skills/pm-entities \
         /opt/hermes/skills/pm-action-plans /opt/hermes/skills/pm-crons \
         -mindepth 1 -type d -exec chmod 0755 {} + \
 && find /opt/hermes/skills/pm-setup /opt/hermes/skills/pm-entities \
         /opt/hermes/skills/pm-action-plans /opt/hermes/skills/pm-crons \
         -mindepth 1 -type f ! -perm -u+x -exec chmod 0644 {} + \
 && find /opt/hermes/skills/pm-setup /opt/hermes/skills/pm-entities \
         /opt/hermes/skills/pm-action-plans /opt/hermes/skills/pm-crons \
         -mindepth 1 -type f -perm -u+x -exec chmod 0755 {} +

# Agent Index usage reporter -- fetched at build time from the commit
# vendor/client.pin names, checked against the hash beside it. Fetched
# rather than vendored because plow-pbc/agent-index-client owns that file.
COPY vendor/client.pin /opt/plow/agent-index-client.pin
RUN set -eu; \
    sha="$(sed -n 's/^sha=//p' /opt/plow/agent-index-client.pin)"; \
    want="$(sed -n 's/^sha256=//p' /opt/plow/agent-index-client.pin)"; \
    path="$(sed -n 's/^path=//p' /opt/plow/agent-index-client.pin)"; \
    curl -fsS --max-time 60 -o /opt/plow/agent-index-client.py \
      "https://raw.githubusercontent.com/plow-pbc/agent-index-client/${sha}/${path}"; \
    got="$(sha256sum /opt/plow/agent-index-client.py | cut -d' ' -f1)"; \
    [ "$got" = "$want" ] || { echo "agent-index client is $got, pin says $want" >&2; exit 1; }; \
    chmod 0644 /opt/plow/agent-index-client.py

COPY image/s6-overlay/ /etc/s6-overlay/
