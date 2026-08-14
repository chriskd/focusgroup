---
id: focusgroup-x6r
status: closed
deps: []
links: []
created: 2026-01-06T15:29:08.579568636-05:00
type: bug
priority: 0
---
# Make JSON output machine-clean

When using -o json or --output json, focusgroup prints 'Session saved: ...' after the JSON, breaking parsers. Move status messages to stderr or add --quiet flag. Both agents identified this as automation-blocking.
