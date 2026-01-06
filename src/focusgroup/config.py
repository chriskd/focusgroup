"""Configuration models and loading for focusgroup sessions."""

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
    """Supported agent providers (CLI-only)."""

    CLAUDE = "claude"
    CODEX = "codex"


class AgentConfig(BaseModel):
    """Configuration for a single agent in the panel."""

    provider: AgentProvider
    model: str | None = None
    name: str | None = None  # Display name, defaults to provider
    system_prompt: str | None = None
    exploration: bool = False  # Enable interactive tool exploration
    timeout: int | None = None  # Agent timeout in seconds (None = use default)

    @property
    def display_name(self) -> str:
        """Get a display name for this agent."""
        if self.name:
            return self.name
        if self.model:
            return f"{self.provider.value}:{self.model}"
        return self.provider.value


class ToolConfig(BaseModel):
    """Configuration for the tool being evaluated."""

    type: Literal["cli", "docs"] = "cli"
    command: str  # CLI command or path to docs
    help_args: list[str] = Field(default_factory=lambda: ["--help"])
    working_dir: str | None = None

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


def list_agent_presets() -> list[tuple[str, Path]]:
    """List all available agent presets.

    Returns:
        List of (name, path) tuples for each preset
    """
    agents_dir = get_agents_dir()
    presets = []
    for path in agents_dir.glob("*.toml"):
        presets.append((path.stem, path))
    return sorted(presets)
