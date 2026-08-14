---
id: focusgroup-bix
status: closed
deps: []
links: []
created: 2026-01-05T18:02:59.143668828-05:00
type: feature
priority: 2
---
# Make CLI agent integration pluggable for custom providers

## Problem
Currently, adding a new CLI agent (like Gemini CLI) requires:
1. Creating a new Python file in `src/focusgroup/agents/`
2. Implementing a full agent class with respond/stream methods
3. Adding to registry with factory function
4. Adding to AgentProvider enum in config.py

This is too much friction for users who just want to add support for another CLI tool.

## Proposed Solution
Single providers config file at `~/.config/focusgroup/providers.toml`:

```toml
[gemini]
command = "gemini"
prompt_flag = "-p"
model_flag = "--model"
timeout = 120

[ollama]
command = "ollama run"
prompt_flag = ""              # prompt is positional
model_flag = ""               # model is part of command
default_model = "llama3"

[local-claude]
command = "claude"
prompt_flag = "-p"
extra_flags = ["--dangerously-skip-permissions"]
```

Then users can use any defined provider:
```bash
focusgroup ask mytool "question" --context "mytool --help" --provider gemini
focusgroup ask mytool "question" -x @README.md --provider ollama
```

## Implementation Notes
- Keep ClaudeCLIAgent and CodexCLIAgent as built-in defaults
- Add GenericCLIAgent that handles arbitrary CLI patterns
- Load ~/.config/focusgroup/providers.toml on startup
- Registry checks user providers before falling back to built-ins
- User can override built-ins by defining [claude] or [codex] sections

## Acceptance Criteria
- [ ] Single providers.toml file for all custom CLI providers
- [ ] Users can define custom CLI providers with command + flags
- [ ] Custom providers work with all focusgroup commands
- [ ] Built-in claude/codex continue to work unchanged
- [ ] User-defined providers can override built-ins
- [ ] Documentation explains the providers.toml format
