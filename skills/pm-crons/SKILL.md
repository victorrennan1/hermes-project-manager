---
name: pm-crons
description: As rotinas automáticas do agente — briefing diário, radar semanal e cobrança — que o dono liga, desliga e reagenda conversando. Use quando ele falar de rotina, horário, briefing, relatório automático ou lembrete recorrente — "me manda um resumo todo dia às 9", "muda o briefing para as 7", "para de me mandar aquilo", "que rotinas você tem?", "você não me mandou o relatório hoje" — e SEMPRE depois de reconstruir o agente.
---

# Rotinas — o que o agente faz sem ser chamado

Três rotinas, todas opcionais, todas no horário que o dono escolher:

| rotina | o que manda |
|---|---|
| `briefing-diario` | atrasadas, o que vence hoje, quem cobrar, o que priorizar |
| `radar-semanal` | a semana que vem e cada projeto contra o plano |
| `cobranca` | quem está devendo, com texto pronto para encaminhar |

O CLI, por caminho absoluto:

    /var/lib/hermes/skills/pm-crons/scripts/crons.py <comando> [args]

    fuso <IANA>                 ex: America/Recife — obrigatório, uma vez
    definir <rotina> <HH:MM>    liga uma rotina no horário do DONO
    desligar <rotina>
    listar                      o que está configurado e o que está agendado
    registrar                   aplica o config no agendador

## Duas armadilhas que este script existe para evitar

**Um rebuild apaga todas as rotinas.** O `hermes cron` grava em
`/var/lib/hermes/cron/jobs.json`, e nada replica esse arquivo quando a imagem
é reconstruída. O agente sobe, responde normalmente, e simplesmente nunca mais
manda o briefing — sem erro em lugar nenhum. Por isso as rotinas moram no
config e `registrar` as recria. **Rode `registrar` depois de todo rebuild.**

**Um cron dispara no fuso do container, não no do dono.** "9h" registrado
cru chega às 6h para quem está em Natal. O script converte a partir do `fuso`
e recusa registrar sem ele. Se o dono viajar ou mudar de fuso, é `fuso` novo
seguido de `registrar`.

## Como conduzir a conversa

Quando o dono pedir uma rotina e não disser a hora, **pergunte uma vez** — e
sugira: o briefing rende mais antes do primeiro compromisso, a cobrança rende
mais no meio da tarde, quando ainda dá tempo da pessoa entregar no mesmo dia.

Quando ele reclamar que não recebeu, rode `listar` antes de responder. Os
estados que aparecem ali são diferentes e pedem respostas diferentes: *não
configurada* (nunca foi ligada), *NÃO registrada* (configurada mas o
`registrar` não rodou — quase sempre um rebuild), e *PAUSADA* (agendada mas
suspensa; reative com `hermes cron resume`).

`definir` e `desligar` só mexem no config. **Nada vale até `registrar` rodar**
— diga isso ao dono na mesma frase, para ele não achar que já está de pé.

## Rode `registrar` de dentro de uma conversa

O comando precisa de `PLOW_HOME_CHANNEL` no ambiente para saber a qual
conversa entregar, e essa variável chega pelo gateway — um `docker exec` a
partir do host não carrega nenhum desses valores e o registro falha. Se o
script recusar por canal vazio, é isso.

Depois de `registrar`, **cole a saída inteira e diga o código de saída**. Ela
sinaliza cada recusa que teve — fuso ausente, `cron create` que falhou, rotina
registrada mas pausada — e um turno não propaga código de saída. Resumir
transforma "registrei, mas uma já existia e está inativa" numa frase honesta
que descreve uma execução que falhou, e ninguém fica sabendo.

## O que uma rotina nunca faz

Um turno disparado por cron **nunca roda setup**, nunca faz onboarding, nunca
força outra rotina como prova, e nunca envia nada a terceiros por conta
própria. Ele segue o prompt da rotina e devolve a mensagem. Um turno de cron
não tem ninguém do outro lado para responder uma pergunta — perguntar ali é
falar sozinho.

A `cobranca` devolve `NO_REPLY` quando não há nada atrasado: um dia sem
atraso não merece uma mensagem. As outras duas sempre têm conteúdo.
