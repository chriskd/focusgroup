---
id: focusgroup-n1g
status: closed
deps: []
links: []
created: 2026-01-05T18:09:37.203538434-05:00
type: feature
priority: 2
---
# Make tool argument optional, infer from context

## Problem
With --context now required, the positional `tool` argument is redundant:

```bash
# Current - tool name repeated
focusgroup ask mytool "question" --context "mytool --help"

# Desired - infer from context
focusgroup ask "question" --context "mytool --help"
```

## Proposed Solution
1. Make `tool` argument optional
2. Infer tool name from context when not provided:
   - Command context: `"mx --help"` → tool = `"mx"` (first word/token)
   - File context: `"@path/to/README.md"` → tool = `"README"` (filename without extension)
   - Fallback: `"unknown"` if can't parse
3. Allow explicit `--tool` override when inference isn't right

## New Syntax
```bash
# Infer tool from command (tool = "mx")
focusgroup ask "question" -x "mx --help"

# Infer tool from file (tool = "README")
focusgroup ask "question" -x @README.md

# Explicit override
focusgroup ask "question" -x "mx --help" --tool "memex"
```

## Acceptance Criteria
- [ ] Tool argument is optional
- [ ] Tool name inferred from command context (first token)
- [ ] Tool name inferred from file context (filename stem)
- [ ] --tool flag allows explicit override
- [ ] Session logs still have meaningful tool names
- [ ] Update help text and docs
