---
id: focusgroup-x1o
status: closed
deps: []
links: []
created: 2026-01-05T16:39:22.154708926-05:00
type: feature
priority: 2
---
# Allow user to choose moderator/synthesizer agent

Currently the moderator (which synthesizes all agent feedback into a single report) is hardcoded to use Claude API. Users should be able to choose which agent performs synthesis.

## Current Limitation
- Moderator always uses Claude API (hardcoded in orchestrator.py:155-169)
- No CLI mode support for synthesis
- User cannot specify provider/model for moderator

## Proposed Changes

1. Add moderator_agent config section:
   ```toml
   [session]
   moderator = true

   [session.moderator_agent]
   provider = "codex"  # or "claude", "openai"
   mode = "cli"        # or "api"
   model = "o3"        # optional
   ```

2. CLI flag for quick usage:
   ```bash
   focusgroup ask mx "question" --synthesize-with codex
   focusgroup ask mx "question" --synthesize-with claude-cli
   ```

3. Support exploration mode for moderator (so it can re-run commands if needed)

## Implementation Notes
- Update SessionConfig to accept moderator agent config
- Modify _create_moderator() in orchestrator.py to use user config
- Add --synthesize-with flag to CLI
- Ensure CLI agents (Claude CLI, Codex CLI) work as moderators
