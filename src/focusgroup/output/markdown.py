"""Markdown output writer for session reports."""

from pathlib import Path
from textwrap import dedent

from focusgroup.storage.session_log import AgentResponse, QuestionRound, SessionLog


class MarkdownWriter:
    """Formats session logs as Markdown reports.

    This writer produces human-readable Markdown output suitable for:
    - Documentation
    - Sharing with stakeholders
    - Archival as readable documents
    """

    def __init__(
        self,
        include_metadata: bool = True,
        include_timestamps: bool = False,
        heading_level: int = 1,
    ) -> None:
        """Initialize the Markdown writer.

        Args:
            include_metadata: Whether to include timing/token metadata
            include_timestamps: Whether to include response timestamps
            heading_level: Starting heading level (1 = h1, 2 = h2, etc.)
        """
        self._include_metadata = include_metadata
        self._include_timestamps = include_timestamps
        self._heading_level = heading_level

    def format(self, session: SessionLog) -> str:
        """Format a session log as Markdown string.

        Args:
            session: The session log to format

        Returns:
            Markdown string representation
        """
        parts: list[str] = []

        # Title and header
        parts.append(self._format_header(session))

        # Session overview
        parts.append(self._format_overview(session))

        # Each round
        for round_ in session.rounds:
            parts.append(self._format_round(round_))

        # Final synthesis
        if session.final_synthesis:
            parts.append(self._format_synthesis(session.final_synthesis))

        return "\n".join(parts)

    def write(self, session: SessionLog, path: Path) -> Path:
        """Write a session log to a Markdown file.

        Args:
            session: The session log to write
            path: Output file path

        Returns:
            Path to the written file
        """
        content = self.format(session)
        path.write_text(content)
        return path

    def _h(self, level: int) -> str:
        """Get heading prefix for a given level.

        Args:
            level: Relative heading level (0 = main, 1 = sub, etc.)

        Returns:
            Markdown heading prefix (e.g., "##")
        """
        actual_level = min(self._heading_level + level, 6)
        return "#" * actual_level

    def _format_header(self, session: SessionLog) -> str:
        """Format the report header.

        Args:
            session: The session to format header for

        Returns:
            Markdown header section
        """
        title = session.name or f"Focusgroup Session: {session.tool}"
        date_str = session.created_at.strftime("%Y-%m-%d %H:%M")

        return dedent(f"""\
            {self._h(0)} {title}

            **Session ID:** `{session.display_id}`
            **Tool:** `{session.tool}`
            **Date:** {date_str}
            **Mode:** {session.mode}
        """)

    def _format_overview(self, session: SessionLog) -> str:
        """Format the session overview section.

        Args:
            session: The session to summarize

        Returns:
            Markdown overview section
        """
        status = "✅ Complete" if session.is_complete else "🔄 In Progress"

        lines = [
            f"{self._h(1)} Overview",
            "",
            f"- **Status:** {status}",
            f"- **Agents:** {session.agent_count}",
            f"- **Rounds:** {len(session.rounds)}",
        ]

        if self._include_metadata:
            # Compute total tokens and duration
            total_tokens = 0
            total_duration = 0
            for round_ in session.rounds:
                for resp in round_.responses:
                    if resp.tokens_used:
                        total_tokens += resp.tokens_used
                    if resp.duration_ms:
                        total_duration += resp.duration_ms

            if total_tokens > 0:
                lines.append(f"- **Total Tokens:** {total_tokens:,}")
            if total_duration > 0:
                lines.append(f"- **Total Response Time:** {total_duration / 1000:.1f}s")

            if session.completed_at:
                duration = session.completed_at - session.created_at
                lines.append(f"- **Session Duration:** {duration.total_seconds():.1f}s")

        lines.append("")  # Trailing newline
        return "\n".join(lines)

    def _format_round(self, round_: QuestionRound) -> str:
        """Format a single question round.

        Args:
            round_: The round to format

        Returns:
            Markdown round section
        """
        parts: list[str] = []

        # Round heading
        parts.append(f"{self._h(1)} Round {round_.round_number + 1}")
        parts.append("")
        parts.append(f"**Question:** {round_.question}")
        parts.append("")

        # Each agent's response
        for resp in round_.responses:
            parts.append(self._format_response(resp))
            parts.append("")

        # Moderator synthesis for this round
        if round_.moderator_synthesis:
            parts.append(f"{self._h(2)} Round Synthesis")
            parts.append("")
            parts.append(round_.moderator_synthesis)
            parts.append("")

        return "\n".join(parts)

    def _format_response(self, response: AgentResponse) -> str:
        """Format a single agent response.

        Args:
            response: The response to format

        Returns:
            Markdown response block
        """
        lines: list[str] = []

        # Agent header with metadata
        header_parts = [f"**{response.agent_name}**"]
        if response.model:
            header_parts.append(f"({response.model})")

        metadata_parts: list[str] = []
        if self._include_metadata:
            if response.duration_ms:
                metadata_parts.append(f"{response.duration_ms}ms")
            if response.tokens_used:
                metadata_parts.append(f"{response.tokens_used} tokens")
        if self._include_timestamps:
            metadata_parts.append(response.timestamp.strftime("%H:%M:%S"))

        if metadata_parts:
            header_parts.append(f"*[{', '.join(metadata_parts)}]*")

        lines.append(" ".join(header_parts))
        lines.append("")

        # Response content in blockquote
        for line in response.response.strip().split("\n"):
            lines.append(f"> {line}")

        return "\n".join(lines)

    def _format_synthesis(self, synthesis: str) -> str:
        """Format the final moderator synthesis.

        Args:
            synthesis: The synthesis text

        Returns:
            Markdown synthesis section
        """
        return dedent(f"""\
            {self._h(0)} Final Synthesis

            {synthesis}
        """)


