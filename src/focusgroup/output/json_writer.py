"""JSON output writer for session results."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from focusgroup.storage.session_log import SessionLog


class JsonWriter:
    """Formats session logs as JSON output.

    This writer produces machine-readable JSON output suitable for:
    - Piping to other tools (jq, etc.)
    - Programmatic consumption
    - Data archival and analysis
    """

    def __init__(self, pretty: bool = True, include_metadata: bool = True) -> None:
        """Initialize the JSON writer.

        Args:
            pretty: Whether to indent output for readability
            include_metadata: Whether to include timing/token metadata
        """
        self._pretty = pretty
        self._include_metadata = include_metadata

    def format(self, session: SessionLog) -> str:
        """Format a session log as JSON string.

        Args:
            session: The session log to format

        Returns:
            JSON string representation
        """
        data = self._session_to_dict(session)
        if self._pretty:
            return json.dumps(data, indent=2, default=self._json_encoder)
        return json.dumps(data, default=self._json_encoder)

    def write(self, session: SessionLog, path: Path) -> Path:
        """Write a session log to a JSON file.

        Args:
            session: The session log to write
            path: Output file path

        Returns:
            Path to the written file
        """
        content = self.format(session)
        path.write_text(content)
        return path

    def _session_to_dict(self, session: SessionLog) -> dict[str, Any]:
        """Convert session to dictionary for JSON serialization.

        Args:
            session: The session log to convert

        Returns:
            Dictionary representation
        """
        data: dict[str, Any] = {
            "id": session.display_id,
            "tool": session.tool,
            "mode": session.mode,
            "created_at": session.created_at,
            "completed_at": session.completed_at,
            "is_complete": session.is_complete,
        }

        if session.name:
            data["name"] = session.name

        data["agent_count"] = session.agent_count
        data["round_count"] = len(session.rounds)

        # Convert rounds
        data["rounds"] = []
        for round_ in session.rounds:
            round_data: dict[str, Any] = {
                "round_number": round_.round_number,
                "question": round_.question,
                "responses": [],
            }

            for resp in round_.responses:
                resp_data: dict[str, Any] = {
                    "agent_name": resp.agent_name,
                    "provider": resp.provider,
                    "response": resp.response,
                }

                if self._include_metadata:
                    resp_data["timestamp"] = resp.timestamp
                    if resp.model:
                        resp_data["model"] = resp.model
                    if resp.duration_ms:
                        resp_data["duration_ms"] = resp.duration_ms
                    if resp.tokens_used:
                        resp_data["tokens_used"] = resp.tokens_used

                # Include structured data if present
                if resp.structured_data:
                    resp_data["structured_data"] = resp.structured_data

                round_data["responses"].append(resp_data)

            if round_.moderator_synthesis:
                round_data["moderator_synthesis"] = round_.moderator_synthesis

            data["rounds"].append(round_data)

        if session.final_synthesis:
            data["final_synthesis"] = session.final_synthesis

        # Add summary statistics
        data["summary"] = self._compute_summary(session)

        return data

    def _compute_summary(self, session: SessionLog) -> dict[str, Any]:
        """Compute summary statistics for the session.

        Args:
            session: The session to summarize

        Returns:
            Summary statistics dictionary
        """
        total_responses = sum(len(r.responses) for r in session.rounds)
        total_tokens = 0
        total_duration_ms = 0

        providers: set[str] = set()
        for round_ in session.rounds:
            for resp in round_.responses:
                providers.add(resp.provider)
                if resp.tokens_used:
                    total_tokens += resp.tokens_used
                if resp.duration_ms:
                    total_duration_ms += resp.duration_ms

        summary: dict[str, Any] = {
            "total_responses": total_responses,
            "unique_providers": list(providers),
        }

        if total_tokens > 0:
            summary["total_tokens"] = total_tokens
        if total_duration_ms > 0:
            summary["total_duration_ms"] = total_duration_ms
            # Calculate session duration if complete
            if session.completed_at and session.created_at:
                wall_time = session.completed_at - session.created_at
                summary["wall_time_seconds"] = wall_time.total_seconds()

        return summary

    def _json_encoder(self, obj: Any) -> Any:
        """Custom JSON encoder for non-serializable types.

        Args:
            obj: Object to encode

        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def format_json(session: SessionLog, pretty: bool = True) -> str:
    """Convenience function to format a session as JSON.

    Args:
        session: The session log to format
        pretty: Whether to indent output

    Returns:
        JSON string representation
    """
    writer = JsonWriter(pretty=pretty)
    return writer.format(session)
