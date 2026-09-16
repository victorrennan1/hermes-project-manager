# NOTICE

Original code in this repository (`persona.md`, `skills/`, `Dockerfile`,
`compose.yml`, `README.md`) is licensed under MIT -- see `LICENSE`.

This agent builds `FROM` the official
[`plow-hermes-agent`](https://github.com/plow-pbc/plow-hermes-agent) image
(Apache-2.0, Copyright The Plow Collective, Inc.), not redistributed here --
only referenced by immutable tag/digest in the `Dockerfile`.

Two files are copied unmodified from the official example
[`life-assistant-hermes-agent`](https://github.com/plow-pbc/life-assistant-hermes-agent)
(also Apache-2.0, Copyright The Plow Collective, Inc.), and keep that license:

- `vendor/client.pin`
- `image/s6-overlay/s6-rc.d/agent-index/` (the usage-reporter service)

"Plow" and the Plow logo are trademarks of The Plow Collective, Inc. This
license grants no rights to those marks.
