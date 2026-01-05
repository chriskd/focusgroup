# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Focusgroup is a tool for gathering feedback from multiple LLM agents (or LLM-powered agents) on tools being designed with agents as the primary users. The use case: when building CLI tools like `memex` that will primarily be consumed by AI agents, use focusgroup to consult multiple agents about features, design choices, and interactive tests to improve the tool for agent use.

## Project Status

This is a greenfield project. No code exists yet.

## Development Environment

- **Container-based development** via devcontainer on `devbox.voidlabs.local`
- **Python tooling**: Use `uv` for all package management (not pip/poetry)
- **Code at**: `/srv/fast/code/focusgroup`

## Commands (Once Project Is Set Up)

```bash
# Python environment
uv venv && uv pip install -e ".[dev]"

# Quality gates
ruff check --fix . && ruff format .
pytest

# Run the tool (once implemented)
uv run focusgroup <command>
```

## Issue Tracking

Use `bd` (beads) for issue tracking - see AGENTS.md for full workflow.

```bash
bd ready              # See unblocked work
bd create "title" --description="..." -t feature -p 2 --json
bd sync               # Always run at end of session
```

## Architecture Notes

*To be documented as architecture emerges.*

Key design consideration: The tool should be easy for agents to invoke and parse responses from, since agents are both the operators and the subjects of feedback collection.