class TextWriter:
    """Formats session logs as plain text for terminal output.

    This writer produces compact text output suitable for:
    - Terminal display
    - Quick review
    - Piping to simpler tools
    """

    def __init__(self, width: int = 80) -> None:
        """Initialize the text writer.

        Args:
            width: Maximum line width for wrapping
        """
        self._width = width

    def format(self, session: SessionLog) -> str:
        """Format a session log as plain text.

        Args:
            session: The session log to format

        Returns:
            Plain text representation
        """
        parts: list[str] = []
        separator = "=" * self._width

        # Header
        parts.append(separator)
        title = session.name or f"Focusgroup: {session.tool}"
        parts.append(title.center(self._width))
        parts.append(f"Session: {session.display_id}".center(self._width))
        parts.append(separator)
        parts.append("")

        # Quick stats
        status = "Complete" if session.is_complete else "In Progress"
        parts.append(f"Mode: {session.mode} | Agents: {session.agent_count} | Status: {status}")
        parts.append("")

        # Rounds
        for round_ in session.rounds:
            parts.append("-" * self._width)
            parts.append(f"ROUND {round_.round_number + 1}: {round_.question}")
            parts.append("-" * self._width)
            parts.append("")

            for resp in round_.responses:
                parts.append(f"[{resp.agent_name}]")
                parts.append(resp.response.strip())
                parts.append("")

            if round_.moderator_synthesis:
                parts.append("[Moderator Synthesis]")
                parts.append(round_.moderator_synthesis.strip())
                parts.append("")

        # Final synthesis
        if session.final_synthesis:
            parts.append(separator)
            parts.append("FINAL SYNTHESIS")
            parts.append(separator)
            parts.append(session.final_synthesis.strip())
            parts.append("")

        return "\n".join(parts)

    def write(self, session: SessionLog, path: Path) -> Path:
        """Write a session log to a text file.

        Args:
            session: The session log to write
            path: Output file path

        Returns:
            Path to the written file
        """
        content = self.format(session)
        path.write_text(content)
        return path


def format_markdown(session: SessionLog) -> str:
    """Convenience function to format a session as Markdown.

    Args:
        session: The session log to format

    Returns:
        Markdown string representation
    """
    writer = MarkdownWriter()
    return writer.format(session)


def format_text(session: SessionLog) -> str:
    """Convenience function to format a session as plain text.

    Args:
        session: The session log to format

    Returns:
        Plain text representation
    """
    writer = TextWriter()
    return writer.format(session)
