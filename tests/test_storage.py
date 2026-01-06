"""Unit tests for session storage."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from focusgroup.storage.session_log import (
    AgentResponse,
    QuestionRound,
    SessionLog,
    SessionStorage,
    get_default_storage,
)


@pytest.fixture
def storage(tmp_path: Path) -> SessionStorage:
    """Create a SessionStorage with a temporary directory."""
    return SessionStorage(base_dir=tmp_path)


@pytest.fixture
def sample_session() -> SessionLog:
    """Create a sample session for testing."""
    now = datetime.now()
    return SessionLog(
        id="test123",
        name="Test Session",
        tool="mx",
        created_at=now,
        completed_at=now + timedelta(minutes=5),
        mode="discussion",
        agent_count=2,
        rounds=[
            QuestionRound(
                round_number=0,
                question="What do you think?",
                responses=[
                    AgentResponse(
                        agent_name="Agent-1",
                        provider="claude",
                        model="claude-sonnet-4-20250514",
                        prompt="What do you think?",
                        response="I think it's good.",
                        duration_ms=1000,
                        tokens_used=50,
                    ),
                    AgentResponse(
                        agent_name="Agent-2",
                        provider="openai",
                        model="gpt-4o",
                        prompt="What do you think?",
                        response="I agree it's good.",
                        duration_ms=1200,
                        tokens_used=60,
                    ),
                ],
                moderator_synthesis="Both agents agree.",
            ),
        ],
        final_synthesis="The tool is well-received.",
    )


class TestSessionLog:
    """Test SessionLog model."""

    def test_session_log_defaults(self):
        """SessionLog has sensible defaults."""
        session = SessionLog(tool="test")
        assert session.id is not None
        assert len(session.id) == 8  # Short UUID
        assert session.created_at is not None
        assert session.completed_at is None
        assert session.mode == "single"
        assert session.rounds == []

    def test_display_id_format(self):
        """Display ID combines date and ID."""
        session = SessionLog(tool="test")
        display_id = session.display_id

        # Format: YYYYMMDD-<id>
        assert "-" in display_id
        date_part, id_part = display_id.split("-", 1)
        assert len(date_part) == 8  # YYYYMMDD
        assert date_part.isdigit()
        assert id_part == session.id

    def test_is_complete_property(self):
        """is_complete reflects completed_at state."""
        session = SessionLog(tool="test")
        assert session.is_complete is False

        session.completed_at = datetime.now()
        assert session.is_complete is True


class TestAgentResponse:
    """Test AgentResponse model."""

    def test_agent_response_defaults(self):
        """AgentResponse has sensible defaults."""
        response = AgentResponse(
            agent_name="Test",
            provider="claude",
            prompt="Question",
            response="Answer",
        )
        assert response.timestamp is not None
        assert response.model is None
        assert response.duration_ms is None
        assert response.tokens_used is None

    def test_agent_response_full(self):
        """AgentResponse with all fields."""
        now = datetime.now()
        response = AgentResponse(
            agent_name="Claude",
            provider="claude",
            model="claude-opus-4-20250514",
            prompt="Question",
            response="Answer",
            timestamp=now,
            duration_ms=500,
            tokens_used=100,
        )
        assert response.model == "claude-opus-4-20250514"
        assert response.duration_ms == 500


class TestQuestionRound:
    """Test QuestionRound model."""

    def test_question_round_defaults(self):
        """QuestionRound has sensible defaults."""
        round_ = QuestionRound(round_number=0, question="Test?")
        assert round_.responses == []
        assert round_.moderator_synthesis is None

    def test_question_round_with_responses(self):
        """QuestionRound with responses."""
        round_ = QuestionRound(
            round_number=1,
            question="Test?",
            responses=[
                AgentResponse(
                    agent_name="Agent",
                    provider="claude",
                    prompt="Test?",
                    response="Yes!",
                ),
            ],
        )
        assert len(round_.responses) == 1


class TestSessionStorage:
    """Test SessionStorage class."""

    def test_save_and_load(self, storage: SessionStorage, sample_session: SessionLog):
        """Save and load a session."""
        # Save
        path = storage.save(sample_session)
        assert path.exists()
        assert path.suffix == ".json"

        # Load
        loaded = storage.load(sample_session.display_id)
        assert loaded.id == sample_session.id
        assert loaded.name == sample_session.name
        assert loaded.tool == sample_session.tool
        assert loaded.mode == sample_session.mode
        assert loaded.agent_count == sample_session.agent_count

    def test_save_creates_valid_json(self, storage: SessionStorage, sample_session: SessionLog):
        """Saved file is valid JSON."""
        path = storage.save(sample_session)

        content = path.read_text()
        data = json.loads(content)

        assert data["id"] == sample_session.id
        assert data["tool"] == "mx"

    def test_load_by_display_id(self, storage: SessionStorage, sample_session: SessionLog):
        """Load session by display ID."""
        storage.save(sample_session)
        loaded = storage.load(sample_session.display_id)
        assert loaded.id == sample_session.id

    def test_load_by_partial_id(self, storage: SessionStorage, sample_session: SessionLog):
        """Load session by partial ID match."""
        storage.save(sample_session)

        # Partial match on the ID portion
        loaded = storage.load("test123")
        assert loaded.id == sample_session.id

    def test_load_not_found(self, storage: SessionStorage):
        """Loading non-existent session raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Session not found"):
            storage.load("nonexistent-session")

    def test_load_ambiguous_id(self, storage: SessionStorage):
        """Ambiguous partial ID raises ValueError."""
        # Create multiple sessions with similar IDs
        session1 = SessionLog(id="abc123", tool="tool1")
        session2 = SessionLog(id="abc456", tool="tool2")

        storage.save(session1)
        storage.save(session2)

        # "abc" matches both
        with pytest.raises(ValueError, match="Ambiguous session ID"):
            storage.load("abc")

    def test_list_sessions_empty(self, storage: SessionStorage):
        """List returns empty when no sessions."""
        sessions = storage.list_sessions()
        assert sessions == []

    def test_list_sessions_returns_sessions(self, storage: SessionStorage):
        """List returns saved sessions."""
        session1 = SessionLog(id="sess1", tool="tool1")
        session2 = SessionLog(id="sess2", tool="tool2")

        storage.save(session1)
        storage.save(session2)

        sessions = storage.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_limit(self, storage: SessionStorage):
        """List respects limit parameter."""
        for i in range(5):
            session = SessionLog(id=f"sess{i}", tool="tool")
            storage.save(session)

        sessions = storage.list_sessions(limit=3)
        assert len(sessions) == 3

    def test_list_sessions_tool_filter(self, storage: SessionStorage):
        """List filters by tool name."""
        session1 = SessionLog(id="sess1", tool="mx")
        session2 = SessionLog(id="sess2", tool="beads")
        session3 = SessionLog(id="sess3", tool="mx-search")

        storage.save(session1)
        storage.save(session2)
        storage.save(session3)

        sessions = storage.list_sessions(tool_filter="mx")
        assert len(sessions) == 2  # mx and mx-search

        sessions = storage.list_sessions(tool_filter="beads")
        assert len(sessions) == 1

    def test_list_sessions_tag_filter(self, storage: SessionStorage):
        """List filters by tag."""
        session1 = SessionLog(id="sess1", tool="mx", tags=["release-prep", "urgent"])
        session2 = SessionLog(id="sess2", tool="beads", tags=["release-prep"])
        session3 = SessionLog(id="sess3", tool="mx", tags=["backlog"])

        storage.save(session1)
        storage.save(session2)
        storage.save(session3)

        sessions = storage.list_sessions(tag_filter="release-prep")
        assert len(sessions) == 2

        sessions = storage.list_sessions(tag_filter="urgent")
        assert len(sessions) == 1
        assert sessions[0].id == "sess1"

        sessions = storage.list_sessions(tag_filter="nonexistent")
        assert len(sessions) == 0

    def test_list_sessions_skips_malformed(
        self, storage: SessionStorage, sample_session: SessionLog
    ):
        """List skips malformed JSON files."""
        # Save a valid session
        storage.save(sample_session)

        # Create a malformed file
        bad_file = storage.base_dir / "bad-session.json"
        bad_file.write_text("{ invalid json }")

        # Should skip the bad file
        sessions = storage.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == sample_session.id

    def test_delete_existing(self, storage: SessionStorage, sample_session: SessionLog):
        """Delete an existing session."""
        storage.save(sample_session)
        path = storage._get_session_path(sample_session.display_id)
        assert path.exists()

        result = storage.delete(sample_session.display_id)

        assert result is True
        assert not path.exists()

    def test_delete_nonexistent(self, storage: SessionStorage):
        """Delete returns False for non-existent session."""
        result = storage.delete("nonexistent")
        assert result is False

    def test_storage_creates_directory(self, tmp_path: Path):
        """Storage creates base directory if it doesn't exist."""
        new_dir = tmp_path / "new" / "storage" / "path"
        assert not new_dir.exists()

        SessionStorage(base_dir=new_dir)  # Constructor creates the directory
        assert new_dir.exists()

    def test_session_path_format(self, storage: SessionStorage, sample_session: SessionLog):
        """Session files are named by display ID."""
        path = storage._get_session_path(sample_session.display_id)
        assert path.name == f"{sample_session.display_id}.json"
        assert path.parent == storage.base_dir


