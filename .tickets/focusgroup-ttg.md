---
id: focusgroup-ttg
status: closed
deps: []
links: []
created: 2026-01-06T14:12:36.070448-05:00
type: task
priority: 2
---
# Remove deprecated API integration references

Clean up all mentions of API integration/API mode across the codebase. This feature has been deprecated and removed, but references remain in:
- README
- Documentation (kb/)
- Any code comments or config examples

Search for: 'api', 'API mode', 'mode = "api"', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', etc. and remove or update accordingly.
