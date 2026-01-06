# Configuration Reference

Focusgroup uses TOML configuration files for full session control. This document describes all available options.

## Complete Example

```toml
[session]
name = "my-review"
mode = "structured"          # single | discussion | structured
moderator = true             # Enable synthesis at the end
parallel_agents = true       # Query agents concurrently
exploration = false          # Let agents run the tool

[session.moderator_agent]    # Optional: customize the moderator
provider = "claude"
mode = "api"
model = "claude-sonnet-4-20250514"

[tool]
type = "cli"                 # cli | docs
command = "mytool"           # Command name or path
help_args = ["--help"]       # Args to get help output
working_dir = "/path/to/dir" # Optional working directory

[[agents]]
provider = "claude"
mode = "api"
model = "claude-sonnet-4-20250514"
name = "Claude-Sonnet"
system_prompt = "You are a DevOps engineer..."
exploration = false          # Per-agent exploration override

[[agents]]
provider = "openai"
mode = "api"
model = "gpt-4o"
name = "GPT-4o"

[questions]
rounds = [
    "What's your first impression of this tool?",
    "What improvements would you suggest?",
]

[output]
format = "markdown"          # json | markdown | text
directory = "./output"       # Where to save files
save_log = true              # Persist session log
```

## Section Reference

### `[session]`

Controls overall session behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | auto-generated | Session identifier |
| `mode` | string | `"single"` | Session mode: `single`, `discussion`, or `structured` |
| `moderator` | bool | `false` | Enable a moderator agent to synthesize feedback |
| `parallel_agents` | bool | `true` | Query agents concurrently vs sequentially |
| `exploration` | bool | `false` | Allow agents to run tool commands |
| `agent_timeout` | integer | none | Timeout in seconds for all agents (overrides defaults) |

### `[session.moderator_agent]`

Optional custom configuration for the moderator. If omitted, uses Claude API with default synthesis prompt.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | `"claude"` | `claude`, `openai`, or `codex` |
| `mode` | string | `"api"` | `api` or `cli` |
| `model` | string | provider default | Specific model to use |

### `[tool]`

Specifies the tool being evaluated.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | `"cli"` | Tool type: `cli` or `docs` |
| `command` | string | **required** | CLI command name or path to docs |
| `help_args` | array | `["--help"]` | Arguments to get help output |
| `working_dir` | string | current dir | Working directory for tool execution |
| `path_additions` | array | `[]` | Additional directories to add to PATH for agents |

### `[[agents]]`

Define one or more agents. At least one agent is required.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | **required** | `claude`, `codex`, or custom provider name |
| `model` | string | provider default | Specific model to use |
| `name` | string | auto-generated | Display name for this agent |
| `system_prompt` | string | none | Custom system prompt for this agent |
| `exploration` | bool | `false` | Enable tool exploration for this agent |
| `timeout` | integer | none | Agent timeout in seconds (overrides session default) |

### `[questions]`

Define the questions/prompts for the session.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rounds` | array | **required** | List of questions (at least one) |

In `single` mode, only the first question is used. In `discussion` and `structured` modes, agents see all questions in sequence.

### `[output]`

Configure session output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | string | `"text"` | Output format: `json`, `markdown`, or `text` |
| `directory` | string | none | Directory to save output files |
| `save_log` | bool | `true` | Whether to save session log for later review |

## Minimal Config

The smallest valid config:

```toml
[tool]
command = "git"

[[agents]]
provider = "claude"

[questions]
rounds = ["What do you think of this tool?"]
```

## Built-in Providers

| Provider | Description | Notes |
|----------|-------------|-------|
| `claude` | Anthropic Claude via `claude` CLI | Requires `claude` CLI installed and authenticated |
| `codex` | OpenAI Codex via `codex` CLI | Requires `codex` CLI installed |

## Custom Providers

You can define custom providers in `~/.config/focusgroup/providers.toml`:

```toml
[myagent]
name = "My Custom Agent"
command = "my-agent-cli"
prompt_arg = "--prompt"          # How to pass the prompt
context_arg = "--context"        # How to pass context (optional)
model_arg = "--model"            # How to specify model (optional)
description = "My custom CLI agent"
```

Then use in configs:
```toml
[[agents]]
provider = "myagent"
name = "Custom Agent"
```

## Model Defaults

When `model` is not specified:

- **claude**: Uses claude CLI's default model
- **codex**: Uses codex CLI's default model
- Custom providers: Use their CLI defaults
