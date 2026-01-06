---
title: Structured Feedback Schemas
tags: [focusgroup, feedback, json, schema]
created: 2026-01-06
---

# Structured Feedback Schemas

Request agents respond with structured JSON matching a predefined schema, enabling automated analysis and aggregation of feedback.

## Quick Start

```bash
# Use a built-in schema preset
focusgroup ask "Rate this tool" -x "mytool --help" --schema rating

# Output includes structured_data in JSON
focusgroup ask "Pros and cons?" -x "mytool --help" --schema pros-cons -o json
```

## Built-in Schema Presets

### `rating`
Simple numeric rating with explanation.
```json
{
  "rating": 4,
  "reasoning": "Clear help output, intuitive flags"
}
```

### `pros-cons`
List positive and negative aspects.
```json
{
  "pros": ["Fast execution", "Good error messages"],
  "cons": ["Missing documentation"],
  "summary": "Solid tool with room for improvement"
}
```

### `review`
Comprehensive review with rating, pros, cons, and suggestions.
```json
{
  "rating": 4,
  "pros": ["Intuitive CLI", "Good defaults"],
  "cons": ["Verbose output"],
  "suggestions": ["Add --quiet flag", "Support JSON output"]
}
```

## How It Works

1. **Prompt Injection**: Schema instructions are appended to your question
2. **Agent Response**: Agents are instructed to respond with valid JSON
3. **Response Parsing**: Focusgroup extracts JSON from the response
4. **Output**: Both raw response and structured data are available

## JSON Output Format

When using `--schema` with `-o json`, responses include `structured_data`:

```json
{
  "rounds": [{
    "question": "Rate this tool",
    "responses": [{
      "agent_name": "Agent-1",
      "provider": "claude-cli",
      "response": "{\"rating\": 4, \"reasoning\": \"Good tool\"}",
      "structured_data": {
        "rating": 4,
        "reasoning": "Good tool"
      }
    }]
  }]
}
```

## Custom Schemas (TOML Config)

Define custom schemas in your config file:

```toml
[session]
name = "Custom Review"

[session.feedback_schema]
include_raw_response = true

[[session.feedback_schema.fields]]
name = "usability"
type = "integer"
min_value = 1
max_value = 10
description = "How easy is the tool to use?"

[[session.feedback_schema.fields]]
name = "would_recommend"
type = "boolean"
description = "Would you recommend this tool to other agents?"

[[session.feedback_schema.fields]]
name = "improvements"
type = "list"
description = "Suggested improvements"
required = false
```

### Field Types

| Type | JSON Type | Description |
|------|-----------|-------------|
| `integer` | number | Numeric values (supports `min_value`, `max_value`) |
| `string` | string | Free text |
| `list` | array | Array of strings |
| `boolean` | boolean | True/false |

## Response Parsing

Focusgroup handles various response formats:

1. **Pure JSON**: Response is just the JSON object
2. **Code blocks**: JSON in markdown ` ```json ... ``` ` blocks
3. **Embedded**: JSON object anywhere in the response text

If JSON parsing fails, `structured_data` will be `null` and the raw response is preserved.

## Use Cases

### Automated Analysis

```bash
# Collect structured reviews from multiple agents
focusgroup ask "Review this CLI" -x "mytool --help" --schema review -o json -n 5 | \
  jq '[.rounds[0].responses[].structured_data.rating] | add / length'
# Average rating across 5 agents
```

### Trend Tracking

Compare structured feedback across sessions:
```bash
focusgroup logs export --json | jq '.rounds[].responses[].structured_data'
```

### CI/CD Integration

```bash
# Fail if average rating is below threshold
rating=$(focusgroup ask "Rate this tool" -x "mytool --help" --schema rating -o json -q | \
  jq '[.rounds[0].responses[].structured_data.rating // 0] | add / length')

if (( $(echo "$rating < 3" | bc -l) )); then
  echo "Tool rating too low: $rating"
  exit 1
fi
```

## Best Practices

1. **Keep schemas simple**: Fewer fields = more reliable parsing
2. **Use descriptive field descriptions**: Helps agents understand expectations
3. **Make non-essential fields optional**: Set `required = false`
4. **Use `--quiet` with scripts**: Prevents status messages in output
5. **Combine with `-o json`**: Structured data is most useful in JSON output

## See Also

- [[json-formats|JSON Output Formats]] - Export format details
- [[configuration|Configuration Reference]] - Full config options
