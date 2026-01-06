---
title: JSON Output Formats
tags: [focusgroup, json, api, output]
created: 2026-01-06
---

# JSON Output Formats

Focusgroup uses two distinct JSON formats: the **internal session log** format for storage and the **export format** for reporting and piping.

## Session Log Format (Internal)

Used by: `~/.local/share/focusgroup/logs/*.json`

This is the raw Pydantic model serialization, used for session persistence and internal operations.

```json
{
  "id": "abc123",
  "name": "My Session",
  "tool": "mytool",
  "created_at": "2026-01-06T10:30:00",
  "completed_at": "2026-01-06T10:32:00",
  "mode": "single",
  "agent_count": 3,
  "rounds": [
    {
      "round_number": 1,
      "question": "Is the help output clear?",
      "responses": [
        {
          "agent_name": "Agent-1",
          "provider": "claude-cli",
          "model": null,
          "prompt": "...",
          "response": "The help output is clear...",
          "timestamp": "2026-01-06T10:31:00",
          "duration_ms": 1500,
          "tokens_used": 150
        }
      ],
      "moderator_synthesis": null
    }
  ],
  "final_synthesis": null,
  "tags": ["review"]
}
```

### Key Fields

- `id`: Short UUID (8 chars)
- `prompt`: The full prompt sent to the agent (included in responses)
- `provider`: The CLI backend used (`claude-cli`, `codex-cli`)
- Direct Pydantic serialization via `model_dump()`

## Export Format (Reports)

Used by: `focusgroup ask -o json`, `focusgroup logs export --json`

This is a curated format designed for human readability and tooling consumption.

```json
{
  "id": "20260106-abc123",
  "tool": "mytool",
  "mode": "single",
  "created_at": "2026-01-06T10:30:00.000000",
  "completed_at": "2026-01-06T10:32:00.000000",
  "is_complete": true,
  "name": "My Session",
  "agent_count": 3,
  "round_count": 1,
  "rounds": [
    {
      "round_number": 1,
      "question": "Is the help output clear?",
      "responses": [
        {
          "agent_name": "Agent-1",
          "provider": "claude-cli",
          "response": "The help output is clear...",
          "timestamp": "2026-01-06T10:31:00.000000",
          "model": "claude-sonnet-4",
          "duration_ms": 1500,
          "tokens_used": 150
        }
      ]
    }
  ],
  "summary": {
    "total_responses": 3,
    "unique_providers": ["claude-cli"],
    "total_tokens": 450,
    "total_duration_ms": 4500,
    "wall_time_seconds": 120.5
  }
}
```

### Key Differences from Session Log

| Aspect | Session Log | Export Format |
|--------|-------------|---------------|
| `id` | Short UUID | Display ID (`YYYYMMDD-uuid`) |
| `prompt` | Included in responses | Omitted (use question) |
| `round_count` | Not present | Computed field |
| `is_complete` | Not present | Computed boolean |
| `summary` | Not present | Aggregated statistics |

### Summary Statistics

The export format includes computed metrics:

- `total_responses`: Sum of all agent responses
- `unique_providers`: Deduplicated list of providers used
- `total_tokens`: Sum of tokens across all responses
- `total_duration_ms`: Sum of agent response times
- `wall_time_seconds`: Real elapsed time (if session complete)

## Choosing a Format

| Use Case | Recommended Format |
|----------|-------------------|
| Piping to `jq` | Export (`-o json`) |
| Archiving sessions | Session log (automatic) |
| CI/CD integration | Export with `--quiet` |
| Debugging prompts | Session log (includes `prompt`) |
| Metrics collection | Export (includes `summary`) |

## Future Compatibility

Both formats may evolve. For programmatic consumers, we recommend:

1. Parse fields you need, ignore unknown fields
2. Check for presence of optional fields before accessing
3. Use the export format for stable consumption

A `schema_version` field may be added in future releases for breaking changes.

## See Also

- [[configuration|Configuration Reference]] - Output format options
- [[modes|Session Modes]] - How different modes affect output
