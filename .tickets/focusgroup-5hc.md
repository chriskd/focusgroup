---
id: focusgroup-5hc
status: closed
deps: []
links: []
created: 2026-01-05T16:52:56.010145524-05:00
type: task
priority: 2
---
# Document provider/mode matrix in help text

The --provider, --cli, and --synthesize-with flags are confusing without context. Help should explain:

1. What's the difference between API and CLI mode?
2. Which providers support which modes?
3. What prerequisites are needed (API keys, CLI tools)?

Suggested table for help or README:
| Provider | API Mode | CLI Mode | Prerequisites |
|----------|----------|----------|---------------|
| claude   | ✓        | ✓        | ANTHROPIC_API_KEY or claude CLI |
| openai   | ✓        | ✗        | OPENAI_API_KEY |
| codex    | ✗        | ✓        | codex CLI installed |

Reference: Session 20260105-34d58421 and 20260105-3a88f82e
