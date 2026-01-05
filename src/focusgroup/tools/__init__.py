"""Tool abstractions for interacting with target CLIs and documentation.

This module provides the infrastructure for wrapping external CLI tools
that focusgroup agents will evaluate. It includes:

- Base protocol and types (Tool, CommandResult, ToolHelp)
- Generic CLI wrapper (CLITool)
- Documentation parser (parse_help_output)
- Concrete implementations (MemexTool)

Example:
    from focusgroup.tools import CLITool, create_cli_tool

    # Create a generic CLI wrapper
    git = create_cli_tool("git", name="Git")
    help_info = await git.get_help()
    result = await git.run_command(["status"])

    # Use specialized wrapper
    from focusgroup.tools import MemexTool
    mx = MemexTool()
    results = await mx.search("deployment")
"""

from .base import (
    BaseTool,
    CommandResult,
    HelpSection,
    Tool,
    ToolError,
    ToolExecutionError,
    ToolHelp,
    ToolNotFoundError,
    ToolTimeoutError,
)
from .cli import CLITool, create_cli_tool
from .docs import (
    extract_options,
    extract_subcommands,
    format_help_for_agent,
    parse_help_output,
)
from .memex import (
    EntryInfo,
    MemexTool,
    SearchResult,
    create_memex_tool,
)

__all__ = [
    # Base types
    "Tool",
    "BaseTool",
    "CommandResult",
    "ToolHelp",
    "HelpSection",
    # Exceptions
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolTimeoutError",
    # CLI wrapper
    "CLITool",
    "create_cli_tool",
    # Documentation parsing
    "parse_help_output",
    "format_help_for_agent",
    "extract_subcommands",
    "extract_options",
    # Memex integration
    "MemexTool",
    "create_memex_tool",
    "SearchResult",
    "EntryInfo",
]
