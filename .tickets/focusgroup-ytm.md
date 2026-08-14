---
id: focusgroup-ytm
status: closed
deps: []
links: []
created: 2026-01-05T18:25:26.754388404-05:00
type: feature
priority: 3
---
# Support stdin for context in ask command

Allow piping context via stdin:

```bash
echo 'context' | focusgroup ask tool 'question' --context -
cat README.md | focusgroup ask tool 'review this' --context -
```

Reference: Dogfood session 20260105-1829f3f3
