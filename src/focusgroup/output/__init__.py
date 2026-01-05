"""Output formatters for session results.

This module provides formatters for converting SessionLog objects
to various output formats (JSON, Markdown, plain text).

All formatters follow the OutputFormatter protocol, allowing them
to be used interchangeably.
"""

from pathlib import Path
from typing import Protocol

from focusgroup.storage.session_log import SessionLog

from .json_writer import JsonWriter, format_json
from .markdown import MarkdownWriter, TextWriter, format_markdown, format_text


class OutputFormatter(Protocol):
    """Protocol for session output formatters.

    All formatters must implement these methods to be compatible
    with the output system.
    """

    def format(self, session: SessionLog) -> str:
        """Format a session log as a string.

        Args:
            session: The session log to format

        Returns:
            Formatted string representation
        """
        ...

    def write(self, session: SessionLog, path: Path) -> Path:
        """Write a session log to a file.

        Args:
            session: The session log to write
            path: Output file path

        Returns:
            Path to the written file
        """
        ...


def get_formatter(format_type: str) -> OutputFormatter:
    """Get a formatter instance for the given format type.

    Args:
        format_type: One of "json", "markdown", or "text"

    Returns:
        Appropriate formatter instance

    Raises:
        ValueError: If format type is not recognized
    """
    formatters: dict[str, type[OutputFormatter]] = {
        "json": JsonWriter,
        "markdown": MarkdownWriter,
        "md": MarkdownWriter,
        "text": TextWriter,
        "txt": TextWriter,
    }

    formatter_class = formatters.get(format_type.lower())
    if formatter_class is None:
        valid = ", ".join(sorted(set(formatters.keys())))
        raise ValueError(f"Unknown format type: {format_type}. Valid options: {valid}")

    return formatter_class()


def format_session(session: SessionLog, format_type: str = "text") -> str:
    """Format a session log in the specified format.

    Convenience function that creates the appropriate formatter
    and formats the session.

    Args:
        session: The session log to format
        format_type: Output format ("json", "markdown", "text")

    Returns:
        Formatted string representation
    """
    formatter = get_formatter(format_type)
    return formatter.format(session)


__all__ = [
    # Protocol
    "OutputFormatter",
    # Writers
    "JsonWriter",
    "MarkdownWriter",
    "TextWriter",
    # Convenience functions
    "format_json",
    "format_markdown",
    "format_text",
    "format_session",
    "get_formatter",
]
