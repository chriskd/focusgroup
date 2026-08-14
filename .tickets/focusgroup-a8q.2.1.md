---
id: focusgroup-a8q.2.1
status: closed
deps: []
links: []
created: 2026-01-05T14:41:50.212421943-05:00
type: task
priority: 1
parent: focusgroup-a8q.2
---
# Create Agent protocol and base class

Define Agent Protocol in agents/base.py with: name, provider properties; respond(prompt, context) async method; stream_respond(prompt, context) async iterator. Create AgentResponse dataclass with content, model, tokens_used.
