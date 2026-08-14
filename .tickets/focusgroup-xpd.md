---
id: focusgroup-xpd
status: closed
deps: []
links: []
created: 2026-01-06T12:38:31.221493718-05:00
type: bug
priority: 1
---
# Handle API quota/rate limit errors gracefully

When providers hit rate limits (e.g., Codex 429 'usage_limit_reached'), the error crashes the session instead of gracefully handling it. Should: 1) Catch rate limit errors specifically, 2) Show user-friendly message with reset time, 3) Allow session to continue with remaining agents, 4) Consider retry logic with backoff.
