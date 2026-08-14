---
id: focusgroup-jri
status: closed
deps: []
links: []
created: 2026-01-05T19:32:03.174938565-05:00
type: bug
priority: 1
---
# AgentConfig missing 'mode' attribute in error handling

When an agent times out or errors, the error handling code in single.py and structured.py tries to access agent.config.mode which doesn't exist on AgentConfig. This causes an AttributeError that masks the original error.

Stack trace shows:
- /srv/fast/code/focusgroup/src/focusgroup/modes/single.py:135
- /srv/fast/code/focusgroup/src/focusgroup/modes/structured.py:279

Both try: mode=agent.config.mode

Fix: Either add 'mode' field to AgentConfig or remove it from error response construction.
