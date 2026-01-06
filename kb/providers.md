---
title: Agent Providers Guide
tags: [focusgroup, providers, agents]
created: 2026-01-06
---

# Agent Providers Guide

Focusgroup supports multiple LLM providers via their CLI tools. This guide covers setup and best practices for each.

## Overview

| Provider | CLI Tool | Best For |
|----------|----------|----------|
| Claude (Anthropic) | `claude` | General feedback, nuanced analysis |
| Codex (OpenAI) | `codex` | Code-focused feedback, OpenAI perspective |

All agents operate in CLI mode, invoking the actual CLI tools. This provides authentic agent behavior—the same way agents really use tools.

## Why CLI-Only?

Focusgroup deliberately uses only CLI-based agents rather than API calls or SDK integrations. This is a core design philosophy, not a limitation.

### The Problem with Approximations

When you call an LLM API directly or use an agent SDK, you're not talking to "the agent"—you're talking to a model through your own harness. You control the system prompt, tool configurations, safety parameters, and context window management. The result is an *approximation* of an agent, not the real thing.

Many agent implementations are closed-source. We don't know exactly how Claude Code, Codex, or other CLI agents are configured internally:

- What system prompts shape their behavior?
- What safety layers filter their responses?
- How do they manage context and tool use?
- What defaults and optimizations are baked in?

These details significantly affect how agents interact with tools—and they're invisible when you roll your own integration.

### Authentic Feedback from Real Customers

Focusgroup exists to get feedback on tools designed for AI agents. The agents *are* the customers. When evaluating a CLI tool that agents will use, you want feedback from:

- The actual agent as its provider ships it
- With its real configuration and behaviors
- Using the same interface it would use in production

You don't want feedback from a simulation you cobbled together using API calls—that feedback reflects your harness, not the agent's actual experience.

### CLI Tools as Ground Truth

CLI tools like `claude` and `codex` represent the most accurate form of each agent as its provider intends it to operate. By invoking these tools directly, focusgroup captures:

- Authentic agent reasoning and interaction patterns
- Real-world tool use behavior
- Provider-intended safety and capability boundaries

This means focusgroup feedback reflects what agents will *actually* do with your tool, not what a bespoke API integration might do.

## Claude (Anthropic)

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
name = "Claude"
```

**When to use Claude:**
- Testing how agents actually interact with tools
- Getting feedback that reflects real-world agent usage
- When you want the agent to use its full toolset (file reading, web access, etc.)

## Codex (OpenAI)

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
name = "Claude-1"
system_prompt = "Focus on UX and ergonomics."

[[agents]]
provider = "claude"
name = "Claude-2"
system_prompt = "Focus on correctness and edge cases."

[[agents]]
provider = "codex"
name = "Codex"
# Code-focused perspective
```

## System Prompts

Customize agent perspectives with system prompts:

```toml
[[agents]]
provider = "claude"
name = "DevOps-Engineer"
system_prompt = """You are an experienced DevOps engineer who values:
- Reliability and operational simplicity
- Clear error messages and debugging support
- Consistent behavior across environments

Focus on operational concerns when evaluating this tool."""

[[agents]]
provider = "claude"
name = "Junior-Developer"
system_prompt = """You are a junior developer who is:
- Still learning CLI conventions
- Easily confused by complex options
- Appreciative of good documentation and examples

Evaluate this tool from a beginner's perspective."""
```

See also: [[configuration]] for full config options, [[exploration]] for letting agents run tools.

## Troubleshooting

### Claude CLI Issues

```bash
# Verify Claude CLI is installed
claude --version

# Test authentication
claude "Hello, can you respond?"
```

### Codex CLI Issues

```bash
# Verify Codex CLI is installed
codex --version

# Test authentication
codex "Hello"
```
