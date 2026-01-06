"""Configuration models and loading for focusgroup sessions."""

import importlib.resources
import tomllib
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SessionMode(str, Enum):
    """How the session should be structured."""

    SINGLE = "single"  # One question, all agents respond once
    DISCUSSION = "discussion"  # Agents can see and respond to each other
    STRUCTURED = "structured"  # Phases: explore, critique, suggest, synthesize


class AgentProvider(str, Enum):
    """Built-in agent providers (CLI-only)."""

    CLAUDE = "claude"
    CODEX = "codex"


def _get_provider_value(provider: "AgentProvider | str") -> str:
    """Get the string value of a provider (enum or custom string)."""
    if isinstance(provider, AgentProvider):
        return provider.value
    return provider


class SchemaFieldType(str, Enum):
    """Types for structured feedback schema fields."""

    INTEGER = "integer"  # Numeric rating (1-5, 1-10, etc.)
    STRING = "string"  # Free text
    LIST = "list"  # List of strings (pros, cons, suggestions)
    BOOLEAN = "boolean"  # Yes/no


class SchemaField(BaseModel):
    """A single field in a structured feedback schema."""

    name: str
    type: SchemaFieldType = SchemaFieldType.STRING
    description: str | None = None  # Help text for the agent
    required: bool = True
    min_value: int | None = None  # For integer fields (e.g., rating 1-5)
    max_value: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure field name is a valid identifier."""
        if not v.isidentifier():
            raise ValueError(f"Field name must be a valid identifier: {v}")
        return v


class FeedbackSchema(BaseModel):
    """Schema for structured agent feedback responses.

    When enabled, agents are instructed to respond with JSON
    matching this schema, enabling automated analysis and aggregation.

    Example:
        schema = FeedbackSchema(fields=[
            SchemaField(name="rating", type=SchemaFieldType.INTEGER, min_value=1, max_value=5),
            SchemaField(name="pros", type=SchemaFieldType.LIST),
            SchemaField(name="cons", type=SchemaFieldType.LIST),
            SchemaField(name="summary", type=SchemaFieldType.STRING),
        ])
    """

    fields: list[SchemaField] = Field(min_length=1)
    include_raw_response: bool = True  # Also include unstructured response

    def to_json_schema(self) -> dict:
        """Convert to JSON Schema format for agent instructions."""
        properties = {}
        required = []

        for field in self.fields:
            prop: dict = {"description": field.description or f"The {field.name} field"}

            if field.type == SchemaFieldType.INTEGER:
                prop["type"] = "integer"
                if field.min_value is not None:
                    prop["minimum"] = field.min_value
                if field.max_value is not None:
                    prop["maximum"] = field.max_value
            elif field.type == SchemaFieldType.STRING:
                prop["type"] = "string"
            elif field.type == SchemaFieldType.LIST:
                prop["type"] = "array"
                prop["items"] = {"type": "string"}
            elif field.type == SchemaFieldType.BOOLEAN:
                prop["type"] = "boolean"

            properties[field.name] = prop
            if field.required:
                required.append(field.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_prompt_instructions(self) -> str:
        """Generate instructions for agents to follow this schema."""
        import json

        schema = self.to_json_schema()
        lines = [
            "IMPORTANT: Respond with valid JSON matching this schema:",
            "```json",
            json.dumps(schema, indent=2),
            "```",
            "",
            "Field descriptions:",
        ]

        for field in self.fields:
            desc = field.description or f"The {field.name} field"
            type_hint = field.type.value
            if field.type == SchemaFieldType.INTEGER and field.min_value is not None:
                type_hint = f"integer ({field.min_value}-{field.max_value})"
            elif field.type == SchemaFieldType.LIST:
                type_hint = "array of strings"
            lines.append(f"- {field.name} ({type_hint}): {desc}")

        lines.append("")
        lines.append("Respond ONLY with the JSON object, no other text.")

        return "\n".join(lines)


# Built-in schema presets for common use cases
BUILTIN_SCHEMAS: dict[str, FeedbackSchema] = {
    "rating": FeedbackSchema(
        fields=[
            SchemaField(
                name="rating",
                type=SchemaFieldType.INTEGER,
                description="Overall rating",
                min_value=1,
                max_value=5,
            ),
            SchemaField(
                name="reasoning",
                type=SchemaFieldType.STRING,
                description="Explanation for the rating",
            ),
        ]
    ),
    "pros-cons": FeedbackSchema(
        fields=[
            SchemaField(
                name="pros",
                type=SchemaFieldType.LIST,
                description="List of positive aspects",
            ),
            SchemaField(
                name="cons",
                type=SchemaFieldType.LIST,
                description="List of negative aspects or issues",
            ),
            SchemaField(
                name="summary",
                type=SchemaFieldType.STRING,
                description="Brief overall summary",
            ),
        ]
    ),
    "review": FeedbackSchema(
        fields=[
            SchemaField(
                name="rating",
                type=SchemaFieldType.INTEGER,
                description="Overall quality rating",
                min_value=1,
                max_value=5,
            ),
            SchemaField(
                name="pros",
                type=SchemaFieldType.LIST,
                description="Positive aspects",
            ),
            SchemaField(
                name="cons",
                type=SchemaFieldType.LIST,
                description="Areas for improvement",
            ),
            SchemaField(
                name="suggestions",
                type=SchemaFieldType.LIST,
                description="Specific suggestions for improvement",
                required=False,
            ),
        ]
    ),
}


def get_schema_preset(name: str) -> FeedbackSchema | None:
    """Get a built-in schema preset by name."""
    return BUILTIN_SCHEMAS.get(name)


def list_schema_presets() -> list[str]:
    """List available built-in schema preset names."""
    return list(BUILTIN_SCHEMAS.keys())


class AgentConfig(BaseModel):
    """Configuration for a single agent in the panel."""

    provider: AgentProvider | str  # Built-in enum or custom provider name
    model: str | None = None
    name: str | None = None  # Display name, defaults to provider
    system_prompt: str | None = None
    exploration: bool = False  # Enable interactive tool exploration
    timeout: int | None = None  # Agent timeout in seconds (None = use default)

    @property
    def provider_name(self) -> str:
        """Get the provider name as a string."""
        return _get_provider_value(self.provider)

    @property
    def is_builtin_provider(self) -> bool:
        """Check if this uses a built-in provider."""
        return isinstance(self.provider, AgentProvider)

    @property
    def display_name(self) -> str:
        """Get a display name for this agent."""
        if self.name:
            return self.name
        provider_str = _get_provider_value(self.provider)
        if self.model:
            return f"{provider_str}:{self.model}"
        return provider_str


class ToolConfig(BaseModel):
    """Configuration for the tool being evaluated."""

    type: Literal["cli", "docs"] = "cli"
    command: str  # CLI command or path to docs
    help_args: list[str] = Field(default_factory=lambda: ["--help"])
    working_dir: str | None = None
    path_additions: list[str] = Field(default_factory=list)
    """Additional directories to add to PATH when agents run the tool.

    If the tool command is an absolute path (e.g., /srv/code/tool/.venv/bin/mytool),
    its directory is automatically added. Use this field for additional paths needed.
    """

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Ensure command is not empty."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()


class QuestionsConfig(BaseModel):
    """Configuration for session questions/prompts."""

    rounds: list[str] = Field(default_factory=list)

    @field_validator("rounds")
    @classmethod
    def validate_rounds(cls, v: list[str]) -> list[str]:
        """Ensure at least one question is provided."""
        if not v:
            raise ValueError("At least one question round is required")
        return v


class SessionConfig(BaseModel):
    """Configuration for session behavior."""

    name: str | None = None
    mode: SessionMode = SessionMode.SINGLE
    moderator: bool = False
    moderator_agent: AgentConfig | None = None  # Custom moderator agent config
    parallel_agents: bool = True  # Query agents in parallel
    exploration: bool = False  # Allow agents to run tool commands interactively
    agent_timeout: int | None = None  # Timeout for all agents (seconds)
    feedback_schema: FeedbackSchema | None = None  # Schema for structured responses


class OutputConfig(BaseModel):
    """Configuration for session output."""

    format: Literal["json", "markdown", "text"] = "text"
    directory: str | None = None  # Where to save output
    save_log: bool = True  # Whether to persist the session log


class FocusgroupConfig(BaseModel):
    """Complete configuration for a focusgroup session."""

    session: SessionConfig = Field(default_factory=SessionConfig)
    tool: ToolConfig
    agents: list[AgentConfig] = Field(min_length=1)
    questions: QuestionsConfig
    output: OutputConfig = Field(default_factory=OutputConfig)

    @field_validator("agents")
    @classmethod
    def validate_agents(cls, v: list[AgentConfig]) -> list[AgentConfig]:
        """Ensure at least one agent is configured."""
        if not v:
            raise ValueError("At least one agent must be configured")
        return v


def load_config(path: Path) -> FocusgroupConfig:
    """Load and validate a TOML configuration file.

    Args:
        path: Path to the TOML config file

    Returns:
        Validated FocusgroupConfig

    Raises:
        FileNotFoundError: If config file doesn't exist
        tomllib.TOMLDecodeError: If TOML is malformed
        pydantic.ValidationError: If config doesn't match schema
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return FocusgroupConfig.model_validate(data)


