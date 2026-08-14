---
id: focusgroup-8j7
status: closed
deps: []
links: []
created: 2026-01-06T15:29:22.253636478-05:00
type: bug
priority: 1
---
# Fix --synthesize-with in single/ask mode

Agent B found: --synthesize-with does nothing in single mode because moderator requires conversation history. Either record single-round responses into history, or build moderator prompt directly from session.rounds.
