---
id: focusgroup-vj5
status: closed
deps: []
links: []
created: 2026-01-06T15:29:33.440923331-05:00
type: bug
priority: 1
---
# Fix agents init usage hint

Agent B found: After 'focusgroup agents init my-reviewer', it prints wrong command. Suggests '--agents my-reviewer' but -n/--agents expects integer. Update hint to show correct usage (copy to config or future --agent-preset flag).
