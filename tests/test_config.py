"""Unit tests for configuration loading and validation."""

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from focusgroup.config import (
    AgentConfig,
    AgentProvider,
    FeedbackSchema,
    FocusgroupConfig,
    OutputConfig,
    QuestionsConfig,
    SchemaField,
    SchemaFieldType,
    SessionConfig,
    SessionMode,
    ToolConfig,
    get_agents_dir,
    get_default_config_dir,
    get_schema_preset,
    list_agent_presets,
    list_schema_presets,
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

    def test_agent_provider_values(self):
        """Agent providers should have expected values."""
        assert AgentProvider.CLAUDE.value == "claude"
        assert AgentProvider.CODEX.value == "codex"


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_minimal_agent_config(self):
        """Agent config with only required fields."""
        config = AgentConfig(provider=AgentProvider.CLAUDE)
        assert config.provider == AgentProvider.CLAUDE
        assert config.model is None
        assert config.name is None
        assert config.system_prompt is None

    def test_full_agent_config(self):
        """Agent config with all fields."""
        config = AgentConfig(
            provider=AgentProvider.CODEX,
            model="o3-mini",
            name="Codex Expert",
            system_prompt="You are a helpful assistant.",
        )
        assert config.provider == AgentProvider.CODEX
        assert config.model == "o3-mini"
        assert config.name == "Codex Expert"

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
        config = AgentConfig(provider=AgentProvider.CODEX)
        assert config.display_name == "codex"


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
provider = "codex"
model = "o3-mini"

[questions]
rounds = ["Evaluate this tool"]
"""
        config_file = tmp_path / "multi.toml"
        config_file.write_text(config_content)

        config = load_config(config_file)
        assert len(config.agents) == 2
        assert config.agents[0].name == "Claude Expert"
        assert config.agents[1].model == "o3-mini"

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
provider = "codex"
model = "o3-mini"
"""
        preset_file = tmp_path / "codex.toml"
        preset_file.write_text(preset_content)

        preset = load_agent_preset(preset_file)
        assert preset.provider == AgentProvider.CODEX
        assert preset.model == "o3-mini"


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
        """List presets returns empty when none exist (with bundled disabled)."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)
        # Disable bundled presets to test user presets in isolation
        monkeypatch.setattr("focusgroup.config._get_bundled_presets", lambda: {})

        presets = list_agent_presets()
        assert presets == []

    def test_list_agent_presets(self, monkeypatch, tmp_path: Path):
        """List presets returns available presets."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()

        # Create some preset files
        (agents_dir / "claude.toml").write_text('provider = "claude"')
        (agents_dir / "codex.toml").write_text('provider = "codex"')
        (agents_dir / "not_toml.txt").write_text("ignored")

        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)
        # Disable bundled presets to test user presets in isolation
        monkeypatch.setattr("focusgroup.config._get_bundled_presets", lambda: {})

        presets = list_agent_presets()
        names = [name for name, _ in presets]
        assert len(presets) == 2
        assert "claude" in names
        assert "codex" in names


class TestSchemaField:
    """Test SchemaField model."""

    def test_minimal_schema_field(self):
        """Schema field with just name."""
        field = SchemaField(name="rating")
        assert field.name == "rating"
        assert field.type == SchemaFieldType.STRING  # default
        assert field.required is True

    def test_integer_field_with_range(self):
        """Schema field for integer with min/max."""
        field = SchemaField(
            name="score",
            type=SchemaFieldType.INTEGER,
            min_value=1,
            max_value=10,
            description="Score from 1 to 10",
        )
        assert field.min_value == 1
        assert field.max_value == 10
        assert field.description == "Score from 1 to 10"

    def test_list_field(self):
        """Schema field for list of strings."""
        field = SchemaField(
            name="pros",
            type=SchemaFieldType.LIST,
            description="Positive aspects",
        )
        assert field.type == SchemaFieldType.LIST

    def test_invalid_field_name_rejected(self):
        """Field name must be valid identifier."""
        with pytest.raises(ValueError, match="valid identifier"):
            SchemaField(name="invalid-name")

    def test_optional_field(self):
        """Schema field can be optional."""
        field = SchemaField(name="notes", required=False)
        assert field.required is False


