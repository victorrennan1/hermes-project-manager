# NOTICE

O código original deste repositório (`persona.md`, `skills/pm-memory/`,
`Dockerfile`, `compose.yml`, `README.md`) é licenciado sob MIT — veja
`LICENSE`.

Este agente builda `FROM` a imagem oficial
[`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent)
(Apache-2.0, Copyright The Plow Collective, Inc.), que não é redistribuída
aqui — apenas referenciada por tag/digest imutável no `Dockerfile`.

Dois arquivos são copiados diretamente do exemplo oficial
[`life-assistant-hermes-agent`](https://github.com/plow-pbc/life-assistant-hermes-agent)
(também Apache-2.0, Copyright The Plow Collective, Inc.), sem modificação, e
mantêm a licença original de origem:

- `vendor/client.pin`
- `image/s6-overlay/s6-rc.d/agent-index/` (o serviço do reporter de uso)

"Plow" e o logo Plow são marcas registradas de The Plow Collective, Inc. Esta
licença não concede direitos sobre essas marcas.
