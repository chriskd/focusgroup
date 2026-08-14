---
id: focusgroup-82l
status: closed
deps: []
links: []
created: 2026-01-06T12:38:30.782292488-05:00
type: bug
priority: 1
---
# Fix AgentConfig.mode AttributeError in discussion mode error handling

When an agent fails (e.g., rate limit), discussion.py tries to create AgentResponse with mode=agent.config.mode, but neither AgentResponse nor AgentConfig has a mode field. Fix already applied in discussion.py:280-301 - removed invalid mode= parameter.
