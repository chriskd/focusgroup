---
title: CLI Tool PATH Lookup Behavior
tags: [focusgroup, configuration, troubleshooting]
created: 2026-01-06
---

# CLI Tool PATH Lookup Behavior

Focusgroup invokes external CLI tools (`claude`, `codex`) via subprocess and relies on standard PATH resolution to locate them.

## How It Works

When focusgroup needs to run an agent CLI:

1. **PATH lookup**: Uses Python's `shutil.which()` to verify the command exists
2. **Subprocess execution**: Runs the command directly via `asyncio.create_subprocess_exec()`
3. **Error on failure**: Raises a clear error if the command is not found

## Error Messages

If a CLI tool is not in PATH, you'll see errors like:

```
Claude CLI not found. Is it installed and in PATH?
```

```
Codex CLI not found. Is it installed and in PATH?
```

## Solutions

### Option 1: Ensure CLIs are in PATH

Add the directory containing your CLI tools to your PATH environment variable:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Verify it works
which claude
which codex
```

### Option 2: Use absolute paths in configuration

If your CLIs are installed in non-standard locations, you can specify absolute paths in your focusgroup configuration file:

```toml
[agents.claude]
command = "/opt/anthropic/bin/claude"

[agents.codex]
command = "/usr/local/bin/codex"
```

## Technical Details

The PATH lookup is implemented in two places:

- **CLITool class** (`src/focusgroup/tools/cli.py`): General CLI wrapper using `shutil.which()`
- **Agent implementations** (`src/focusgroup/agents/claude.py`, `codex.py`): Direct subprocess calls

Both raise descriptive errors when commands are not found, helping users diagnose PATH issues quickly.
