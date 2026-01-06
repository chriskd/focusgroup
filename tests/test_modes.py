"""Tests for session modes and orchestrator."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
)
from focusgroup.modes.base import (
    ConversationHistory,
    ConversationTurn,
    RoundResult,
    SessionModeError,
)
from focusgroup.modes.orchestrator import SessionOrchestrator, parse_structured_response
from focusgroup.storage.session_log import SessionLog, SessionStorage
from focusgroup.tools.base import Tool, ToolHelp

from .conftest import create_mock_agent


class TestRoundResult:
    """Test RoundResult dataclass."""

    def test_round_result_defaults(self):
        """RoundResult has sensible defaults."""
        result = RoundResult(round_number=0, prompt="Test?")
        assert result.round_number == 0
        assert result.prompt == "Test?"
        assert result.responses == []
        assert result.started_at is not None
        assert result.completed_at is None
        assert result.context is None

    def test_duration_ms_incomplete(self):
        """Duration is None when not completed."""
        result = RoundResult(round_number=0, prompt="Test?")
        assert result.duration_ms is None

    def test_duration_ms_completed(self):
        """Duration is calculated when completed."""
        now = datetime.now()
        result = RoundResult(
            round_number=0,
            prompt="Test?",
            started_at=now,
        )
        result.completed_at = now + timedelta(seconds=1.5)
        assert result.duration_ms == pytest.approx(1500, rel=0.1)

    def test_mark_complete(self):
        """mark_complete sets completed_at."""
        result = RoundResult(round_number=0, prompt="Test?")
        assert result.completed_at is None
        result.mark_complete()
        assert result.completed_at is not None


class TestConversationTurn:
    """Test ConversationTurn dataclass."""

    def test_conversation_turn_defaults(self):
        """ConversationTurn has sensible defaults."""
        turn = ConversationTurn(
            agent_name="Claude",
            content="Hello!",
        )
        assert turn.agent_name == "Claude"
        assert turn.content == "Hello!"
        assert turn.turn_type == "response"
        assert turn.timestamp is not None

    def test_conversation_turn_custom_type(self):
        """ConversationTurn can have custom type."""
        turn = ConversationTurn(
            agent_name="Moderator",
            content="Summary...",
            turn_type="synthesis",
        )
        assert turn.turn_type == "synthesis"


class TestConversationHistory:
    """Test ConversationHistory dataclass."""

    def test_empty_history(self):
        """Empty history has no turns."""
        history = ConversationHistory()
        assert history.turns == []

    def test_add_turn(self):
        """add_turn creates and appends turn."""
        history = ConversationHistory()
        turn = history.add_turn("Claude", "Hello!", "response")

        assert len(history.turns) == 1
        assert history.turns[0] == turn
        assert turn.agent_name == "Claude"
        assert turn.content == "Hello!"

    def test_add_multiple_turns(self):
        """Multiple turns are tracked in order."""
        history = ConversationHistory()
        history.add_turn("Claude", "First response")
        history.add_turn("GPT", "Second response")
        history.add_turn("Claude", "Third response", "reply")

        assert len(history.turns) == 3
        assert history.turns[0].agent_name == "Claude"
        assert history.turns[1].agent_name == "GPT"
        assert history.turns[2].turn_type == "reply"

    def test_to_context_string_empty(self):
        """Empty history produces empty context."""
        history = ConversationHistory()
        assert history.to_context_string() == ""

    def test_to_context_string(self):
        """History formats as context string."""
        history = ConversationHistory()
        history.add_turn("Claude", "I think it's good.")
        history.add_turn("GPT", "I agree.")

        context = history.to_context_string()
        assert "Previous Responses" in context
        assert "Claude" in context
        assert "I think it's good." in context
        assert "GPT" in context
        assert "I agree." in context

    def test_to_context_string_exclude_agent(self):
        """Can exclude specific agent from context."""
        history = ConversationHistory()
        history.add_turn("Claude", "Claude's response")
        history.add_turn("GPT", "GPT's response")

        context = history.to_context_string(exclude_agent="Claude")
        assert "Claude" not in context
        assert "GPT" in context
        assert "GPT's response" in context


class TestSessionModeError:
    """Test SessionModeError exception."""

    def test_session_mode_error(self):
        """SessionModeError stores mode name."""
        error = SessionModeError("Something went wrong", mode_name="single")
        assert str(error) == "Something went wrong"
        assert error.mode_name == "single"

    def test_session_mode_error_no_mode(self):
        """SessionModeError without mode name."""
        error = SessionModeError("Error message")
        assert error.mode_name is None


class TestSessionOrchestrator:
    """Test SessionOrchestrator with mocked dependencies."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock Tool."""
        tool = MagicMock(spec=Tool)
        tool.name = "test-tool"
        tool.command = "test-tool"

        # Mock get_help to return async result
        async def mock_get_help():
            return ToolHelp(
                tool_name="test-tool",
                description="A test tool",
                usage="test-tool [options]",
                raw_output="Test tool help output",
            )

        tool.get_help = mock_get_help
        return tool

    @pytest.fixture
    def mock_storage(self, tmp_path):
        """Create a mock SessionStorage."""
        return SessionStorage(base_dir=tmp_path)

    @pytest.fixture
    def basic_config(self):
        """Create a basic FocusgroupConfig."""
        return FocusgroupConfig(
            session=SessionConfig(name="Test Session", mode=SessionMode.SINGLE),
            tool=ToolConfig(command="test-tool"),
            agents=[
                AgentConfig(provider=AgentProvider.CLAUDE, name="Agent1"),
                AgentConfig(provider=AgentProvider.CLAUDE, name="Agent2"),
            ],
            questions=QuestionsConfig(rounds=["Question 1?", "Question 2?"]),
            output=OutputConfig(format="text"),
        )

    def test_orchestrator_init(self, basic_config, mock_tool, mock_storage):
        """Orchestrator initializes with config."""
        orchestrator = SessionOrchestrator(
            config=basic_config,
            tool=mock_tool,
            storage=mock_storage,
        )

        assert orchestrator.session.tool == "test-tool"
        assert orchestrator.session.mode == "single"
        assert orchestrator.session.agent_count == 2

    def test_orchestrator_session_property(self, basic_config, mock_tool, mock_storage):
        """Orchestrator exposes session property."""
        orchestrator = SessionOrchestrator(
            config=basic_config,
            tool=mock_tool,
            storage=mock_storage,
        )

        session = orchestrator.session
        assert isinstance(session, SessionLog)
        assert session.name == "Test Session"

    @pytest.mark.asyncio
    async def test_run_session_without_setup_raises(self, basic_config, mock_tool, mock_storage):
        """Running session without setup raises error."""
        orchestrator = SessionOrchestrator(
            config=basic_config,
            tool=mock_tool,
            storage=mock_storage,
        )

        with pytest.raises(SessionModeError, match="not set up"):
            async for _ in orchestrator.run_session():
                pass

    @pytest.mark.asyncio
    async def test_setup_creates_agents(self, basic_config, mock_tool, mock_storage):
        """Setup creates agents from config."""
        # Mock agent creation to avoid API key requirements
        mock_agents = [
            create_mock_agent(name="Agent1"),
            create_mock_agent(name="Agent2"),
        ]
        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=basic_config,
                tool=mock_tool,
                storage=mock_storage,
            )

            await orchestrator.setup()

            assert len(orchestrator.agents) == 2
            assert orchestrator.agents[0].name == "Agent1"
            assert orchestrator.agents[1].name == "Agent2"

    @pytest.mark.asyncio
    async def test_setup_fetches_tool_help(self, basic_config, mock_tool, mock_storage):
        """Setup fetches tool help."""
        mock_agents = [create_mock_agent(name="Agent1")]
        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=basic_config,
                tool=mock_tool,
                storage=mock_storage,
            )

            await orchestrator.setup()
            # Tool.get_help should have been called - no exception means success

    @pytest.mark.asyncio
    async def test_setup_tool_help_failure(self, basic_config, mock_storage):
        """Setup raises error if tool help fails."""
        mock_tool = MagicMock(spec=Tool)
        mock_tool.command = "failing-tool"

        async def failing_get_help():
            raise RuntimeError("Tool not found")

        mock_tool.get_help = failing_get_help

        mock_agents = [create_mock_agent(name="Agent1")]
        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=basic_config,
                tool=mock_tool,
                storage=mock_storage,
            )

            with pytest.raises(SessionModeError, match="Failed to get tool help"):
                await orchestrator.setup()

    def test_save_returns_path(self, basic_config, mock_tool, mock_storage):
        """Save returns path string."""
        orchestrator = SessionOrchestrator(
            config=basic_config,
            tool=mock_tool,
            storage=mock_storage,
        )

        path = orchestrator.save()

        assert isinstance(path, str)
        assert Path(path).exists()


