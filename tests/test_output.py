"""Unit tests for output formatters."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from focusgroup.output import (
    JsonWriter,
    MarkdownWriter,
    TextWriter,
    format_json,
    format_markdown,
    format_session,
    format_text,
    get_formatter,
)
from focusgroup.storage.session_log import AgentResponse, QuestionRound, SessionLog


@pytest.fixture
def sample_session() -> SessionLog:
    """Create a sample session for testing formatters."""
    now = datetime.now()
    return SessionLog(
        id="abc123",
        name="Test Focusgroup",
        tool="mx",
        created_at=now,
        completed_at=now + timedelta(minutes=5),
        mode="single",
        agent_count=2,
        rounds=[
            QuestionRound(
                round_number=0,
                question="How usable is this CLI?",
                responses=[
                    AgentResponse(
                        agent_name="Claude",
                        provider="claude",
                        model="claude-sonnet-4-20250514",
                        prompt="How usable is this CLI?",
                        response="The CLI has a clean interface with good help text.",
                        timestamp=now + timedelta(seconds=10),
                        duration_ms=1500,
                        tokens_used=150,
                    ),
                    AgentResponse(
                        agent_name="GPT-4",
                        provider="openai",
                        model="gpt-4o",
                        prompt="How usable is this CLI?",
                        response="Good overall structure, but could use more examples.",
                        timestamp=now + timedelta(seconds=12),
                        duration_ms=2000,
                        tokens_used=200,
                    ),
                ],
                moderator_synthesis="Both agents appreciate the clean interface.",
            ),
        ],
        final_synthesis="The tool is well-designed with room for improvement.",
    )


@pytest.fixture
def minimal_session() -> SessionLog:
    """Create a minimal session with no optional fields."""
    return SessionLog(
        tool="test-tool",
        mode="single",
        agent_count=1,
        rounds=[
            QuestionRound(
                round_number=0,
                question="Simple question?",
                responses=[
                    AgentResponse(
                        agent_name="Agent-1",
                        provider="claude",
                        prompt="Simple question?",
                        response="Simple answer.",
                    ),
                ],
            ),
        ],
    )


class TestJsonWriter:
    """Test JSON output formatter."""

    def test_format_pretty(self, sample_session: SessionLog):
        """JSON format with pretty printing."""
        writer = JsonWriter(pretty=True)
        output = writer.format(sample_session)

        # Should be valid JSON
        data = json.loads(output)
        assert data["id"] == sample_session.display_id
        assert data["tool"] == "mx"
        assert data["name"] == "Test Focusgroup"

    def test_format_compact(self, sample_session: SessionLog):
        """JSON format without pretty printing."""
        writer = JsonWriter(pretty=False)
        output = writer.format(sample_session)

        # Should be valid JSON on single line
        assert "\n" not in output
        data = json.loads(output)
        assert data["tool"] == "mx"

    def test_format_includes_metadata(self, sample_session: SessionLog):
        """JSON includes timing and token metadata by default."""
        writer = JsonWriter(include_metadata=True)
        output = writer.format(sample_session)
        data = json.loads(output)

        response = data["rounds"][0]["responses"][0]
        assert "timestamp" in response
        assert "duration_ms" in response
        assert response["duration_ms"] == 1500
        assert response["tokens_used"] == 150

    def test_format_excludes_metadata(self, sample_session: SessionLog):
        """JSON can exclude metadata."""
        writer = JsonWriter(include_metadata=False)
        output = writer.format(sample_session)
        data = json.loads(output)

        response = data["rounds"][0]["responses"][0]
        assert "timestamp" not in response
        assert "duration_ms" not in response

    def test_format_includes_summary(self, sample_session: SessionLog):
        """JSON includes summary statistics."""
        writer = JsonWriter()
        output = writer.format(sample_session)
        data = json.loads(output)

        assert "summary" in data
        summary = data["summary"]
        assert summary["total_responses"] == 2
        assert "claude" in summary["unique_providers"]
        assert "openai" in summary["unique_providers"]
        assert summary["total_tokens"] == 350  # 150 + 200
        assert summary["total_duration_ms"] == 3500  # 1500 + 2000

    def test_format_minimal_session(self, minimal_session: SessionLog):
        """JSON handles session without optional fields."""
        writer = JsonWriter()
        output = writer.format(minimal_session)
        data = json.loads(output)

        assert data["tool"] == "test-tool"
        assert "name" not in data  # Optional field not included
        assert data["is_complete"] is False

    def test_write_to_file(self, sample_session: SessionLog, tmp_path: Path):
        """Write JSON to file."""
        writer = JsonWriter()
        output_path = tmp_path / "output.json"

        result = writer.write(sample_session, output_path)

        assert result == output_path
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["tool"] == "mx"

    def test_datetime_serialization(self, sample_session: SessionLog):
        """Datetime objects serialize to ISO format."""
        writer = JsonWriter()
        output = writer.format(sample_session)
        data = json.loads(output)

        # created_at should be ISO string
        created_at = data["created_at"]
        assert isinstance(created_at, str)
        # Should be parseable
        datetime.fromisoformat(created_at)

    def test_round_structure(self, sample_session: SessionLog):
        """Rounds have expected structure."""
        writer = JsonWriter()
        output = writer.format(sample_session)
        data = json.loads(output)

        assert len(data["rounds"]) == 1
        round_data = data["rounds"][0]
        assert round_data["round_number"] == 0
        assert round_data["question"] == "How usable is this CLI?"
        assert len(round_data["responses"]) == 2
        assert "moderator_synthesis" in round_data

    def test_format_json_convenience(self, sample_session: SessionLog):
        """Convenience function works correctly."""
        output = format_json(sample_session, pretty=True)
        data = json.loads(output)
        assert data["tool"] == "mx"


class TestMarkdownWriter:
    """Test Markdown output formatter."""

    def test_format_basic(self, sample_session: SessionLog):
        """Basic Markdown formatting."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "# Test Focusgroup" in output
        assert "**Session ID:**" in output
        assert "**Tool:** `mx`" in output

    def test_format_includes_overview(self, sample_session: SessionLog):
        """Markdown includes session overview."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "## Overview" in output
        assert "**Status:** ✅ Complete" in output
        assert "**Agents:** 2" in output
        assert "**Rounds:** 1" in output

    def test_format_includes_metadata(self, sample_session: SessionLog):
        """Markdown includes timing metadata by default."""
        writer = MarkdownWriter(include_metadata=True)
        output = writer.format(sample_session)

        assert "Total Tokens:" in output
        assert "350" in output  # 150 + 200 tokens

    def test_format_excludes_metadata(self, sample_session: SessionLog):
        """Markdown can exclude metadata."""
        writer = MarkdownWriter(include_metadata=False)
        output = writer.format(sample_session)

        assert "Total Tokens:" not in output

    def test_format_round_structure(self, sample_session: SessionLog):
        """Markdown formats rounds correctly."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "## Round 1" in output
        assert "**Question:** How usable is this CLI?" in output
        assert "**Claude**" in output
        assert "**GPT-4**" in output

    def test_format_blockquote_responses(self, sample_session: SessionLog):
        """Agent responses are in blockquotes."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "> The CLI has a clean interface" in output
        assert "> Good overall structure" in output

    def test_format_moderator_synthesis(self, sample_session: SessionLog):
        """Moderator synthesis is included."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "Round Synthesis" in output
        assert "Both agents appreciate" in output

    def test_format_final_synthesis(self, sample_session: SessionLog):
        """Final synthesis section is included."""
        writer = MarkdownWriter()
        output = writer.format(sample_session)

        assert "# Final Synthesis" in output
        assert "well-designed with room for improvement" in output

    def test_custom_heading_level(self, sample_session: SessionLog):
        """Can start at different heading level."""
        writer = MarkdownWriter(heading_level=2)
        output = writer.format(sample_session)

        # Main heading should be ##
        assert "## Test Focusgroup" in output
        # Subheadings should be ###
        assert "### Overview" in output

    def test_include_timestamps(self, sample_session: SessionLog):
        """Can include response timestamps."""
        writer = MarkdownWriter(include_timestamps=True)
        output = writer.format(sample_session)

        # Should have time in HH:MM:SS format in the response metadata
        # Look for the timestamp pattern in the output
        import re

        timestamp_pattern = r"\d{2}:\d{2}:\d{2}"  # HH:MM:SS
        assert re.search(timestamp_pattern, output), f"No timestamp found in output: {output[:500]}"

    def test_write_to_file(self, sample_session: SessionLog, tmp_path: Path):
        """Write Markdown to file."""
        writer = MarkdownWriter()
        output_path = tmp_path / "output.md"

        result = writer.write(sample_session, output_path)

        assert result == output_path
        assert output_path.exists()
        content = output_path.read_text()
        assert "# Test Focusgroup" in content

    def test_format_minimal_session(self, minimal_session: SessionLog):
        """Markdown handles minimal session."""
        writer = MarkdownWriter()
        output = writer.format(minimal_session)

        assert "test-tool" in output
        assert "🔄 In Progress" in output  # Not complete

    def test_multiline_response(self):
        """Multiline responses format correctly."""
        session = SessionLog(
            tool="test",
            mode="single",
            agent_count=1,
            rounds=[
                QuestionRound(
                    round_number=0,
                    question="Test?",
                    responses=[
                        AgentResponse(
                            agent_name="Agent",
                            provider="claude",
                            prompt="Test?",
                            response="Line 1\nLine 2\nLine 3",
                        ),
                    ],
                ),
            ],
        )

        writer = MarkdownWriter()
        output = writer.format(session)

        # Each line should be blockquoted
        assert "> Line 1" in output
        assert "> Line 2" in output
        assert "> Line 3" in output

    def test_format_markdown_convenience(self, sample_session: SessionLog):
        """Convenience function works correctly."""
        output = format_markdown(sample_session)
        assert "# Test Focusgroup" in output


