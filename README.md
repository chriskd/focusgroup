# Focusgroup

Gather feedback from multiple LLM agents on tools designed for agent use.

When building CLI tools that AI agents will consume (like `memex`, `bd`, or custom CLIs), use focusgroup to consult multiple agents about features, design choices, and usability—directly from your terminal.

## Quick Start (2 minutes)

**Install:**
```bash
pip install focusgroup  # or: uv pip install -e ".[dev]" for dev setup
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

# Dogfood: review focusgroup itself
focusgroup demo
```

## Installation

Requires Python 3.11+ and [uv](https://github.com/astral-sh/uv):

```bash
# Clone the repository
git clone https://github.com/yourorg/focusgroup.git
cd focusgroup

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### API Keys

Set up API keys for the providers you want to use:

```bash
# For Claude (Anthropic)
export ANTHROPIC_API_KEY="your-key"

# For OpenAI
export OPENAI_API_KEY="your-key"
```

For CLI-mode agents (`claude`, `codex`), ensure those CLIs are installed and authenticated.

## Usage

### Quick Feedback (`ask`)

Get instant feedback without a config file:

```bash
# Basic usage
focusgroup ask <tool> "<question>"

# Options
focusgroup ask mx "How would you search for docs?" \
  --agents 5 \           # Number of agents (default: 3)
  --provider openai \    # Provider: claude, openai, codex
  --output markdown \    # Format: text, markdown, json
  --explore \            # Let agents run the tool
  --synthesize-with claude  # Have a moderator summarize
```

### Config-Driven Sessions (`run`)

For structured feedback with multiple rounds and custom agents:

```bash
focusgroup run session.toml
focusgroup run session.toml --dry-run  # Preview without executing
```

See [Configuration Reference](docs/configuration.md) for the full schema.

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

- [Configuration Reference](docs/configuration.md) - Full config file schema
- [Agent Providers Guide](docs/providers.md) - Claude, OpenAI, Codex setup
- [Session Modes](docs/modes.md) - When to use each mode
- [Exploration Mode](docs/exploration.md) - Letting agents run tools

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
