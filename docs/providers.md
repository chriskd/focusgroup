# Agent Providers Guide

Focusgroup supports multiple LLM providers, each with API and/or CLI modes. This guide covers setup and best practices for each.

## Overview

| Provider | API Mode | CLI Mode | Best For |
|----------|----------|----------|----------|
| Claude (Anthropic) | ✅ | ✅ | General feedback, nuanced analysis |
| OpenAI | ✅ | ❌ | Alternative perspective, GPT-4o capabilities |
| Codex (OpenAI) | ❌ | ✅ | Code-focused feedback, authentic CLI behavior |

## Claude (Anthropic)

### API Mode

Direct API calls to Anthropic's Claude models.

**Setup:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Config:**
```toml
[[agents]]
provider = "claude"
mode = "api"
model = "claude-sonnet-4-20250514"  # or claude-opus-4-20250514
name = "Claude-Sonnet"
```

**Available Models:**
- `claude-sonnet-4-20250514` (default) - Fast, capable, cost-effective
- `claude-opus-4-20250514` - Most capable, higher cost

### CLI Mode

Invokes the actual `claude` CLI tool, providing authentic agent behavior.

**Setup:**
```bash
# Install Claude Code CLI
# See: https://docs.anthropic.com/claude-code

# Authenticate
claude auth login
```

**Config:**
```toml
[[agents]]
provider = "claude"
mode = "cli"
name = "Claude-CLI"
```

**When to use CLI mode:**
- Testing how agents actually interact with tools
- Getting feedback that reflects real-world agent usage
- When you want the agent to use its full toolset (file reading, web access, etc.)

## OpenAI

### API Mode

Direct API calls to OpenAI's GPT models.

**Setup:**
```bash
export OPENAI_API_KEY="sk-..."
```

**Config:**
```toml
[[agents]]
provider = "openai"
mode = "api"
model = "gpt-4o"
name = "GPT-4o"
```

**Available Models:**
- `gpt-4o` (default) - Latest multimodal model
- `gpt-4o-mini` - Faster, lower cost
- `gpt-4-turbo` - Previous generation

**Notes:**
- OpenAI does not have CLI mode in focusgroup
- System prompts are fully supported

## Codex

### CLI Mode

Invokes the OpenAI Codex CLI for code-focused feedback.

**Setup:**
```bash
# Install Codex CLI
# See OpenAI's codex documentation

# Authenticate
codex auth
```

**Config:**
```toml
[[agents]]
provider = "codex"
mode = "cli"
name = "Codex"
```

**When to use Codex:**
- Getting code-focused feedback
- Testing CLI tools that agents interact with programmatically
- When you want an OpenAI-based CLI agent perspective

## Mixing Providers

A key strength of focusgroup is combining multiple providers for diverse perspectives:

```toml
[[agents]]
provider = "claude"
mode = "api"
name = "Claude-API"
system_prompt = "Focus on UX and ergonomics."

[[agents]]
provider = "openai"
mode = "api"
model = "gpt-4o"
name = "GPT-4o"
system_prompt = "Focus on correctness and edge cases."

[[agents]]
provider = "claude"
mode = "cli"
name = "Claude-CLI"
# No system prompt - uses authentic CLI behavior

[[agents]]
provider = "codex"
mode = "cli"
name = "Codex"
# Code-focused perspective
```

## API vs CLI Mode

| Aspect | API Mode | CLI Mode |
|--------|----------|----------|
| Speed | Faster (direct calls) | Slower (subprocess) |
| Control | Full control (system prompts, params) | Limited (CLI defaults) |
| Authenticity | Controlled environment | Real agent behavior |
| Cost | Pay per token | Depends on CLI pricing |
| Exploration | Limited | Full tool access |

**Recommendation:** Use API mode for controlled experiments and CLI mode when you want to test authentic agent interactions.

## System Prompts

Customize agent perspectives with system prompts:

```toml
[[agents]]
provider = "claude"
mode = "api"
name = "DevOps-Engineer"
system_prompt = """You are an experienced DevOps engineer who values:
- Reliability and operational simplicity
- Clear error messages and debugging support
- Consistent behavior across environments

Focus on operational concerns when evaluating this tool."""

[[agents]]
provider = "claude"
mode = "api"
name = "Junior-Developer"
system_prompt = """You are a junior developer who is:
- Still learning CLI conventions
- Easily confused by complex options
- Appreciative of good documentation and examples

Evaluate this tool from a beginner's perspective."""
```

## Troubleshooting

### Claude API Issues

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Test directly
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### OpenAI API Issues

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test directly
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"Hi"}]}'
```

### CLI Agent Issues

```bash
# Verify Claude CLI
claude --version
claude "Hello"

# Verify Codex CLI
codex --version
codex "Hello"
```