def load_agent_preset(path: Path) -> AgentConfig:
    """Load an agent preset from a TOML file.

    Args:
        path: Path to the agent preset TOML

    Returns:
        Validated AgentConfig

    Raises:
        FileNotFoundError: If preset file doesn't exist
        tomllib.TOMLDecodeError: If TOML is malformed
        pydantic.ValidationError: If config doesn't match schema
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    # Agent presets have the config nested under [agent]
    agent_data = data.get("agent", data)
    return AgentConfig.model_validate(agent_data)


def get_default_config_dir() -> Path:
    """Get the default configuration directory.

    Returns ~/.config/focusgroup, creating it if needed.
    """
    config_dir = Path.home() / ".config" / "focusgroup"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_agents_dir() -> Path:
    """Get the directory for agent presets."""
    agents_dir = get_default_config_dir() / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    return agents_dir


def _get_bundled_presets() -> dict[str, Path]:
    """Get bundled presets from the package.

    Returns:
        Dictionary mapping preset name to path within the package.
    """
    presets = {}
    try:
        # Use importlib.resources to find bundled presets
        pkg_files = importlib.resources.files("focusgroup.presets")
        for item in pkg_files.iterdir():
            if item.name.endswith(".toml"):
                name = item.name[:-5]  # Remove .toml suffix
                # Get the actual path (works for both installed and dev)
                presets[name] = Path(str(item))
    except (ModuleNotFoundError, TypeError):
        # Package not installed or presets dir doesn't exist
        pass
    return presets


def list_agent_presets() -> list[tuple[str, Path]]:
    """List all available agent presets.

    Includes both bundled presets (shipped with focusgroup) and user presets
    from ~/.config/focusgroup/agents/. User presets override bundled ones
    with the same name.

    Returns:
        List of (name, path) tuples for each preset
    """
    # Start with bundled presets
    presets = _get_bundled_presets()

    # User presets override bundled ones
    agents_dir = get_agents_dir()
    for path in agents_dir.glob("*.toml"):
        presets[path.stem] = path

    return sorted(presets.items())


def get_preset_path(name: str) -> Path | None:
    """Find the path to a preset by name.

    Checks user presets first, then bundled presets.

    Args:
        name: The preset name (without .toml extension)

    Returns:
        Path to the preset file, or None if not found
    """
    # Check user presets first
    user_path = get_agents_dir() / f"{name}.toml"
    if user_path.exists():
        return user_path

    # Check bundled presets
    bundled = _get_bundled_presets()
    if name in bundled:
        return bundled[name]

    return None


def get_providers_file() -> Path:
    """Get the path to the custom providers config file."""
    return get_default_config_dir() / "providers.toml"


def load_custom_providers() -> dict[str, dict]:
    """Load custom provider definitions from providers.toml.

    Returns:
        Dictionary mapping provider name to its configuration dict.
        Empty dict if file doesn't exist.

    Example providers.toml:
        [gemini]
        command = "gemini"
        prompt_flag = "-p"
        model_flag = "--model"
        timeout = 120

        [ollama]
        command = "ollama run"
        positional_prompt = true
        timeout = 180
    """
    providers_path = get_providers_file()
    if not providers_path.exists():
        return {}

    with open(providers_path, "rb") as f:
        data = tomllib.load(f)

    # Each top-level key is a provider name
    return data


def get_custom_provider_names() -> list[str]:
    """Get list of custom provider names from providers.toml."""
    return list(load_custom_providers().keys())
