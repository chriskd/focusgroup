# Focusgroup

Gather feedback from multiple LLM agents on tools designed for agent use.

When building CLI tools that AI agents will consume (like `memex`, `bd`, or custom CLIs), use focusgroup to consult multiple agents about features, design choices, and usability—directly from your terminal.

## Quick Start (2 minutes)

**Install:**
```bash
# Option 1: Run directly with uvx (no install needed)
uvx --from git+https://github.com/chriskd/focusgroup focusgroup --help

# Option 2: Install as a tool
uv tool install git+https://github.com/chriskd/focusgroup

# Option 3: Clone and install for development
git clone https://github.com/chriskd/focusgroup && cd focusgroup
uv pip install -e ".[dev]"
```

**Run:**
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

That's it! You've just consulted an AI agent about your tool's usability.

### More Examples

```bash
# Ask 3 agents (default) for diverse perspectives
focusgroup ask "What improvements would help agents use this?" -x "mytool --help"

# Let agents actually run the tool (exploration mode)
focusgroup ask "Try common workflows" -x "mytool --help" --explore

# JSON output for piping (status messages suppressed)
focusgroup ask "Review this" -x "mytool --help" -o json | jq .

# Quiet mode for automation (suppress all status messages)
focusgroup --quiet ask "Review" -x "mytool --help" -o json > output.json

# Dogfood: review focusgroup itself
focusgroup demo
```

## Installation

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv):

```bash
# Quick: run without installing
uvx --from git+https://github.com/chriskd/focusgroup focusgroup --help

# Install as a persistent tool
uv tool install git+https://github.com/chriskd/focusgroup

# Or clone for development
git clone https://github.com/chriskd/focusgroup.git
cd focusgroup
uv pip install -e ".[dev]"
```

### CLI Authentication

Focusgroup uses CLI tools for all agents. Set up authentication for the providers you want to use:

```bash
# For Claude
claude auth login

# For Codex (OpenAI)
codex auth
```

See the [Agent Providers Guide](https://chriskd.github.io/focusgroup/providers) for detailed setup instructions.

## Usage

### Quick Feedback (`ask`)

Get instant feedback without a config file:

```bash
# Basic usage - context is required via -x
focusgroup ask "<question>" -x "<context>"

# Context can be a command, file (@path), or stdin (-)
focusgroup ask "Is this help clear?" -x "mx --help"
focusgroup ask "Review this API" -x "@README.md"
cat docs.md | focusgroup ask "What's missing?" -x -

# Options
focusgroup ask "How would you search for docs?" -x "mx --help" \
  --agents 5 \              # Number of agents (default: 3)
  --provider codex \        # Provider: claude (default) or codex
  --output markdown \       # Format: text, markdown, json
  --explore \               # Let agents run the tool
  --synthesize-with claude  # Have a moderator summarize
```

### Config-Driven Sessions (`run`)

For structured feedback with multiple rounds and custom agents:

```bash
focusgroup run session.toml
focusgroup run session.toml --dry-run  # Preview without executing
```

See the [Configuration Reference](https://chriskd.github.io/focusgroup/configuration) for the full schema.

### Session Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `single` | One round, all agents respond once | Quick checks, simple questions |
| `discussion` | Agents see and respond to each other | Debates, exploring tradeoffs |
| `structured` | Four phases: explore→critique→suggest→synthesize | Comprehensive evaluations |

### Managing Agents & Logs

```bash
# List built-in agent presets
focusgroup agents list
focusgroup agents show claude-sonnet

# Review past sessions
focusgroup logs list
focusgroup logs show <session-id>
focusgroup logs export <session-id> -o report.md
```

## Example Configs

The `configs/examples/` directory contains ready-to-use templates:

- **`quick-check.toml`** - Minimal config for fast single-round feedback
- **`discussion-mode.toml`** - Agents debate and build on each other's ideas
- **`cli-mode-agents.toml`** - Uses actual `claude` and `codex` CLIs
- **`memex-review.toml`** - Full structured review with multiple providers

## Documentation

Full documentation is available at **[chriskd.github.io/focusgroup](https://chriskd.github.io/focusgroup/)**:

- [Configuration Reference](https://chriskd.github.io/focusgroup/configuration) - Full config file schema
- [Agent Providers Guide](https://chriskd.github.io/focusgroup/providers) - Claude and Codex setup
- [Session Modes](https://chriskd.github.io/focusgroup/modes) - When to use each mode
- [Exploration Mode](https://chriskd.github.io/focusgroup/exploration) - Letting agents run tools
- [CLI PATH Lookup](https://chriskd.github.io/focusgroup/cli-path-lookup) - How focusgroup finds CLI tools

## Development

```bash
# Run linter and formatter
ruff check --fix . && ruff format .

# Run tests
pytest

# Run with coverage
pytest --cov=focusgroup
```

## How It Works

1. **Tool Context**: Focusgroup runs your tool's `--help` and captures the output
2. **Agent Panel**: Multiple agents receive the help text and your question
3. **Session Mode**: Depending on mode, agents respond once, discuss, or go through phases
4. **Synthesis**: Optionally, a moderator agent summarizes all feedback
5. **Output**: Results are formatted and optionally saved to session logs
