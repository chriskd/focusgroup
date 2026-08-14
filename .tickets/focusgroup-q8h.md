---
id: focusgroup-q8h
status: closed
deps: []
links: []
created: 2026-01-05T19:32:03.703983185-05:00
type: bug
priority: 2
---
# Default 120s timeout too short for exploration mode

When using --explore mode, agents need time to actually run commands and explore the tool. The default 120s timeout in CodexCLIAgent and ClaudeCLIAgent is frequently exceeded.

Suggestions:
- Increase default timeout for exploration mode (e.g., 300s or 600s)
- Add --timeout flag to focusgroup ask/run commands
- Make timeout configurable in session config
