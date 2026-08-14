---
id: focusgroup-a8q.2.3
status: closed
deps: []
links: []
created: 2026-01-05T14:41:50.672690814-05:00
type: task
priority: 1
parent: focusgroup-a8q.2
---
# Implement Claude CLI wrapper

Create ClaudeCLIAgent in agents/claude.py. Invoke 'claude -p <prompt>' via subprocess. Parse JSON output. This gives authentic Claude Code agent behavior including its system prompt and tools.
