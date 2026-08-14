---
id: focusgroup-ui7
status: closed
deps: []
links: []
created: 2026-01-05T16:52:56.311125445-05:00
type: feature
priority: 2
---
# Add --json output to logs and agents commands

Both agents flagged that logs list/show and agents list/show produce human-readable tables but no JSON option for programmatic parsing.

Add --json flag to:
- focusgroup logs list
- focusgroup logs show
- focusgroup agents list
- focusgroup agents show

This is critical for agent consumption of focusgroup output.

Reference: Session 20260105-34d58421 and 20260105-3a88f82e
