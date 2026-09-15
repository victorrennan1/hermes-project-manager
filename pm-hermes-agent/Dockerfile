# PM Second Brain -- agente de PM de consultoria, construído sobre a imagem
# oficial do Plow. Pin por sha imutável: confira se há uma tag mais recente
# com o comando no README (seção "Base image") antes da build final.
FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-8088c7f77f5ffd536a80c9dc302ebdb39e6be1d2@sha256:26d69e81faebc584a4d819f68f756e2d4917938409b0f8ff98488c93bdd34b78

# Identidade: plow-init recompõe o SOUL.md em todo boot como a persona base +
# este arquivo. Nunca copiar para /var/lib/hermes/SOUL.md -- é sobrescrito no boot.
COPY --chmod=0644 persona.md /opt/hermes/plow-seed/persona.md

# Skills, fora de qualquer home -- o runtime as reconcilia para dentro da home
# do agente no boot, e uma atualização de imagem alcança uma skill não
# customizada pelo dono.
COPY skills/pm-memory/ /opt/hermes/skills/pm-memory/
RUN find /opt/hermes/skills/pm-memory -mindepth 1 -type d -exec chmod 0755 {} + \
 && find /opt/hermes/skills/pm-memory -mindepth 1 -type f ! -perm -u+x -exec chmod 0644 {} + \
 && find /opt/hermes/skills/pm-memory -mindepth 1 -type f -perm -u+x -exec chmod 0755 {} +

# Reporter de uso para o Agent Index -- buscado no build a partir do commit
# que vendor/client.pin nomeia, e checado contra o hash ao lado. Buscado em vez
# de versionado porque plow-pbc/agent-index-client é quem possui esse arquivo.
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