class TestModeCreation:
    """Test mode creation based on config."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock Tool."""
        tool = MagicMock(spec=Tool)
        tool.name = "test-tool"
        tool.command = "test-tool"

        async def mock_get_help():
            return ToolHelp(
                tool_name="test-tool",
                description="A test tool",
                usage="test-tool [options]",
                raw_output="Test tool help output",
            )

        tool.get_help = mock_get_help
        return tool

    def _create_config(self, mode: SessionMode):
        """Helper to create config with specified mode."""
        return FocusgroupConfig(
            session=SessionConfig(mode=mode),
            tool=ToolConfig(command="test-tool"),
            agents=[AgentConfig(provider=AgentProvider.CLAUDE)],
            questions=QuestionsConfig(rounds=["Test?"]),
        )

    @pytest.mark.asyncio
    async def test_creates_single_mode(self, mock_tool, tmp_path):
        """Config with SINGLE creates SingleMode."""
        config = self._create_config(SessionMode.SINGLE)
        mock_agents = [create_mock_agent(name="Agent1")]

        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=config,
                tool=mock_tool,
                storage=SessionStorage(base_dir=tmp_path),
            )
            await orchestrator.setup()

            from focusgroup.modes.single import SingleMode

            assert isinstance(orchestrator._mode, SingleMode)

    @pytest.mark.asyncio
    async def test_creates_discussion_mode(self, mock_tool, tmp_path):
        """Config with DISCUSSION creates DiscussionMode."""
        config = self._create_config(SessionMode.DISCUSSION)
        mock_agents = [create_mock_agent(name="Agent1")]

        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=config,
                tool=mock_tool,
                storage=SessionStorage(base_dir=tmp_path),
            )
            await orchestrator.setup()

            from focusgroup.modes.discussion import DiscussionMode

            assert isinstance(orchestrator._mode, DiscussionMode)

    @pytest.mark.asyncio
    async def test_creates_structured_mode(self, mock_tool, tmp_path):
        """Config with STRUCTURED creates StructuredMode."""
        config = self._create_config(SessionMode.STRUCTURED)
        mock_agents = [create_mock_agent(name="Agent1")]

        with patch("focusgroup.modes.orchestrator.create_agents", return_value=mock_agents):
            orchestrator = SessionOrchestrator(
                config=config,
                tool=mock_tool,
                storage=SessionStorage(base_dir=tmp_path),
            )
            await orchestrator.setup()

            from focusgroup.modes.structured import StructuredMode

            assert isinstance(orchestrator._mode, StructuredMode)