class TestFeedbackSchema:
    """Test FeedbackSchema model."""

    def test_minimal_schema(self):
        """Schema with one field."""
        schema = FeedbackSchema(fields=[SchemaField(name="rating", type=SchemaFieldType.INTEGER)])
        assert len(schema.fields) == 1
        assert schema.include_raw_response is True

    def test_schema_to_json_schema(self):
        """Convert FeedbackSchema to JSON Schema format."""
        schema = FeedbackSchema(
            fields=[
                SchemaField(
                    name="rating",
                    type=SchemaFieldType.INTEGER,
                    min_value=1,
                    max_value=5,
                    description="Rating from 1-5",
                ),
                SchemaField(
                    name="pros",
                    type=SchemaFieldType.LIST,
                    description="Positive aspects",
                ),
                SchemaField(
                    name="notes",
                    type=SchemaFieldType.STRING,
                    required=False,
                ),
            ]
        )

        json_schema = schema.to_json_schema()

        assert json_schema["type"] == "object"
        assert "rating" in json_schema["properties"]
        assert "pros" in json_schema["properties"]
        assert "notes" in json_schema["properties"]

        # Required should only include required fields
        assert "rating" in json_schema["required"]
        assert "pros" in json_schema["required"]
        assert "notes" not in json_schema["required"]

        # Integer field should have min/max
        rating_prop = json_schema["properties"]["rating"]
        assert rating_prop["type"] == "integer"
        assert rating_prop["minimum"] == 1
        assert rating_prop["maximum"] == 5

        # List field should have array type
        pros_prop = json_schema["properties"]["pros"]
        assert pros_prop["type"] == "array"
        assert pros_prop["items"]["type"] == "string"

    def test_schema_to_prompt_instructions(self):
        """Generate prompt instructions from schema."""
        schema = FeedbackSchema(
            fields=[
                SchemaField(
                    name="rating",
                    type=SchemaFieldType.INTEGER,
                    min_value=1,
                    max_value=5,
                ),
            ]
        )

        instructions = schema.to_prompt_instructions()

        assert "IMPORTANT" in instructions
        assert "JSON" in instructions
        assert "rating" in instructions
        assert "1-5" in instructions

    def test_empty_fields_rejected(self):
        """Schema must have at least one field."""
        with pytest.raises(ValidationError):
            FeedbackSchema(fields=[])


class TestSchemaPresets:
    """Test built-in schema presets."""

    def test_list_schema_presets(self):
        """List available schema presets."""
        presets = list_schema_presets()
        assert "rating" in presets
        assert "pros-cons" in presets
        assert "review" in presets

    def test_get_rating_preset(self):
        """Get the rating schema preset."""
        schema = get_schema_preset("rating")
        assert schema is not None
        field_names = [f.name for f in schema.fields]
        assert "rating" in field_names
        assert "reasoning" in field_names

    def test_get_pros_cons_preset(self):
        """Get the pros-cons schema preset."""
        schema = get_schema_preset("pros-cons")
        assert schema is not None
        field_names = [f.name for f in schema.fields]
        assert "pros" in field_names
        assert "cons" in field_names
        assert "summary" in field_names

    def test_get_review_preset(self):
        """Get the full review schema preset."""
        schema = get_schema_preset("review")
        assert schema is not None
        field_names = [f.name for f in schema.fields]
        assert "rating" in field_names
        assert "pros" in field_names
        assert "cons" in field_names
        assert "suggestions" in field_names

    def test_get_unknown_preset_returns_none(self):
        """Unknown preset returns None."""
        schema = get_schema_preset("nonexistent")
        assert schema is None


class TestSessionConfigWithSchema:
    """Test SessionConfig with feedback_schema field."""

    def test_session_config_with_schema(self):
        """Session config can include feedback schema."""
        schema = FeedbackSchema(fields=[SchemaField(name="rating", type=SchemaFieldType.INTEGER)])
        config = SessionConfig(feedback_schema=schema)
        assert config.feedback_schema is not None
        assert len(config.feedback_schema.fields) == 1

    def test_session_config_without_schema(self):
        """Session config without schema has None."""
        config = SessionConfig()
        assert config.feedback_schema is None
