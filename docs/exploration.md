# Exploration Mode

Exploration mode lets agents actually run the tool being evaluated, rather than just reading its help output. This provides more authentic feedback based on real interaction.

## Overview

By default, focusgroup shows agents the tool's `--help` output and asks them to provide feedback. With exploration mode enabled, agents can:

- Run the tool with various arguments
- Explore subcommands
- Test edge cases
- Discover issues through actual use

## Enabling Exploration

### Via CLI

```bash
focusgroup ask mx "Try searching for deployment docs" --explore
```

### Via Config

```toml
[session]
exploration = true  # Enable for all agents

# Or per-agent:
[[agents]]
provider = "claude"
mode = "cli"
exploration = true  # Just this agent can explore
```

## How It Works

1. **Context Enhancement**: Agents receive instructions on how to run the tool
2. **Tool Access**: CLI-mode agents can execute the tool command
3. **Interactive Feedback**: Agents explore, then report findings

### What Agents See

With exploration enabled, agents receive additional context:

```
## Interactive Exploration

**IMPORTANT**: You can and should run `mytool` commands to explore
this tool before giving feedback!

### How to Explore
1. Try the basic help: mytool --help
2. Explore subcommands: mytool <subcommand> --help
3. Try common operations
4. Explore subcommands that interest you
```

## Requirements

Exploration works best with CLI-mode agents:

| Provider | Mode | Exploration Support |
|----------|------|---------------------|
| Claude | CLI | ✅ Full support |
| Codex | CLI | ✅ Full support |
| Claude | API | ⚠️ Limited (no shell access) |
| OpenAI | API | ⚠️ Limited (no shell access) |

**Recommendation:** Use CLI-mode agents for exploration.

## Example: Exploring a Search Tool

```toml
[session]
name = "memex-exploration"
mode = "single"
exploration = true
moderator = true

[tool]
command = "mx"

[[agents]]
provider = "claude"
mode = "cli"
name = "Explorer-1"

[[agents]]
provider = "codex"
mode = "cli"
name = "Explorer-2"

[questions]
rounds = [
    "Explore this knowledge base tool. Try searching for various topics, then report what worked well and what was confusing.",
]
```

### Sample Session Output

```
## Explorer-1 (Claude-CLI)

I explored the `mx` tool by running several commands:

1. `mx --help` - Good overview, clear subcommand list
2. `mx search "deployment"` - Found relevant docs quickly
3. `mx search "nonexistent-topic"` - Helpful "no results" message
4. `mx get docs/deployment.md` - Retrieved full content

**What worked well:**
- Search is fast and results are relevant
- Error messages are clear

**What was confusing:**
- Unclear difference between `search` and `list`
- No obvious way to see all available tags

## Explorer-2 (Codex-CLI)

I tested the tool with various inputs:

1. Basic search worked well
2. Tried `mx add` but wasn't sure about required fields
3. `mx tree` gave a good overview of structure

**Suggestions:**
- Add examples to each subcommand's help
- Show available tags in search results
```

## Security Considerations

> **WARNING**: Exploration mode grants agents significant system access. Read this section carefully before enabling exploration.

### What Permissions Are Granted

CLI-mode agents run with **relaxed permission controls** to enable tool exploration:

| Provider | Mode | Permission Flags | What This Means |
|----------|------|------------------|-----------------|
| Claude | CLI | `--dangerously-skip-permissions` | Bypasses all permission prompts; agent can run any command without approval |
| Codex | CLI (explore) | `--sandbox danger-full-access` | Removes sandbox restrictions; full filesystem and network access |
| Codex | CLI (no explore) | `--full-auto` | Standard Codex safety checks apply |
| Claude/OpenAI | API | N/A | No shell access; limited to API-only interactions |

### What Agents Can Access

With exploration mode enabled, CLI agents can:

