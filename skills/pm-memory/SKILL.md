---
name: pm-memory
description: O estado de um projeto de consultoria - escopo, objetivos (OKR), resultados-chave, planos de ação (5W2H) e demandas emergentes. Use sempre que o dono falar sobre um projeto - "novo projeto: X", "objetivo do projeto Y é...", "resultado chave:", "novo plano de ação", "surgiu uma demanda emergente", "qual o status do projeto?", "reprioriza X", "fulano entregou Y", "resultado Z não é mais prioridade, agora é W".
---

# Memória de Projeto (Second Brain)

Um arquivo por projeto, em JSON: `/var/lib/hermes/pm/<slug-do-projeto>.json`.
Você nunca edita esse arquivo à mão. Toda mudança passa por um único CLI, por
caminho absoluto:

    /var/lib/hermes/skills/pm-memory/scripts/pm_state.py <projeto> <comando> [args]

Comandos mutantes não imprimem nada em caso de sucesso, exceto
`add-key-result` e `add-action`, que imprimem o id criado. Erro = `refusing:
...` na saída de erro e código de saída não-zero.

| comando | o que faz |
|---|---|
| `show` | o estado completo em JSON — leia SEMPRE primeiro |
| `init --scope "..." --objective "..."` | cria o projeto com escopo e objetivo inicial |
| `add-key-result "<texto>"` | adiciona um resultado-chave (imprime o id) |
| `add-action <kr-id> --what "..." --who "..." --when "..." [--how "..." --where "..." --why "..." --how-much "..."]` | adiciona um plano de ação 5W2H sob um resultado-chave (imprime o id) |
| `update-status <action-id> <pendente\|em-andamento\|concluido\|atrasado>` | atualiza status de uma ação |
| `log-emergent "<texto>"` | registra uma demanda emergente ainda não cascateada |
| `prioritize <kr-id>` / `deprioritize <kr-id>` | move um resultado-chave para prioridade alta/baixa |

## Todo turno que toca um projeto

1. `show` do projeto mencionado (se não existir, ofereça `init`).
2. Interprete o que o dono pediu:
   - **Novo objetivo/projeto** → `init`, depois cascateie você mesmo em 1 a 3
     resultados-chave (`add-key-result`) e, para cada um, pelo menos um plano
     de ação 5W2H (`add-action`), a partir do que o dono descreveu. Não
     invente números ou prazos que o dono não deu — pergunte se faltar algo
     essencial.
   - **Demanda emergente** ("surgiu X", "apareceu uma nova demanda") →
     `log-emergent` primeiro. Pergunte se isso deve reorganizar prioridades
     existentes antes de tocar em qualquer resultado-chave já cascateado.
   - **Reprioridade confirmada** → `deprioritize` no que perde prioridade,
     `prioritize` no que ganha, e só então cascateie a nova demanda em
     resultado-chave + plano de ação como no caso de novo objetivo.
   - **Conclusão de tarefa** ("fulano entregou X") → `update-status` para
     `concluido`.
   - **Pergunta de status** → apenas `show` e responda com um resumo, sem
     alterar nada.
3. Responda de forma direta: o que mudou no cascateamento, em poucas linhas —
   nunca despeje o JSON inteiro na conversa.

## O que isso não é

Não é um substituto para reunião de alinhamento — se a demanda emergente for
ambígua, pergunte antes de cascatear. Não gera lembretes por e-mail nem
valida entregas contra template (fica para uma v2); esta skill só mantém o
estado do cascateamento coerente e rastreável.