class TestNeedsHistory:
    """Test _needs_history method for various configurations."""

    @pytest.fixture
    def mock_tool(self):
        """Create a mock Tool for testing."""
        tool = MagicMock(spec=Tool)
        tool.command = "test-tool"
        tool.name = "test-tool"

        async def mock_get_help():
            return ToolHelp(
                tool_name="test-tool",
                description="A test tool",
                usage="test-tool [options]",
                raw_output="Test tool help output",
            )

        tool.get_help = mock_get_help
        return tool

    def _create_config(self, mode: SessionMode, moderator: bool = False):
        """Create a test config with specified mode and moderator setting."""
        return FocusgroupConfig(
            session=SessionConfig(name="Test", mode=mode, moderator=moderator),
            tool=ToolConfig(command="test"),
            agents=[AgentConfig(provider=AgentProvider.CLAUDE)],
            questions=QuestionsConfig(rounds=["Q?"]),
            output=OutputConfig(format="text", save_log=False),
        )

    def test_single_mode_no_moderator(self, mock_tool, tmp_path):
        """Single mode without moderator doesn't need history."""
        config = self._create_config(SessionMode.SINGLE, moderator=False)
        orchestrator = SessionOrchestrator(
            config=config,
            tool=mock_tool,
            storage=SessionStorage(base_dir=tmp_path),
        )
        assert orchestrator._needs_history() is False

    def test_single_mode_with_moderator(self, mock_tool, tmp_path):
        """Single mode with moderator needs history for synthesis."""
        config = self._create_config(SessionMode.SINGLE, moderator=True)
        orchestrator = SessionOrchestrator(
            config=config,
            tool=mock_tool,
            storage=SessionStorage(base_dir=tmp_path),
        )
        assert orchestrator._needs_history() is True

    def test_discussion_mode_always_needs_history(self, mock_tool, tmp_path):
        """Discussion mode always needs history."""
        config = self._create_config(SessionMode.DISCUSSION, moderator=False)
        orchestrator = SessionOrchestrator(
            config=config,
            tool=mock_tool,
            storage=SessionStorage(base_dir=tmp_path),
        )
        assert orchestrator._needs_history() is True

    def test_structured_mode_always_needs_history(self, mock_tool, tmp_path):
        """Structured mode always needs history."""
        config = self._create_config(SessionMode.STRUCTURED, moderator=False)
        orchestrator = SessionOrchestrator(
            config=config,
            tool=mock_tool,
            storage=SessionStorage(base_dir=tmp_path),
        )
        assert orchestrator._needs_history() is True


