---
title: Session Modes
tags: [focusgroup, modes, sessions]
created: 2026-01-06
---

# Session Modes

Focusgroup offers three session modes that control how agents interact and provide feedback. Choose the mode that best fits your evaluation goals.

## Overview

| Mode | Agents See Each Other | Rounds | Best For |
|------|----------------------|--------|----------|
| `single` | No | 1 | Quick checks, specific questions |
| `discussion` | Yes | Multiple | Debates, exploring tradeoffs |
| `structured` | Yes (within phases) | 4 phases | Comprehensive evaluations |

## Single Mode

The simplest mode: all agents answer independently, without seeing each other's responses.

```toml
[session]
mode = "single"
```

### How It Works

1. Focusgroup captures the tool's help output
2. Each agent receives the help text + your question
3. All agents respond independently (optionally in parallel)
4. Responses are collected and displayed

### When to Use

- Quick sanity checks
- Gathering independent perspectives
- A/B testing different agent configurations
- Simple, focused questions

### Example

```toml
[session]
name = "quick-check"
mode = "single"
moderator = false

[tool]
command = "git"

[[agents]]
provider = "claude"

[[agents]]
provider = "codex"

[questions]
rounds = [
    "What's the most confusing aspect of this tool's help output?",
]
```

## Discussion Mode

Agents can see and respond to each other, enabling debate and collaborative exploration.

```toml
[session]
mode = "discussion"
```

### How It Works

1. Round 1: All agents respond to the initial question
2. Round 2+: Agents see previous responses and can build on, agree with, or challenge them
3. Moderator (optional): Synthesizes the discussion at the end

### When to Use

- Exploring tradeoffs between approaches
- When you want agents to challenge each other
- Building consensus on complex issues
- Getting nuanced, multi-perspective analysis

### Example

```toml
[session]
name = "design-discussion"
mode = "discussion"
moderator = true

[tool]
command = "mytool"

[[agents]]
provider = "claude"
name = "UX-Advocate"
system_prompt = "Prioritize user experience and ergonomics."

[[agents]]
provider = "claude"
name = "Minimalist"
system_prompt = "Advocate for simplicity and fewer options."

[[agents]]
provider = "codex"
name = "Power-User"
system_prompt = "Represent users who want advanced features."

[questions]
rounds = [
    "What's your initial take on this tool's design?",
    "Given the other perspectives, what tradeoffs should we prioritize?",
    "Can we reach consensus on the top 3 improvements?",
]
```

## Structured Mode

Guided feedback through four distinct phases, ensuring comprehensive and organized evaluation.

```toml
[session]
mode = "structured"
```

### The Four Phases

1. **Explore** - Initial impressions and understanding
   - What does this tool do?
   - How does it fit into workflows?
   - First impressions of the interface

2. **Critique** - Issues, concerns, and problems
   - What's confusing or unclear?
   - What could cause errors?
   - What's missing?

3. **Suggest** - Recommendations and improvements
   - Specific changes to make
   - New features to add
   - Documentation improvements

4. **Synthesize** - Final summary and conclusions
   - Key takeaways
   - Priority recommendations
   - Overall assessment

### How It Works

1. All agents go through each phase in sequence
2. Within each phase, agents see each other's responses (if running sequentially)
3. Phase context accumulates—later phases build on earlier insights
4. Moderator (recommended) provides final synthesis

### When to Use

- Comprehensive tool evaluations
- Generating structured feedback reports
- When you need organized, actionable feedback
- Formal design reviews

### Example

```toml
[session]
name = "full-review"
mode = "structured"
moderator = true

[tool]
command = "memex"

[[agents]]
provider = "claude"
name = "Claude-Sonnet"

[[agents]]
provider = "codex"
name = "Codex"

[questions]
rounds = [
    "Evaluate this knowledge base CLI tool for AI agent use.",
]

[output]
format = "markdown"
save_log = true
```

## Moderator

Any mode can include a moderator that synthesizes all feedback:

```toml
[session]
moderator = true

# Optional: customize the moderator
[session.moderator_agent]
provider = "claude"
```

The moderator:
- Identifies common themes across agents
- Highlights unique insights
- Notes disagreements and tensions
- Provides prioritized recommendations

## Choosing a Mode

```
┌─────────────────────────────────────────────────────────────┐
│                     What do you need?                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Quick answer to a specific question?                        │
│  └─→ single mode                                             │
│                                                              │
│  Explore tradeoffs or get debate?                            │
│  └─→ discussion mode                                         │
│                                                              │
│  Comprehensive, structured evaluation?                       │
│  └─→ structured mode                                         │
│                                                              │
│  Any mode + want a summary?                                  │
│  └─→ Enable moderator = true                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

See also: [[configuration]] for full config reference, [[exploration]] for letting agents run the tool.

## Parallel vs Sequential

Within any mode, you can control whether agents run in parallel:

```toml
[session]
parallel_agents = true   # Default: faster, independent responses
parallel_agents = false  # Sequential: each agent sees prior responses
```

- **Parallel** (default): Faster execution, independent perspectives
- **Sequential**: Agents build on each other, more conversational