- **Filesystem**: Read, write, and delete any files accessible to your user account
- **Network**: Make HTTP requests, download files, connect to services
- **Shell Commands**: Run arbitrary shell commands (git, curl, rm, etc.)
- **Environment**: Access environment variables, including secrets in your shell
- **Other Tools**: Invoke any CLI tools installed on your system

### Why These Permissions?

Exploration mode exists to let agents **actually use** tools and give authentic feedback. An agent exploring a CLI tool needs to run that tool—which requires shell access. Sandbox restrictions would prevent agents from testing the very tool you want feedback on.

This is a deliberate trade-off: **useful exploration feedback requires real tool access**.

### Recommendations

#### 1. Run in Isolated Environments

The safest approach is to run focusgroup exploration in an isolated environment:

```bash
# Use a container
docker run -it --rm -v $(pwd):/workspace myimage focusgroup ask mytool "..." --explore

# Use a VM
# Run focusgroup inside a disposable VM or devcontainer

# Use a separate user account
# Create a low-privilege account specifically for exploration
```

#### 2. Review Tools Before Exploration

Before enabling exploration for a tool:

- Understand what the tool can do (especially write operations)
- Check if the tool accesses sensitive data or services
- Consider using read-only tools first to test the setup

#### 3. Limit What's in the Environment

```bash
# Run with a clean environment to limit exposed secrets
env -i PATH="$PATH" HOME="$HOME" focusgroup ask mytool "..." --explore

# Or explicitly set only needed variables
export MYTOOL_API_KEY=xxx  # Only what's needed
focusgroup ask mytool "..." --explore
```

#### 4. Use API Mode for Untrusted Scenarios

If you can't isolate the environment, use API-mode agents instead:

```toml
[[agents]]
provider = "claude"
mode = "api"  # No shell access, safer but can't explore
```

API agents can still review documentation and help text, but cannot run commands.

### Risk Summary

| Scenario | Risk Level | Recommendation |
|----------|------------|----------------|
| Exploring your own read-only tool in a dev container | Low | Safe to proceed |
| Exploring any tool in a VM/container | Low | Safe to proceed |
| Exploring read-only tools on your main system | Medium | Acceptable with caution |
| Exploring write-capable tools on your main system | High | Use isolated environment |
| Running exploration with sensitive secrets in env | High | Clean environment or container |

### Future: Sandbox Level Control

A `--sandbox-level` flag for granular control is planned but not yet implemented. For now, exploration mode is all-or-nothing with respect to permissions.

## Best Practices

### 1. Use Specific Questions

```toml
# Good: Specific exploration task
rounds = ["Search for 'deployment' and 'API' topics, then compare the results"]

# Less effective: Vague request
rounds = ["Explore this tool"]
```

### 2. Combine with Discussion Mode

```toml
[session]
mode = "discussion"
exploration = true

[questions]
rounds = [
    "Each of you explore different aspects of this tool.",
    "Share what you found. What patterns do you see?",
    "Based on everyone's exploration, what should be prioritized?",
]
```

### 3. Use Moderator for Synthesis

```toml
[session]
exploration = true
moderator = true  # Synthesize exploration findings
```

### 4. Mix API and CLI Agents

```toml
# CLI agents explore, API agents analyze
[[agents]]
provider = "claude"
mode = "cli"
name = "Explorer"
exploration = true

[[agents]]
provider = "claude"
mode = "api"
name = "Analyst"
system_prompt = "Analyze the explorer's findings and suggest improvements."
```

## Troubleshooting

### Agent Can't Run Commands

- Ensure you're using CLI mode (`mode = "cli"`)
- Verify the CLI tool is installed (`claude --version`, `codex --version`)
- Check that the tool being evaluated is in PATH

### Exploration Too Slow

- Reduce number of agents
- Use `parallel_agents = false` to run sequentially
- Limit the scope of exploration in your question

### Agent Runs Wrong Commands

- Provide more specific instructions in your question
- Use `working_dir` to set the right directory
- Ensure tool name is clear and unambiguous
