"""Integration tests for CLI commands."""

from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from focusgroup.cli import app, infer_tool_from_context
from focusgroup.storage.session_log import AgentResponse, QuestionRound, SessionLog

runner = CliRunner()


class TestMainApp:
    """Test main CLI app."""

    def test_help_shows_description(self):
        """Help text shows application description."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Gather feedback from multiple LLM agents" in result.stdout

    def test_version_flag(self):
        """--version flag shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "focusgroup" in result.stdout.lower()

    def test_no_args_shows_help(self):
        """Running without args shows help (exit code 2 due to no_args_is_help)."""
        result = runner.invoke(app, [])
        # Typer with no_args_is_help=True returns exit code 0, but shows usage
        # The help text should be shown regardless
        assert "Usage:" in result.stdout or "Commands:" in result.stdout


class TestRunCommand:
    """Test 'run' command."""

    def test_run_missing_config(self, tmp_path: Path):
        """Run with non-existent config shows error."""
        result = runner.invoke(app, ["run", str(tmp_path / "missing.toml")])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_run_invalid_config(self, tmp_path: Path):
        """Run with invalid config shows error."""
        bad_config = tmp_path / "bad.toml"
        bad_config.write_text("not valid toml = = =")

        result = runner.invoke(app, ["run", str(bad_config)])
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()

    def test_run_dry_run(self, tmp_path: Path):
        """Dry run shows session plan without executing."""
        config_content = """
[session]
name = "Test Session"
mode = "single"
moderator = true

[tool]
command = "mx"

[[agents]]
provider = "claude"
name = "Claude Expert"
model = "claude-sonnet-4-20250514"

[[agents]]
provider = "codex"
name = "Codex Expert"

[questions]
rounds = [
    "How usable is this CLI?",
    "What would you improve?"
]

[output]
format = "json"
"""
        config_file = tmp_path / "session.toml"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["run", str(config_file), "--dry-run"])

        assert result.exit_code == 0
        assert "Session Plan" in result.stdout
        assert "mx" in result.stdout
        assert "single" in result.stdout
        assert "enabled" in result.stdout  # moderator
        assert "Claude Expert" in result.stdout
        assert "Codex Expert" in result.stdout
        assert "How usable" in result.stdout
        assert "2" in result.stdout  # Two questions

    def test_run_dry_run_json_output(self, tmp_path: Path):
        """Dry run with --json outputs parseable JSON."""
        import json

        config_content = """
[session]
name = "Test Session"
mode = "single"
moderator = true

[tool]
command = "mx"

[[agents]]
provider = "claude"
name = "Claude Expert"
model = "claude-sonnet-4-20250514"

[[agents]]
provider = "codex"
name = "Codex Expert"

[questions]
rounds = [
    "How usable is this CLI?",
    "What would you improve?"
]

[output]
format = "json"
"""
        config_file = tmp_path / "session.toml"
        config_file.write_text(config_content)

        result = runner.invoke(app, ["run", str(config_file), "--dry-run", "--json"])

        assert result.exit_code == 0
        # Output should be valid JSON
        data = json.loads(result.stdout)
        assert data["tool"] == "mx"
        assert data["mode"] == "single"
        assert data["moderator_enabled"] is True
        assert len(data["agents"]) == 2
        assert len(data["questions"]) == 2
        assert data["agents"][0]["name"] == "Claude Expert"