class TestGetDefaultStorage:
    """Test default storage factory."""

    def test_get_default_storage_creates_storage(self):
        """get_default_storage returns a SessionStorage."""
        storage = get_default_storage()
        assert isinstance(storage, SessionStorage)
        assert storage.base_dir.is_dir()

    def test_default_storage_path(self):
        """Default storage is in ~/.focusgroup/sessions."""
        storage = get_default_storage()
        assert "focusgroup" in str(storage.base_dir)
        assert "sessions" in str(storage.base_dir)


class TestSessionRoundTrip:
    """Test complete session serialization round-trip."""

    def test_full_session_roundtrip(self, storage: SessionStorage, sample_session: SessionLog):
        """Complete session survives save/load cycle."""
        storage.save(sample_session)
        loaded = storage.load(sample_session.display_id)

        # Session metadata
        assert loaded.id == sample_session.id
        assert loaded.name == sample_session.name
        assert loaded.tool == sample_session.tool
        assert loaded.mode == sample_session.mode
        assert loaded.agent_count == sample_session.agent_count

        # Timestamps (need to compare isoformat since datetime precision may differ)
        assert loaded.created_at.isoformat() == sample_session.created_at.isoformat()
        assert loaded.completed_at is not None
        assert loaded.is_complete is True

        # Rounds
        assert len(loaded.rounds) == len(sample_session.rounds)
        original_round = sample_session.rounds[0]
        loaded_round = loaded.rounds[0]

        assert loaded_round.round_number == original_round.round_number
        assert loaded_round.question == original_round.question
        assert loaded_round.moderator_synthesis == original_round.moderator_synthesis

        # Responses
        assert len(loaded_round.responses) == len(original_round.responses)
        for orig_resp, loaded_resp in zip(
            original_round.responses, loaded_round.responses, strict=True
        ):
            assert loaded_resp.agent_name == orig_resp.agent_name
            assert loaded_resp.provider == orig_resp.provider
            assert loaded_resp.model == orig_resp.model
            assert loaded_resp.response == orig_resp.response
            assert loaded_resp.duration_ms == orig_resp.duration_ms
            assert loaded_resp.tokens_used == orig_resp.tokens_used

        # Final synthesis
        assert loaded.final_synthesis == sample_session.final_synthesis

    def test_minimal_session_roundtrip(self, storage: SessionStorage):
        """Minimal session survives save/load cycle."""
        minimal = SessionLog(tool="test")
        storage.save(minimal)

        loaded = storage.load(minimal.display_id)
        assert loaded.id == minimal.id
        assert loaded.tool == "test"
        assert loaded.rounds == []
        assert loaded.is_complete is False
