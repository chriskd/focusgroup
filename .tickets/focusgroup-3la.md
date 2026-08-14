---
id: focusgroup-3la
status: closed
deps: []
links: []
created: 2026-01-05T19:32:04.325323593-05:00
type: bug
priority: 2
---
# CLI agents run in isolated environment without target tool access

When using focusgroup to evaluate a CLI tool (e.g., mx), the claude/codex agents run in their own subprocess environment where the target tool may not be in PATH.

Example: Evaluating memex with mx at /srv/fast/code/memex/.venv/bin/mx - the codex agent reported 'mx: command not found'.

Suggestions:
- Allow specifying PATH additions in config
- Automatically add the tool's directory to agent PATH
- Document this limitation clearly
- Consider running agents with the same environment as focusgroup
