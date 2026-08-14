---
id: focusgroup-a8q.2.6
status: closed
deps: []
links: []
created: 2026-01-05T14:41:51.365647928-05:00
type: task
priority: 1
parent: focusgroup-a8q.2
---
# Build agent registry and discovery

Create agents/registry.py. Register agents by provider name. Load agent presets from ~/.config/focusgroup/agents/*.toml. Provide get_agent(provider, mode, **config) factory function.
