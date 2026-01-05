"""Unit tests for configuration loading and validation."""

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from focusgroup.config import (
    AgentConfig,
    AgentMode,
    AgentProvider,
    FocusgroupConfig,
    OutputConfig,
    QuestionsConfig,
    SessionConfig,
    SessionMode,
    ToolConfig,
    get_agents_dir,
    get_default_config_dir,
    list_agent_presets,
    load_agent_preset,
    load_config,
)


class TestEnums:
    """Test configuration enums."""

    def test_session_mode_values(self):
        """Session modes should have expected values."""
        assert SessionMode.SINGLE.value == "single"
        assert SessionMode.DISCUSSION.value == "discussion"
        assert SessionMode.STRUCTURED.value == "structured"

    def test_agent_mode_values(self):
        """Agent modes should have expected values."""
        assert AgentMode.API.value == "api"
        assert AgentMode.CLI.value == "cli"

    def test_agent_provider_values(self):
        """Agent providers should have expected values."""
        assert AgentProvider.CLAUDE.value == "claude"
        assert AgentProvider.OPENAI.value == "openai"
        assert AgentProvider.CODEX.value == "codex"


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_minimal_agent_config(self):
        """Agent config with only required fields."""
        config = AgentConfig(provider=AgentProvider.CLAUDE)
        assert config.provider == AgentProvider.CLAUDE
        assert config.mode == AgentMode.API  # default
        assert config.model is None
        assert config.name is None
        assert config.system_prompt is None

    def test_full_agent_config(self):
        """Agent config with all fields."""
        config = AgentConfig(
            provider=AgentProvider.OPENAI,
            mode=AgentMode.API,
            model="gpt-4o",
            name="GPT Expert",
            system_prompt="You are a helpful assistant.",
        )
        assert config.provider == AgentProvider.OPENAI
        assert config.model == "gpt-4o"
        assert config.name == "GPT Expert"

    def test_display_name_with_custom_name(self):
        """Display name should use custom name when set."""
        config = AgentConfig(provider=AgentProvider.CLAUDE, name="Custom Agent")
        assert config.display_name == "Custom Agent"

    def test_display_name_with_model(self):
        """Display name should combine provider:model when no custom name."""
        config = AgentConfig(provider=AgentProvider.CLAUDE, model="opus")
        assert config.display_name == "claude:opus"

    def test_display_name_provider_only(self):
        """Display name should fall back to provider."""
        config = AgentConfig(provider=AgentProvider.OPENAI)
        assert config.display_name == "openai"


class TestToolConfig:
    """Test ToolConfig model."""

    def test_minimal_tool_config(self):
        """Tool config with only required command."""
        config = ToolConfig(command="mx")
        assert config.command == "mx"
        assert config.type == "cli"  # default
        assert config.help_args == ["--help"]  # default
        assert config.working_dir is None

    def test_docs_type_tool_config(self):
        """Tool config for documentation type."""
        config = ToolConfig(type="docs", command="./README.md")
        assert config.type == "docs"
        assert config.command == "./README.md"

    def test_empty_command_rejected(self):
        """Empty command should raise validation error."""
        with pytest.raises(ValueError, match="Command cannot be empty"):
            ToolConfig(command="")

    def test_whitespace_command_rejected(self):
        """Whitespace-only command should raise validation error."""
        with pytest.raises(ValueError, match="Command cannot be empty"):
            ToolConfig(command="   ")

    def test_command_whitespace_stripped(self):
        """Command with surrounding whitespace should be stripped."""
        config = ToolConfig(command="  mx  ")
        assert config.command == "mx"


class TestQuestionsConfig:
    """Test QuestionsConfig model."""

    def test_single_question(self):
        """Questions config with one round."""
        config = QuestionsConfig(rounds=["What do you think?"])
        assert len(config.rounds) == 1
        assert config.rounds[0] == "What do you think?"

    def test_multiple_questions(self):
        """Questions config with multiple rounds."""
        questions = ["Question 1", "Question 2", "Question 3"]
        config = QuestionsConfig(rounds=questions)
        assert len(config.rounds) == 3

    def test_empty_rounds_rejected(self):
        """Empty rounds list should raise validation error."""
        with pytest.raises(ValueError, match="At least one question"):
            QuestionsConfig(rounds=[])


class TestSessionConfig:
    """Test SessionConfig model."""

    def test_default_session_config(self):
        """Session config with all defaults."""
        config = SessionConfig()
        assert config.name is None
        assert config.mode == SessionMode.SINGLE
        assert config.moderator is False
        assert config.parallel_agents is True

    def test_custom_session_config(self):
        """Session config with custom values."""
        config = SessionConfig(
            name="Test Session",
            mode=SessionMode.DISCUSSION,
            moderator=True,
            parallel_agents=False,
        )
        assert config.name == "Test Session"
        assert config.mode == SessionMode.DISCUSSION
        assert config.moderator is True


class TestOutputConfig:
    """Test OutputConfig model."""

    def test_default_output_config(self):
        """Output config with defaults."""
        config = OutputConfig()
        assert config.format == "text"
        assert config.directory is None
        assert config.save_log is True

    def test_json_format(self):
        """Output config with JSON format."""
        config = OutputConfig(format="json", directory="./output")
        assert config.format == "json"
        assert config.directory == "./output"