class TestTextWriter:
    """Test plain text output formatter."""

    def test_format_basic(self, sample_session: SessionLog):
        """Basic text formatting."""
        writer = TextWriter()
        output = writer.format(sample_session)

        # Title shows the session name when available
        assert "Test Focusgroup" in output
        assert "Session: " in output
        # Tool name may not be shown in title when session has a name,
        # but session ID should be present
        assert sample_session.display_id in output

    def test_format_separator_lines(self, sample_session: SessionLog):
        """Text has separator lines."""
        writer = TextWriter(width=80)
        output = writer.format(sample_session)

        # Should have '=' separators
        assert "=" * 80 in output
        # Should have '-' separators
        assert "-" * 80 in output

    def test_format_round_structure(self, sample_session: SessionLog):
        """Text formats rounds correctly."""
        writer = TextWriter()
        output = writer.format(sample_session)

        assert "ROUND 1:" in output
        assert "[Claude]" in output
        assert "[GPT-4]" in output

    def test_format_status(self, sample_session: SessionLog):
        """Status is shown."""
        writer = TextWriter()
        output = writer.format(sample_session)

        assert "Status: Complete" in output

    def test_format_mode(self, sample_session: SessionLog):
        """Mode is shown."""
        writer = TextWriter()
        output = writer.format(sample_session)

        assert "Mode: single" in output

    def test_format_moderator_synthesis(self, sample_session: SessionLog):
        """Moderator synthesis is shown."""
        writer = TextWriter()
        output = writer.format(sample_session)

        assert "[Moderator Synthesis]" in output
        assert "Both agents appreciate" in output

    def test_format_final_synthesis(self, sample_session: SessionLog):
        """Final synthesis section is shown."""
        writer = TextWriter()
        output = writer.format(sample_session)

        assert "FINAL SYNTHESIS" in output
        assert "well-designed with room for improvement" in output

    def test_custom_width(self, sample_session: SessionLog):
        """Can use custom width for separators."""
        writer = TextWriter(width=60)
        output = writer.format(sample_session)

        assert "=" * 60 in output

    def test_write_to_file(self, sample_session: SessionLog, tmp_path: Path):
        """Write text to file."""
        writer = TextWriter()
        output_path = tmp_path / "output.txt"

        result = writer.write(sample_session, output_path)

        assert result == output_path
        assert output_path.exists()

    def test_format_minimal_session(self, minimal_session: SessionLog):
        """Text handles minimal session."""
        writer = TextWriter()
        output = writer.format(minimal_session)

        assert "test-tool" in output
        assert "Status: In Progress" in output

    def test_format_text_convenience(self, sample_session: SessionLog):
        """Convenience function works correctly."""
        output = format_text(sample_session)
        assert "Test Focusgroup" in output


