---
id: focusgroup-hkn
status: closed
deps: []
links: []
created: 2026-01-05T16:52:56.609479084-05:00
type: feature
priority: 2
---
# Document config schema and add focusgroup init command

focusgroup run requires TOML config but help doesn't explain the schema. Options:

1. Add focusgroup init - generate a starter config template
2. Add focusgroup run --example - show example config
3. Add focusgroup config schema - print the schema
4. Better document session modes (single/discussion/structured)

The existing configs/examples/ directory is not discoverable from CLI.

Reference: Session 20260105-34d58421 and 20260105-3a88f82e