class TestAgentsCommands:
    """Test 'agents' subcommand group."""

    def test_agents_list_help(self):
        """Agents list shows help."""
        result = runner.invoke(app, ["agents", "list", "--help"])
        assert result.exit_code == 0
        assert "List available agent presets" in result.stdout

    def test_agents_list_empty(self, monkeypatch, tmp_path: Path):
        """Agents list shows message when no presets."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.cli.get_agents_dir", lambda: agents_dir)
        monkeypatch.setattr("focusgroup.cli.list_agent_presets", lambda: [])

        result = runner.invoke(app, ["agents", "list"])

        assert result.exit_code == 0
        assert "No agent presets found" in result.stdout

    def test_agents_show_not_found(self, monkeypatch, tmp_path: Path):
        """Agents show with non-existent preset shows error."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.cli.get_agents_dir", lambda: agents_dir)

        result = runner.invoke(app, ["agents", "show", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestLogsCommands:
    """Test 'logs' subcommand group."""

    def test_logs_list_help(self):
        """Logs list shows help."""
        result = runner.invoke(app, ["logs", "list", "--help"])
        assert result.exit_code == 0
        assert "List past session logs" in result.stdout

    def test_logs_list_empty(self, monkeypatch):
        """Logs list shows message when no sessions."""
        mock_storage = MagicMock()
        mock_storage.list_sessions.return_value = []
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "list"])

        assert result.exit_code == 0
        assert "No sessions found" in result.stdout

    def test_logs_list_with_sessions(self, monkeypatch):
        """Logs list shows table of sessions."""
        mock_storage = MagicMock()
        mock_storage.list_sessions.return_value = [
            SessionLog(
                id="abc123",
                tool="mx",
                mode="single",
                agent_count=2,
                rounds=[QuestionRound(round_number=0, question="Test?")],
                completed_at=datetime.now(),
            ),
        ]
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "list"])

        assert result.exit_code == 0
        assert "mx" in result.stdout
        assert "single" in result.stdout

    def test_logs_list_with_limit(self, monkeypatch):
        """Logs list respects --limit option."""
        mock_storage = MagicMock()
        mock_storage.list_sessions.return_value = []
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        runner.invoke(app, ["logs", "list", "--limit", "5"])

        mock_storage.list_sessions.assert_called_with(limit=5, tool_filter=None)

    def test_logs_list_with_tool_filter(self, monkeypatch):
        """Logs list respects --tool option."""
        mock_storage = MagicMock()
        mock_storage.list_sessions.return_value = []
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        runner.invoke(app, ["logs", "list", "--tool", "mx"])

        mock_storage.list_sessions.assert_called_with(limit=10, tool_filter="mx")

    def test_logs_show_not_found(self, monkeypatch):
        """Logs show with non-existent session shows error."""
        mock_storage = MagicMock()
        mock_storage.load.side_effect = FileNotFoundError("Session not found")
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "show", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_logs_show_displays_session(self, monkeypatch):
        """Logs show displays session content."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(
            id="test123",
            tool="mx",
            mode="single",
            agent_count=1,
            rounds=[
                QuestionRound(
                    round_number=0,
                    question="Test question?",
                    responses=[
                        AgentResponse(
                            agent_name="Agent-1",
                            provider="claude",
                            prompt="Test question?",
                            response="Test response",
                        ),
                    ],
                ),
            ],
        )
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "show", "test123"])

        assert result.exit_code == 0
        assert "mx" in result.stdout
        assert "Test question" in result.stdout or "Test response" in result.stdout

    def test_logs_show_json_format(self, monkeypatch):
        """Logs show with --format json outputs JSON."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(
            id="test123",
            tool="mx",
            mode="single",
            agent_count=0,
            rounds=[],
        )
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "show", "test123", "--format", "json"])

        assert result.exit_code == 0
        # Should be valid JSON structure
        assert "tool" in result.stdout
        assert "mx" in result.stdout

    def test_logs_export_not_found(self, monkeypatch):
        """Logs export with non-existent session shows error."""
        mock_storage = MagicMock()
        mock_storage.load.side_effect = FileNotFoundError("Session not found")
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "export", "nonexistent"])

        assert result.exit_code == 1

    def test_logs_export_creates_file(self, monkeypatch, tmp_path: Path):
        """Logs export creates output file."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(
            id="test123",
            tool="mx",
            mode="single",
            agent_count=1,
            rounds=[],
        )
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        output_file = tmp_path / "export.md"
        result = runner.invoke(app, ["logs", "export", "test123", "--output", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Exported" in result.stdout

    def test_logs_delete_not_found(self, monkeypatch):
        """Logs delete with non-existent session shows error."""
        mock_storage = MagicMock()
        mock_storage.load.side_effect = FileNotFoundError("Session not found")
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "delete", "nonexistent"])

        assert result.exit_code == 1

    def test_logs_delete_cancelled(self, monkeypatch):
        """Logs delete cancellation works."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(id="test123", tool="mx")
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        # Simulate user typing 'n' to cancel
        result = runner.invoke(app, ["logs", "delete", "test123"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        mock_storage.delete.assert_not_called()

    def test_logs_delete_confirmed(self, monkeypatch):
        """Logs delete with confirmation works."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(id="test123", tool="mx")
        mock_storage.delete.return_value = True
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        # Simulate user typing 'y' to confirm
        result = runner.invoke(app, ["logs", "delete", "test123"], input="y\n")

        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        mock_storage.delete.assert_called_once()

    def test_logs_delete_force(self, monkeypatch):
        """Logs delete with --force skips confirmation."""
        mock_storage = MagicMock()
        mock_storage.load.return_value = SessionLog(id="test123", tool="mx")
        mock_storage.delete.return_value = True
        monkeypatch.setattr("focusgroup.cli.get_default_storage", lambda: mock_storage)

        result = runner.invoke(app, ["logs", "delete", "test123", "--force"])

        assert result.exit_code == 0
        assert "Deleted" in result.stdout
        mock_storage.delete.assert_called_once()


class TestAskCommand:
    """Test 'ask' command."""

    def test_ask_help(self):
        """Ask command shows help."""
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0
        assert "Quick ad-hoc query" in result.stdout

    def test_ask_invalid_provider(self):
        """Ask with invalid provider shows error."""
        result = runner.invoke(
            app,
            ["ask", "What's good?", "--context", "mx --help", "--provider", "invalid"],
        )
        assert result.exit_code == 1
        assert "Unknown provider" in result.stdout

    @patch("focusgroup.cli.asyncio.run")
    def test_ask_invokes_async(self, mock_run):
        """Ask command invokes async implementation."""
        mock_run.return_value = None
        runner.invoke(app, ["ask", "What's good?", "--context", "echo test"])

        # Should have called asyncio.run with the async implementation
        mock_run.assert_called_once()

    def test_ask_requires_context(self):
        """Ask command requires --context option."""
        result = runner.invoke(app, ["ask", "What's good?"])
        assert result.exit_code == 2
        # Typer puts required option error in output (stdout or stderr combined)
        assert "--context" in result.output

    @patch("focusgroup.cli.asyncio.run")
    def test_ask_infers_tool_from_command_context(self, mock_run):
        """Ask command infers tool name from command context."""
        mock_run.return_value = None
        result = runner.invoke(app, ["ask", "What's good?", "--context", "mytool --help"])
        assert result.exit_code == 0
        # The call should have used 'mytool' as the inferred tool name
        mock_run.assert_called_once()

    @patch("focusgroup.cli.asyncio.run")
    def test_ask_tool_override(self, mock_run):
        """Ask command allows explicit --tool override."""
        mock_run.return_value = None
        result = runner.invoke(
            app,
            ["ask", "What's good?", "--context", "mx --help", "--tool", "memex"],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("focusgroup.cli.asyncio.run")
    def test_ask_reads_context_from_stdin(self, mock_run):
        """Ask command reads context from stdin when - is provided."""
        mock_run.return_value = None
        result = runner.invoke(
            app,
            ["ask", "Review this?", "--context", "-", "--tool", "myapi"],
            input="This is content piped from stdin",
        )
        assert result.exit_code == 0
        mock_run.assert_called_once()


class TestInferToolFromContext:
    """Test tool name inference from context."""

    def test_infer_from_command_first_token(self):
        """Infers tool name from first token of command."""
        assert infer_tool_from_context("mx --help") == "mx"
        assert infer_tool_from_context("focusgroup doctor") == "focusgroup"
        assert infer_tool_from_context("python script.py") == "python"

    def test_infer_from_file_context_stem(self):
        """Infers tool name from file stem when using @ prefix."""
        assert infer_tool_from_context("@README.md") == "README"
        assert infer_tool_from_context("@path/to/docs.txt") == "docs"
        assert infer_tool_from_context("@src/config.py") == "config"

    def test_infer_handles_whitespace(self):
        """Handles leading/trailing whitespace in context."""
        assert infer_tool_from_context("  mx --help  ") == "mx"
        assert infer_tool_from_context("  @README.md  ") == "README"

    def test_infer_fallback_to_unknown(self):
        """Returns 'unknown' for empty or unparseable context."""
        assert infer_tool_from_context("") == "unknown"
        assert infer_tool_from_context("   ") == "unknown"
        assert infer_tool_from_context("@") == "unknown"

    def test_infer_from_stdin_returns_unknown(self):
        """Returns 'unknown' for stdin context marker."""
        assert infer_tool_from_context("-") == "unknown"


class TestConfigValidation:
    """Test config validation through CLI."""

    def test_config_missing_tool(self, tmp_path: Path):
        """Config without tool section fails."""
        config = tmp_path / "missing_tool.toml"
        config.write_text("""
[[agents]]
provider = "claude"

[questions]
rounds = ["Test?"]
""")
        result = runner.invoke(app, ["run", str(config)])
        assert result.exit_code == 1

    def test_config_missing_agents(self, tmp_path: Path):
        """Config without agents fails."""
        config = tmp_path / "missing_agents.toml"
        config.write_text("""
[tool]
command = "mx"

[questions]
rounds = ["Test?"]
""")
        result = runner.invoke(app, ["run", str(config)])
        assert result.exit_code == 1

    def test_config_missing_questions(self, tmp_path: Path):
        """Config without questions fails."""
        config = tmp_path / "missing_questions.toml"
        config.write_text("""
[tool]
command = "mx"

[[agents]]
provider = "claude"
""")
        result = runner.invoke(app, ["run", str(config)])
        assert result.exit_code == 1

    def test_config_empty_questions(self, tmp_path: Path):
        """Config with empty questions fails."""
        config = tmp_path / "empty_questions.toml"
        config.write_text("""
[tool]
command = "mx"

[[agents]]
provider = "claude"

[questions]
rounds = []
""")
        result = runner.invoke(app, ["run", str(config)])
        assert result.exit_code == 1


class TestCliOutputFormats:
    """Test CLI output format handling."""

    def test_dry_run_different_formats(self, tmp_path: Path):
        """Dry run works regardless of output format."""
        config_content = """
[tool]
command = "mx"

[[agents]]
provider = "claude"

[questions]
rounds = ["Test?"]

[output]
format = "json"
"""
        config = tmp_path / "test.toml"
        config.write_text(config_content)

        for fmt in ["json", "markdown", "text"]:
            config_content_fmt = config_content.replace('format = "json"', f'format = "{fmt}"')
            config.write_text(config_content_fmt)

            result = runner.invoke(app, ["run", str(config), "--dry-run"])
            assert result.exit_code == 0, f"Failed for format: {fmt}"


class TestInitCommand:
    """Test 'init' command."""

    def test_init_help(self):
        """Init command shows help."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize a new focusgroup session config" in result.stdout

    def test_init_quick_mode(self, tmp_path: Path, monkeypatch):
        """Init with --quick creates config with defaults."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "--quick"])

        assert result.exit_code == 0
        assert "Created config" in result.stdout

        # Check file was created
        config_file = tmp_path / "focusgroup.toml"
        assert config_file.exists()

        # Verify it's valid TOML that can be loaded
        from focusgroup.config import load_config

        config = load_config(config_file)
        assert config.tool.command == "mytool"
        assert len(config.agents) == 2
        assert len(config.questions.rounds) == 2

    def test_init_quick_with_tool(self, tmp_path: Path, monkeypatch):
        """Init with --quick and --tool uses custom tool name."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "--tool", "mx", "--quick"])

        assert result.exit_code == 0

        # Check file name is based on tool
        config_file = tmp_path / "mx.toml"
        assert config_file.exists()

        from focusgroup.config import load_config

        config = load_config(config_file)
        assert config.tool.command == "mx"

    def test_init_quick_with_provider(self, tmp_path: Path, monkeypatch):
        """Init with --quick and --provider uses custom provider."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["init", "--tool", "test", "--provider", "codex", "--quick"])

        assert result.exit_code == 0

        config_file = tmp_path / "test.toml"
        from focusgroup.config import load_config

        config = load_config(config_file)
        assert all(agent.provider_name == "codex" for agent in config.agents)

    def test_init_custom_output(self, tmp_path: Path, monkeypatch):
        """Init with --output creates config at custom path."""
        monkeypatch.chdir(tmp_path)
        custom_path = tmp_path / "custom" / "session.toml"

        # Create parent directory
        custom_path.parent.mkdir(parents=True)

        result = runner.invoke(app, ["init", "--output", str(custom_path), "--quick"])

        assert result.exit_code == 0
        assert custom_path.exists()

    def test_init_interactive_accepts_defaults(self, tmp_path: Path, monkeypatch):
        """Init in interactive mode accepts default values."""
        monkeypatch.chdir(tmp_path)

        # Simulate pressing Enter for all prompts (accept defaults)
        # Tool, provider, mode, num_agents, q1, q2, q3 (empty), format,
        # moderator (n), exploration (n) = 8 Enter + 2 n
        input_sequence = "\n" * 8 + "n\nn\n"

        result = runner.invoke(app, ["init"], input=input_sequence)

        assert result.exit_code == 0
        assert "Created config" in result.stdout

        config_file = tmp_path / "focusgroup.toml"
        assert config_file.exists()

    def test_init_overwrite_cancelled(self, tmp_path: Path, monkeypatch):
        """Init cancels when file exists and user declines overwrite."""
        monkeypatch.chdir(tmp_path)

        # Create existing file
        existing = tmp_path / "focusgroup.toml"
        existing.write_text("[tool]\ncommand = 'old'")

        # Simulate 'n' for overwrite prompt
        result = runner.invoke(app, ["init"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.stdout

        # File should be unchanged
        assert "old" in existing.read_text()

    def test_init_overwrite_confirmed(self, tmp_path: Path, monkeypatch):
        """Init overwrites when file exists and user confirms."""
        monkeypatch.chdir(tmp_path)

        # Create existing file
        existing = tmp_path / "focusgroup.toml"
        existing.write_text("[tool]\ncommand = 'old'")

        # Simulate 'y' for overwrite, then defaults for everything else
        # y + 8 Enter + 2 n
        input_sequence = "y\n" + "\n" * 8 + "n\nn\n"
        result = runner.invoke(app, ["init"], input=input_sequence)

        assert result.exit_code == 0
        assert "Created config" in result.stdout

        # File should be overwritten
        assert "old" not in existing.read_text()

    def test_init_generates_valid_toml(self, tmp_path: Path, monkeypatch):
        """Init generates valid TOML that loads and validates."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["init", "--tool", "myapp", "--provider", "claude", "--quick"],
        )

        assert result.exit_code == 0

        config_file = tmp_path / "myapp.toml"
        content = config_file.read_text()

        # Check for expected sections
        assert "[session]" in content
        assert "[tool]" in content
        assert "[[agents]]" in content
        assert "[questions]" in content
        assert "[output]" in content

        # Verify it loads properly
        from focusgroup.config import load_config

        config = load_config(config_file)
        assert config.session.name == "myapp-feedback"
        assert config.tool.command == "myapp"

    def test_init_quick_mode_no_overwrite_prompt(self, tmp_path: Path, monkeypatch):
        """Init with --quick doesn't prompt for overwrite, just overwrites."""
        monkeypatch.chdir(tmp_path)

        # Create existing file
        existing = tmp_path / "focusgroup.toml"
        existing.write_text("[tool]\ncommand = 'old'")

        # No input provided - quick mode should not prompt
        result = runner.invoke(app, ["init", "--quick"])

        assert result.exit_code == 0
        assert "Created config" in result.stdout

        # File should be overwritten
        content = existing.read_text()
        assert "old" not in content
        assert "mytool" in content


class TestDoctorCommand:
    """Test 'doctor' command."""

    def test_doctor_help(self):
        """Doctor command shows help."""
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "Check focusgroup setup" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    def test_doctor_all_providers_installed(self, mock_run, tmp_path: Path, monkeypatch):
        """Doctor shows success when all providers are installed."""
        # Mock config directories
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        # Mock subprocess to return success for both CLIs
        mock_run.return_value = CompletedProcess(
            args=["test", "--version"],
            returncode=0,
            stdout="test-cli 1.0.0",
            stderr="",
        )

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "All checks passed" in result.stdout
        assert "✓" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    def test_doctor_missing_provider(self, mock_run, tmp_path: Path, monkeypatch):
        """Doctor shows error when a provider is not installed."""
        # Mock config directories
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        # Mock subprocess to raise FileNotFoundError (CLI not found)
        mock_run.side_effect = FileNotFoundError("Command not found")

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0  # Doctor doesn't fail, just reports
        assert "Not installed" in result.stdout
        assert "✗" in result.stdout
        assert "Some providers are not installed" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    def test_doctor_shows_install_instructions(self, mock_run, tmp_path: Path, monkeypatch):
        """Doctor shows install instructions for missing providers."""
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        mock_run.side_effect = FileNotFoundError("Command not found")

        result = runner.invoke(app, ["doctor"])

        # Should show install instructions
        assert "npm install" in result.stdout or "Install:" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    @patch("focusgroup.cli.get_default_storage")
    def test_doctor_verbose_mode(self, mock_storage_fn, mock_run, tmp_path: Path, monkeypatch):
        """Doctor verbose mode shows additional info."""
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        mock_run.return_value = CompletedProcess(
            args=["test", "--version"],
            returncode=0,
            stdout="test-cli 1.0.0",
            stderr="",
        )

        mock_storage = MagicMock()
        mock_storage.list_sessions.return_value = []
        mock_storage_fn.return_value = mock_storage

        result = runner.invoke(app, ["doctor", "--verbose"])

        assert result.exit_code == 0
        assert "Auth:" in result.stdout
        assert "Storage:" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    def test_doctor_shows_agent_preset_count(self, mock_run, tmp_path: Path, monkeypatch):
        """Doctor shows count of agent presets."""
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()

        # Create some preset files
        (agents_dir / "expert.toml").write_text('[agent]\nprovider = "claude"')
        (agents_dir / "reviewer.toml").write_text('[agent]\nprovider = "codex"')

        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        mock_run.return_value = CompletedProcess(
            args=["test", "--version"],
            returncode=0,
            stdout="test-cli 1.0.0",
            stderr="",
        )

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "2 presets" in result.stdout

    @patch("focusgroup.cli.subprocess.run")
    def test_doctor_partial_provider_failure(self, mock_run, tmp_path: Path, monkeypatch):
        """Doctor handles one provider installed, one missing."""
        config_dir = tmp_path / "config"
        agents_dir = config_dir / "agents"
        config_dir.mkdir()
        agents_dir.mkdir()
        monkeypatch.setattr("focusgroup.config.get_default_config_dir", lambda: config_dir)
        monkeypatch.setattr("focusgroup.config.get_agents_dir", lambda: agents_dir)

        # First call succeeds (claude), second fails (codex)
        def run_side_effect(cmd, **kwargs):
            if cmd[0] == "claude":
                return CompletedProcess(args=cmd, returncode=0, stdout="claude 1.0.0", stderr="")
            else:
                raise FileNotFoundError("codex not found")

        mock_run.side_effect = run_side_effect

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        # Should have both success and failure indicators
        assert "✓" in result.stdout  # claude succeeded
        assert "✗" in result.stdout  # codex failed
        assert "Some providers are not installed" in result.stdout
