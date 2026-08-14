---
id: focusgroup-a6a
status: closed
deps: []
links: []
created: 2026-01-05T16:59:46.480521418-05:00
type: feature
priority: 2
---
# Remove API support - go CLI-only with claude and codex

Remove API mode support and focus exclusively on CLI agents (claude and codex).

## Rationale
- More authentic agent behavior - testing how agents actually use tools
- Simpler codebase - no need to manage API keys, rate limits, etc.
- Better exploration support - CLI agents have full tool access

## Changes needed
1. Remove OpenAI API agent implementation
2. Remove Claude API agent implementation
3. Update config schema - remove `mode: api` option
4. Update AgentProvider enum to just claude and codex
5. Update CLI options (remove --provider choices for api-only providers)
6. Update all documentation to reflect CLI-only model
7. Update example configs

## Also consider
- Shift focus from --help to open-ended exploration
- Make exploration the default/encouraged pattern
- CLI agents can run the tool, explore subcommands, try things out
