# PM Agent -- persistent project-management agent, built on the official
# Plow base image. Pin by immutable sha; check for a newer tag with the
# command in README.md > "Base image" before the final build.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-ef0019372ff8bca593611b31ebd2e08f9f1458ff@sha256:a8a2f97ad78b8192d80a984dce81d3bf5a9a883d18cb7b677704913a09b56aee

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

