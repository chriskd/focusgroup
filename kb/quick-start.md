---
title: Quick Start
tags: [focusgroup, getting-started]
created: 2026-01-06
---

# Quick Start

Get feedback from AI agents on your CLI tools in under 2 minutes.

## Install

```bash
# Option 1: Run directly with uvx (no install needed)
uvx --from git+https://github.com/chriskd/focusgroup focusgroup --help

# Option 2: Install as a tool
uv tool install git+https://github.com/chriskd/focusgroup

# Option 3: Clone and install for development
git clone https://github.com/chriskd/focusgroup && cd focusgroup
uv pip install -e ".[dev]"
```

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv).

## Authenticate

Focusgroup uses CLI tools for agents. Set up the providers you want:

```bash
# For Claude
claude auth login

# For Codex (OpenAI)
codex auth
```

See [[providers]] for detailed setup.

## Run

```bash
focusgroup ask "Is this help clear?" -x "mytool --help" -n 1
```

**Output:**
```
Agent-1 (claude):
The help output is mostly clear, but I have a few suggestions:

1. The "--format" flag mentions "json, text" but doesn't explain the default
2. The synopsis shows [OPTIONS] but doesn't indicate which are required
3. Consider adding example commands at the bottom

Overall: 7/10 - functional but could be more discoverable for new users.

Session saved: ~/.local/share/focusgroup/logs/20260106-abc123.json
```

That's it! You've consulted an AI agent about your tool's usability.

## More Examples

```bash
# Ask 3 agents (default) for diverse perspectives
focusgroup ask "What improvements would help agents use this?" -x "mytool --help"

# Let agents actually run the tool (exploration mode)
focusgroup ask "Try common workflows" -x "mytool --help" --explore

# JSON output for piping
focusgroup ask "Review this" -x "mytool --help" -o json | jq .

# Context from a file
focusgroup ask "Review this API" -x "@README.md"

# Context from stdin
cat docs.md | focusgroup ask "What's missing?" -x -

# Dogfood: review focusgroup itself
focusgroup demo
```

## Next Steps

- [[configuration]] - Config file reference for structured sessions
- [[modes]] - Session modes (single, discussion, structured)
- [[exploration]] - Letting agents run your tool
- [[providers]] - Agent provider setup and troubleshooting
