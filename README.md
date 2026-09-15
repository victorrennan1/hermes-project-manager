# PM Second Brain — agente de PM de consultoria (Plow / Hermes)

Agente de Project Manager que cascateia Escopo → Objetivos (OKR/SMART) →
Resultados-Chave → Planos de Ação (5W2H), distingue demandas primárias de
emergentes, e mantém isso como estado vivo e rastreável — conversando por
iMessage via Plow Chat.

Construído sobre a imagem oficial [`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent)
(Hermes Agent, da Nous Research, + a integração Plow). Este repo só adiciona
a persona (`persona.md`) e a skill `pm-memory`.

## Pré-requisitos

Git, Docker, Docker Compose v2. Nenhum Mac necessário — roda em qualquer
Linux (VPS inclusive), via Plow Chat / iMessage.

## Instalação

Cada pessoa que for rodar este agente usa a **própria** conta Plow (a
credencial é presa a uma linha/telefone):

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"

git clone <URL-DESTE-REPO>
cd <pasta-deste-repo>

plow-agents login          # texta o código de ativação impresso pro seu telefone
plow-agents lines          # lista as linhas disponíveis, escolha uma "free"
plow-agents mint <linha>   # escreve ./plow-credentials
```

**Passo extra pra contar no leaderboard deste agente** (veja "Agent Index"
abaixo pelo porquê): adicione ao `./plow-credentials` recém-criado:

```sh
echo "AGENT_ID=<id-registrado-abaixo>" >> plow-credentials
```

Depois:

```sh
docker compose up --build -d
docker compose logs -f agent   # espere aparecer "plow-init: configured ... as cht_"
```

Quando aparecer, texte para o número da linha escolhida — o agente responde.

Pra encerrar e limpar a memória local:

```sh
plow-agents revoke
docker compose down -v
```

## Primeira mensagem

```
novo projeto: Estruturação Financeira
escopo: aumentar a governança e transparência das finanças
objetivo: fechamento contábil com 95% de acurácia
```

O agente deve criar o projeto, cascatear em resultado-chave + plano de ação
5W2H, e confirmar em poucas linhas.

## Base image

Este Dockerfile fixa uma tag imutável (`base-<sha>`) da imagem oficial. Pra
conferir se existe uma mais recente antes da build final:

```sh
token=$(curl -fsSL 'https://public.ecr.aws/token/?service=public.ecr.aws&scope=repository:e1h7x4a2/plow-cloud-agents:pull' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -fsSL -H "Authorization: Bearer $token" \
  https://public.ecr.aws/v2/e1h7x4a2/plow-cloud-agents/tags/list
```

Se `docker compose up` falhar puxando a imagem base com erro 403: `docker
logout public.ecr.aws` e tente de novo (credencial de pull anônima expirada).

## Agent Index (leaderboard do hackathon)

O reporter de uso já vem embutido na imagem (roda a cada 5 min, só manda
contagem agregada por dia/modelo — nada de conteúdo de conversa). Ele só
sabe de quem é o uso através de `AGENT_ID`, presente no ambiente do
container.

**Registro (fazer uma única vez, como dono deste agente):**

```sh
curl -O https://raw.githubusercontent.com/plow-pbc/agent-index-client/main/standalone/agent_index_client.py
set -a; . ./plow-credentials; set +a
python3 agent_index_client.py --register --agent "<escolha-um-id>" --name "PM Second Brain" --blurb "Second brain de PM para consultoria: cascateia OKR em planos de ação 5W2H via chat"
```

Anote o `<escolha-um-id>` — é o `AGENT_ID` que você (e todo mundo que
instalar este repo) coloca no próprio `plow-credentials`, conforme o passo
de instalação acima. Assim o uso de terceiros conta pro mesmo agente no
[leaderboard](https://aiworthusing.com/agent-index).

**Depois de registrar, entre na página do seu agente no Agent Index e clique
em "Get my agent verified".** Sem isso ele não conta pro ranking, mesmo
reportando uso normalmente.

**Requisitos pra rankear**, segundo o próprio Agent Index: repositório MIT
licensed (feito — `LICENSE`), agente verificado (passo acima), e reportando
uso através do client oficial (feito — `vendor/client.pin` +
`image/s6-overlay/`).

## Roadmap (fora do escopo desta v1)

- Quality gate: validar entregas submetidas contra um template
- Cron jobs: status diário, atrasos, radar dos próximos dias
- Ingestão de transcrições de reunião
- Envio automático de lembretes por e-mail

## Estrutura

```
persona.md                    identidade do agente
skills/pm-memory/SKILL.md      protocolo: quando e como cascatear/atualizar
skills/pm-memory/scripts/      CLI que lê/escreve o estado (JSON por projeto)
vendor/client.pin              pin do reporter de uso (Agent Index)
image/s6-overlay/              serviço do reporter (copiado do agente de referência)
```