class TestFocusgroupConfig:
    """Test complete FocusgroupConfig model."""

    def test_minimal_config(self):
        """Config with minimal required fields."""
        config = FocusgroupConfig(
            tool=ToolConfig(command="mx"),
            agents=[AgentConfig(provider=AgentProvider.CLAUDE)],
            questions=QuestionsConfig(rounds=["What's your opinion?"]),
        )
        assert config.tool.command == "mx"
        assert len(config.agents) == 1
        assert config.session.mode == SessionMode.SINGLE  # default

    def test_empty_agents_rejected(self):
        """Config with no agents should fail validation."""
        # Pydantic raises ValidationError due to min_length=1 constraint
        with pytest.raises(ValidationError):
            FocusgroupConfig(
                tool=ToolConfig(command="mx"),
                agents=[],
                questions=QuestionsConfig(rounds=["Question?"]),
            )


class TestLoadConfig:
    """Test TOML config file loading."""

    def test_load_valid_config(self, tmp_path: Path):
        """Load a valid TOML config file."""
        config_content = """
[session]
name = "Test Session"
mode = "single"

[tool]
command = "mx"

[[agents]]
provider = "claude"
mode = "api"
model = "claude-sonnet-4-20250514"

[questions]
rounds = ["How usable is this CLI?", "What would you improve?"]

[output]
format = "json"
"""
        config_file = tmp_path / "test.toml"
        config_file.write_text(config_content)

        config = load_config(config_file)
        assert config.session.name == "Test Session"
        assert config.tool.command == "mx"
        assert len(config.agents) == 1
        assert config.agents[0].provider == AgentProvider.CLAUDE
        assert len(config.questions.rounds) == 2
        assert config.output.format == "json"

    def test_load_config_multiple_agents(self, tmp_path: Path):
        """Load config with multiple agents."""
        config_content = """
[tool]
command = "beads"

[[agents]]
provider = "claude"
name = "Claude Expert"

[[agents]]
provider = "openai"
model = "gpt-4o"

[[agents]]
provider = "codex"
mode = "cli"

[questions]
rounds = ["Evaluate this tool"]
"""
        config_file = tmp_path / "multi.toml"
        config_file.write_text(config_content)

        config = load_config(config_file)
        assert len(config.agents) == 3
        assert config.agents[0].name == "Claude Expert"
        assert config.agents[1].model == "gpt-4o"
        assert config.agents[2].mode == AgentMode.CLI

    def test_load_config_file_not_found(self, tmp_path: Path):
        """Loading non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.toml")

    def test_load_config_invalid_toml(self, tmp_path: Path):
        """Loading malformed TOML should raise error."""
        config_file = tmp_path / "bad.toml"
        config_file.write_text("this is not valid = = toml")

        with pytest.raises(tomllib.TOMLDecodeError):
            load_config(config_file)

    def test_load_config_missing_required_field(self, tmp_path: Path):
        """Config missing required fields should fail validation."""
        config_content = """
[session]
name = "Missing tool"

[questions]
rounds = ["Question?"]
"""
        config_file = tmp_path / "incomplete.toml"
        config_file.write_text(config_content)

        with pytest.raises(ValidationError):
            load_config(config_file)


class TestAgentPresets:
    """Test agent preset loading."""

    def test_load_agent_preset(self, tmp_path: Path):
        """Load an agent preset file."""
        preset_content = """
[agent]
provider = "claude"
mode = "api"
model = "claude-sonnet-4-20250514"
name = "Sonnet Expert"
system_prompt = "You are a CLI tool expert."
"""
        preset_file = tmp_path / "sonnet.toml"
        preset_file.write_text(preset_content)

        preset = load_agent_preset(preset_file)
        assert preset.provider == AgentProvider.CLAUDE
        assert preset.model == "claude-sonnet-4-20250514"
        assert preset.name == "Sonnet Expert"
        assert "CLI tool expert" in preset.system_prompt

    def test_load_agent_preset_without_wrapper(self, tmp_path: Path):
        """Load preset without [agent] wrapper."""
        preset_content = """
provider = "openai"
model = "gpt-4o"
"""
        preset_file = tmp_path / "gpt4.toml"
        preset_file.write_text(preset_content)

        preset = load_agent_preset(preset_file)
        assert preset.provider == AgentProvider.OPENAI
        assert preset.model == "gpt-4o"


class TestConfigDirectories:
    """Test config directory utilities."""

    def test_get_default_config_dir(self):
        """Default config dir should be under home."""
        config_dir = get_default_config_dir()
        assert config_dir.is_dir()
        assert "focusgroup" in str(config_dir)

    def test_get_agents_dir(self):
        """Agents dir should be under config dir."""
        agents_dir = get_agents_dir()
        assert agents_dir.is_dir()
        assert "agents" in str(agents_dir)

    def test_list_agent_presets_empty(self, monkeypatch, tmp_path: Path):
        """List presets returns empty when none exist."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        presets = list_agent_presets()
        assert presets == []

    def test_list_agent_presets(self, monkeypatch, tmp_path: Path):
        """List presets returns available presets."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create some preset files
        (agents_dir / "claude.toml").write_text('provider = "claude"')
        (agents_dir / "openai.toml").write_text('provider = "openai"')
        (agents_dir / "not_toml.txt").write_text("ignored")

        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        presets = list_agent_presets()
        names = [name for name, _ in presets]
        assert len(presets) == 2
        assert "claude" in names
        assert "openai" in names
