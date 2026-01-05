"""Integration tests for CLI commands."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from focusgroup.cli import app
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
            ["ask", "mx", "What's good?", "--context", "echo test", "--provider", "invalid"],
        )
        assert result.exit_code == 1
        assert "Unknown provider" in result.stdout

    @patch("focusgroup.cli.asyncio.run")
    def test_ask_invokes_async(self, mock_run):
        """Ask command invokes async implementation."""
        mock_run.return_value = None
        runner.invoke(app, ["ask", "mx", "What's good?", "--context", "echo test"])

        # Should have called asyncio.run with the async implementation
        mock_run.assert_called_once()

    def test_ask_requires_context(self):
        """Ask command requires --context option."""
        result = runner.invoke(app, ["ask", "mx", "What's good?"])
        assert result.exit_code == 2
        # Typer puts required option error in output (stdout or stderr combined)
        assert "--context" in result.output


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
