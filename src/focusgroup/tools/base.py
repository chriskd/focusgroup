"""Base tool protocol and types for interacting with target CLIs."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class CommandResult:
    """Result from running a command on the target tool.

    Attributes:
        stdout: Standard output from the command
        stderr: Standard error output
        exit_code: Process exit code (0 = success)
        command: The full command that was executed
        duration_ms: How long the command took in milliseconds
    """

    stdout: str
    stderr: str
    exit_code: int
    command: str
    duration_ms: float | None = None

    @property
    def success(self) -> bool:
        """Whether the command succeeded (exit code 0)."""
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined stdout and stderr for convenience."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(f"[stderr]\n{self.stderr}")
        return "\n".join(parts) if parts else ""


@dataclass
class HelpSection:
    """A parsed section from help output.

    Attributes:
        name: Section name (e.g., "Commands", "Options", "Arguments")
        content: Raw content of this section
        items: Parsed items if applicable (command/option names to descriptions)
    """

    name: str
    content: str
    items: dict[str, str] = field(default_factory=dict)


@dataclass
class ToolHelp:
    """Structured help information extracted from a tool.

    Attributes:
        tool_name: Name of the tool
        description: Brief description of what the tool does
        usage: Usage pattern string (e.g., "tool [options] <command>")
        sections: Parsed help sections (Commands, Options, etc.)
        raw_output: Original unparsed help text
        version: Tool version if available
    """

    tool_name: str
    description: str
    usage: str
    sections: list[HelpSection] = field(default_factory=list)
    raw_output: str = ""
    version: str | None = None

    def get_section(self, name: str) -> HelpSection | None:
        """Get a section by name (case-insensitive).

        Args:
            name: Section name to find

        Returns:
            HelpSection if found, None otherwise
        """
        name_lower = name.lower()
        for section in self.sections:
            if section.name.lower() == name_lower:
                return section
        return None

    def to_context_string(self, exploration: bool = False) -> str:
        """Format help as context string for agent prompts.

        Args:
            exploration: If True, include instructions for interactive exploration

        Returns:
            Formatted string suitable for providing to agents as context
        """
        lines = [f"# {self.tool_name}"]

        if self.description:
            lines.append(f"\n{self.description}")

        if self.version:
            lines.append(f"\nVersion: {self.version}")

        if self.usage:
            lines.append(f"\n## Usage\n```\n{self.usage}\n```")

        for section in self.sections:
            lines.append(f"\n## {section.name}")
            if section.items:
                for item, desc in section.items.items():
                    lines.append(f"- `{item}`: {desc}")
            elif section.content:
                lines.append(section.content)

        # Add exploration instructions if enabled
        if exploration:
            lines.append(self._exploration_instructions())

        return "\n".join(lines)

    def _exploration_instructions(self) -> str:
        """Generate instructions for interactive tool exploration."""
        return f"""

## Interactive Exploration

**IMPORTANT**: You can and should run `{self.tool_name}` commands to explore this tool!

### How to Explore
1. Try running `{self.tool_name} --help` to see the full help
2. Run a few example commands to see actual output
3. Test edge cases and error handling
4. Explore subcommands that interest you

### What to Evaluate
- Does the output make sense? Is it parseable?
- Are error messages helpful?
- Does the tool behave as documented?
- What would make it easier for you as an AI agent to use?

Run commands now to form your opinion based on real usage, not just documentation."""


@runtime_checkable
class Tool(Protocol):
    """Protocol defining the tool interface.

    All tool implementations must provide these methods.
    Tools represent external CLIs or services that focusgroup
    agents will evaluate and provide feedback on.
    """

    @property
    def name(self) -> str:
        """Display name for this tool."""
        ...

    @property
    def command(self) -> str:
        """Base command to invoke this tool."""
        ...

    async def get_help(self) -> ToolHelp:
        """Get structured help information from the tool.

        Returns:
            ToolHelp with parsed documentation

        Raises:
            ToolError: If help cannot be retrieved
        """
        ...

    async def run_command(self, args: list[str]) -> CommandResult:
        """Run an arbitrary command on the tool.

        Args:
            args: Arguments to pass to the tool command

        Returns:
            CommandResult with output and exit code

        Raises:
            ToolError: If command cannot be executed
        """
        ...


class BaseTool(ABC):
    """Abstract base class providing common tool functionality.

    Provides shared implementation while requiring subclasses
    to implement the core methods.
    """

    def __init__(self, name: str, command: str) -> None:
        """Initialize the tool.

        Args:
            name: Display name for the tool
            command: Base command to invoke
        """
        self._name = name
        self._command = command

    @property
    def name(self) -> str:
        """Display name for this tool."""
        return self._name

    @property
    def command(self) -> str:
        """Base command to invoke this tool."""
        return self._command

    @abstractmethod
    async def get_help(self) -> ToolHelp:
        """Get structured help information from the tool."""
        ...

    @abstractmethod
    async def run_command(self, args: list[str]) -> CommandResult:
        """Run an arbitrary command on the tool."""
        ...


class ToolError(Exception):
    """Base exception for tool-related errors."""

    def __init__(self, message: str, tool_name: str | None = None) -> None:
        self.tool_name = tool_name
        super().__init__(message)


class ToolNotFoundError(ToolError):
    """Raised when a tool executable cannot be found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when a tool command fails to execute."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message, tool_name)
        self.exit_code = exit_code
        self.stderr = stderr


class ToolTimeoutError(ToolError):
    """Raised when a tool command times out."""

    def __init__(
        self, message: str, tool_name: str | None = None, timeout_seconds: float = 0
    ) -> None:
        super().__init__(message, tool_name)
        self.timeout_seconds = timeout_seconds
