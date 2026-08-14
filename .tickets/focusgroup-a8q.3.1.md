---
id: focusgroup-a8q.3.1
status: closed
deps: []
links: []
created: 2026-01-05T14:42:03.094744703-05:00
type: task
priority: 1
parent: focusgroup-a8q.3
---
# Create Tool protocol and base class

Define Tool Protocol in tools/base.py with: name property; get_help() -> str async; run(args) -> ToolOutput async; describe_interface() -> str async. Create ToolOutput dataclass with stdout, stderr, exit_code, duration.