class TestJsonRoundTrip:
    """Test JSON serialization round-trip."""

    def test_json_roundtrip(self, sample_session: SessionLog):
        """Session survives JSON serialization and deserialization."""
        writer = JsonWriter()
        json_output = writer.format(sample_session)

        # Parse back
        data = json.loads(json_output)

        # Key fields preserved
        assert data["tool"] == sample_session.tool
        assert data["mode"] == sample_session.mode
        assert data["agent_count"] == sample_session.agent_count
        assert len(data["rounds"]) == len(sample_session.rounds)

        # Response content preserved
        original_response = sample_session.rounds[0].responses[0].response
        parsed_response = data["rounds"][0]["responses"][0]["response"]
        assert parsed_response == original_response

    def test_json_idempotent(self, sample_session: SessionLog):
        """Formatting same session twice gives identical output."""
        writer = JsonWriter(pretty=True)

        output1 = writer.format(sample_session)
        output2 = writer.format(sample_session)

        # Parse and compare (timestamps might differ in format)
        data1 = json.loads(output1)
        data2 = json.loads(output2)
        assert data1 == data2


class TestGetFormatter:
    """Test get_formatter factory function."""

    def test_get_json_formatter(self):
        """Get JSON formatter."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JsonWriter)

    def test_get_markdown_formatter(self):
        """Get Markdown formatter."""
        formatter = get_formatter("markdown")
        assert isinstance(formatter, MarkdownWriter)

    def test_get_md_alias(self):
        """Get Markdown formatter via 'md' alias."""
        formatter = get_formatter("md")
        assert isinstance(formatter, MarkdownWriter)

    def test_get_text_formatter(self):
        """Get Text formatter."""
        formatter = get_formatter("text")
        assert isinstance(formatter, TextWriter)

    def test_get_txt_alias(self):
        """Get Text formatter via 'txt' alias."""
        formatter = get_formatter("txt")
        assert isinstance(formatter, TextWriter)

    def test_case_insensitive(self):
        """Format type is case insensitive."""
        assert isinstance(get_formatter("JSON"), JsonWriter)
        assert isinstance(get_formatter("MARKDOWN"), MarkdownWriter)
        assert isinstance(get_formatter("Text"), TextWriter)

    def test_invalid_format_raises(self):
        """Invalid format type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format type"):
            get_formatter("invalid")

    def test_invalid_format_shows_valid_options(self):
        """Error message shows valid options."""
        with pytest.raises(ValueError, match="json"):
            get_formatter("invalid")


