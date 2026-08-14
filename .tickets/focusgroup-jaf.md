---
id: focusgroup-jaf
status: closed
deps: []
links: []
created: 2026-01-05T18:25:26.30575869-05:00
type: bug
priority: 2
---
# Fix provider table formatting in --help

The ASCII table in main --help is garbled/misaligned:

```
Provider  │ Exploration  │ Synthesis  │ Prerequisites
──────────┼──────────────┼────────────┼────────────────────────   claude    │
```

Columns don't align properly in terminals.

Reference: Dogfood session 20260105-1829f3f3
