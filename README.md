# Focusgroup

Gather feedback from multiple LLM agents on tools designed for agent use.

## Installation

```bash
uv pip install -e ".[dev]"
```

## Usage

```bash
# Quick ad-hoc query
focusgroup ask memex "How would you search for deployment docs?"

# Config-driven session
focusgroup run session.toml

# List available agent presets
focusgroup agents list

# Review past sessions
focusgroup logs list
focusgroup logs show <session-id>
```

## Development

```bash
# Run linter and formatter
ruff check --fix . && ruff format .

# Run tests
pytest
```
