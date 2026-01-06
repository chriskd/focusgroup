"""Session logging infrastructure for persisting focusgroup sessions."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """A single response from an agent."""

    agent_name: str
    provider: str
    model: str | None = None
    prompt: str
    response: str
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: int | None = None  # Time to generate response
    tokens_used: int | None = None  # If available from API
    structured_data: dict | None = None  # Parsed JSON from structured feedback


class QuestionRound(BaseModel):
    """A single round of questions to the agent panel."""

    round_number: int
    question: str
    responses: list[AgentResponse] = Field(default_factory=list)
    moderator_synthesis: str | None = None  # If moderator is enabled


class SessionLog(BaseModel):
    """Complete log of a focusgroup session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str | None = None
    tool: str  # Command or tool being evaluated
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    mode: str = "single"
    agent_count: int = 0
    rounds: list[QuestionRound] = Field(default_factory=list)
    final_synthesis: str | None = None  # Overall moderator summary
    tags: list[str] = Field(default_factory=list)  # User-defined tags for organization

    @property
    def display_id(self) -> str:
        """Get a human-friendly session identifier."""
        date_str = self.created_at.strftime("%Y%m%d")
        return f"{date_str}-{self.id}"

    @property
    def is_complete(self) -> bool:
        """Check if the session has been completed."""
        return self.completed_at is not None


def _get_default_log_dir() -> Path:
    """Get the default log directory following XDG Base Directory spec.

    Uses $FOCUSGROUP_LOG_DIR if set, otherwise $XDG_DATA_HOME/focusgroup/logs,
    falling back to ~/.local/share/focusgroup/logs.

    Returns:
        Path to the log directory
    """
    import os

    # Allow override via environment variable
    if env_dir := os.environ.get("FOCUSGROUP_LOG_DIR"):
        return Path(env_dir)

    # Use XDG_DATA_HOME if set, otherwise ~/.local/share
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / "focusgroup" / "logs"

    return Path.home() / ".local" / "share" / "focusgroup" / "logs"


class SessionStorage:
    """Handles persistence of session logs to disk."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize storage with a base directory.

        Args:
            base_dir: Directory to store sessions. Defaults to XDG data directory.
        """
        if base_dir is None:
            base_dir = _get_default_log_dir()
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.base_dir / f"{session_id}.json"

    def save(self, session: SessionLog) -> Path:
        """Save a session log to disk.

        Args:
            session: The session log to save

        Returns:
            Path to the saved file
        """
        path = self._get_session_path(session.display_id)
        with open(path, "w") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2, default=str)
        return path

    def load(self, session_id: str) -> SessionLog:
        """Load a session log from disk.

        Args:
            session_id: The session ID or display ID

        Returns:
            The loaded session log

        Raises:
            FileNotFoundError: If session doesn't exist
        """
        # Try exact match first
        path = self._get_session_path(session_id)
        if not path.exists():
            # Try to find by partial ID
            matches = list(self.base_dir.glob(f"*{session_id}*.json"))
            if not matches:
                raise FileNotFoundError(f"Session not found: {session_id}")
            if len(matches) > 1:
                raise ValueError(f"Ambiguous session ID '{session_id}', matches: {matches}")
            path = matches[0]

        with open(path) as f:
            data = json.load(f)
        return SessionLog.model_validate(data)

    def list_sessions(
        self,
        limit: int = 10,
        tool_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[SessionLog]:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return
            tool_filter: Optional filter by tool name
            tag_filter: Optional filter by tag (matches if session has this tag)

        Returns:
            List of session logs, most recent first
        """
        sessions = []
        for path in sorted(self.base_dir.glob("*.json"), reverse=True):
            try:
                with open(path) as f:
                    data = json.load(f)
                session = SessionLog.model_validate(data)

                if tool_filter and tool_filter not in session.tool:
                    continue

                if tag_filter and tag_filter not in session.tags:
                    continue

                sessions.append(session)
                if len(sessions) >= limit:
                    break
            except (json.JSONDecodeError, ValueError):
                continue  # Skip malformed files

        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a session log.

        Args:
            session_id: The session ID to delete

        Returns:
            True if deleted, False if not found
        """
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False


def get_default_storage() -> SessionStorage:
    """Get the default session storage instance."""
    return SessionStorage()
