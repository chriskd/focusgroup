---
id: focusgroup-1i0
status: closed
deps: []
links: []
created: 2026-01-06T16:09:12.718403758-05:00
type: task
priority: 4
---
# Regenerate GitHub Pages with mx publish after mx bug fixes

The kb/ documentation needs to be republished to docs/ for GitHub Pages once mx (memex) fixes its page generation bugs.

## Context
- Documentation lives in kb/ as a memex knowledge base
- Published to docs/ via `mx publish -o docs`
- Current mx has bugs affecting page generation

## Action Required
Once mx page generation is fixed:
1. Run `mx publish -o docs` to regenerate the static site
2. Verify the generated pages look correct
3. Commit both kb/ and docs/ changes
4. Push to update GitHub Pages

## Blocked By
- mx page generation bug fixes (external dependency)