class TestFormatSession:
    """Test format_session convenience function."""

    def test_format_session_text(self, sample_session: SessionLog):
        """format_session with text format."""
        output = format_session(sample_session, "text")
        assert "Test Focusgroup" in output
        # Text format uses === separators
        assert "=" * 80 in output

    def test_format_session_json(self, sample_session: SessionLog):
        """format_session with JSON format."""
        output = format_session(sample_session, "json")
        data = json.loads(output)
        assert data["tool"] == "mx"

    def test_format_session_markdown(self, sample_session: SessionLog):
        """format_session with Markdown format."""
        output = format_session(sample_session, "markdown")
        assert "# Test Focusgroup" in output

    def test_format_session_default_text(self, sample_session: SessionLog):
        """format_session defaults to text format."""
        output = format_session(sample_session)
        # Text format uses === separators
        assert "=" * 80 in output


class TestOutputFormatterProtocol:
    """Test that formatters satisfy the OutputFormatter protocol."""

    def test_json_writer_has_format_method(self):
        """JsonWriter has format method required by protocol."""
        writer = JsonWriter()
        assert hasattr(writer, "format")
        assert callable(writer.format)

    def test_markdown_writer_has_write_method(self):
        """MarkdownWriter has write method required by protocol."""
        writer = MarkdownWriter()
        assert hasattr(writer, "write")
        assert callable(writer.write)

    def test_text_writer_has_both_methods(self):
        """TextWriter has both required protocol methods."""
        writer = TextWriter()
        assert hasattr(writer, "format")
        assert hasattr(writer, "write")
        assert callable(writer.format)
        assert callable(writer.write)