class TestParseStructuredResponse:
    """Test parse_structured_response function."""

    @pytest.fixture
    def rating_schema(self):
        """Create a simple rating schema."""
        return FeedbackSchema(
            fields=[
                SchemaField(name="rating", type=SchemaFieldType.INTEGER),
                SchemaField(name="reasoning", type=SchemaFieldType.STRING),
            ]
        )

    def test_returns_original_without_schema(self):
        """Without schema, returns original content and None."""
        content = "This is just text"
        text, data = parse_structured_response(content, None)
        assert text == content
        assert data is None

    def test_parses_pure_json_response(self, rating_schema):
        """Parse pure JSON response."""
        content = '{"rating": 4, "reasoning": "Good tool"}'
        text, data = parse_structured_response(content, rating_schema)
        assert text == content
        assert data is not None
        assert data["rating"] == 4
        assert data["reasoning"] == "Good tool"

    def test_parses_json_with_whitespace(self, rating_schema):
        """Parse JSON with surrounding whitespace."""
        content = """
        {
            "rating": 5,
            "reasoning": "Excellent"
        }
        """
        text, data = parse_structured_response(content, rating_schema)
        assert data is not None
        assert data["rating"] == 5

    def test_parses_json_in_markdown_code_block(self, rating_schema):
        """Parse JSON from markdown code block."""
        content = """Here is my assessment:

```json
{"rating": 3, "reasoning": "Average"}
```

Hope this helps!"""
        text, data = parse_structured_response(content, rating_schema)
        assert text == content
        assert data is not None
        assert data["rating"] == 3
        assert data["reasoning"] == "Average"

    def test_parses_json_in_code_block_without_language(self, rating_schema):
        """Parse JSON from code block without language specifier."""
        content = """Assessment:

```
{"rating": 2, "reasoning": "Needs work"}
```"""
        text, data = parse_structured_response(content, rating_schema)
        assert data is not None
        assert data["rating"] == 2

    def test_parses_json_embedded_in_text(self, rating_schema):
        """Parse JSON embedded in regular text."""
        content = 'After analysis, I give this {"rating": 4, "reasoning": "Solid"} score.'
        text, data = parse_structured_response(content, rating_schema)
        assert data is not None
        assert data["rating"] == 4

    def test_returns_none_for_invalid_json(self, rating_schema):
        """Invalid JSON returns None for structured_data."""
        content = "This has no valid JSON {broken: json}"
        text, data = parse_structured_response(content, rating_schema)
        assert text == content
        assert data is None

    def test_returns_none_for_text_only(self, rating_schema):
        """Plain text returns None for structured_data."""
        content = "This is just a normal text response without any JSON."
        text, data = parse_structured_response(content, rating_schema)
        assert text == content
        assert data is None

    def test_parses_complex_nested_json(self):
        """Parse complex JSON with arrays."""
        schema = FeedbackSchema(
            fields=[
                SchemaField(name="pros", type=SchemaFieldType.LIST),
                SchemaField(name="cons", type=SchemaFieldType.LIST),
            ]
        )
        content = """```json
{
    "pros": ["Fast", "Easy to use"],
    "cons": ["Limited features"]
}
```"""
        text, data = parse_structured_response(content, schema)
        assert data is not None
        assert data["pros"] == ["Fast", "Easy to use"]
        assert data["cons"] == ["Limited features"]

    def test_handles_multiple_json_blocks(self, rating_schema):
        """Uses first valid JSON object found."""
        content = """First block:
```json
{"rating": 4, "reasoning": "First"}
```
Second block:
```json
{"rating": 2, "reasoning": "Second"}
```"""
        text, data = parse_structured_response(content, rating_schema)
        assert data is not None
        assert data["rating"] == 4  # First one wins
