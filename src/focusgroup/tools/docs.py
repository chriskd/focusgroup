"""Documentation extraction and parsing for CLI tool help output."""

import re
from dataclasses import dataclass

from .base import HelpSection, ToolHelp

# Common section header patterns (case-insensitive)
SECTION_PATTERNS = [
    r"^(Commands?|Subcommands?):?\s*$",
    r"^(Options?|Flags?):?\s*$",
    r"^(Arguments?|Args?|Positional Arguments?):?\s*$",
    r"^(Description):?\s*$",
    r"^(Examples?):?\s*$",
    r"^(Environment Variables?|Env):?\s*$",
    r"^(Configuration|Config):?\s*$",
    r"^(Notes?):?\s*$",
    r"^(See Also):?\s*$",
    # ALL CAPS headers
    r"^([A-Z][A-Z\s]+):?\s*$",
]

# Compiled patterns
_SECTION_REGEXES = [re.compile(p, re.IGNORECASE) for p in SECTION_PATTERNS]


@dataclass
class ParsedLine:
    """A line with metadata for help parsing."""

    text: str
    indent: int
    is_empty: bool
    is_section_header: bool
    section_name: str | None = None


def _parse_line(line: str) -> ParsedLine:
    """Parse a single line to extract metadata."""
    # Calculate indent level
    stripped = line.lstrip()
    indent = len(line) - len(stripped)

    # Check if empty
    if not stripped:
        return ParsedLine(
            text=line,
            indent=indent,
            is_empty=True,
            is_section_header=False,
        )

    # Check for section headers
    for regex in _SECTION_REGEXES:
        match = regex.match(stripped)
        if match:
            section_name = match.group(1).strip().rstrip(":")
            return ParsedLine(
                text=line,
                indent=indent,
                is_empty=False,
                is_section_header=True,
                section_name=section_name,
            )

    return ParsedLine(
        text=line,
        indent=indent,
        is_empty=False,
        is_section_header=False,
    )


def _extract_usage(lines: list[str]) -> tuple[str, int]:
    """Extract usage string and return the line index where it ends.

    Returns:
        Tuple of (usage_string, end_line_index)
    """
    usage_pattern = re.compile(r"^\s*(usage:)\s*(.*)$", re.IGNORECASE)

    for i, line in enumerate(lines):
        match = usage_pattern.match(line)
        if match:
            usage_parts = [match.group(2).strip()]
            # Collect continuation lines (indented, non-empty)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if not next_line.strip():
                    break
                # Check if it's a continuation (more indented than "usage:")
                if len(next_line) - len(next_line.lstrip()) > 0:
                    usage_parts.append(next_line.strip())
                    j += 1
                else:
                    break
            return " ".join(usage_parts), j

    return "", 0


def _extract_description(lines: list[str], usage_end: int) -> str:
    """Extract the tool description from help output.

    Typically this is the text before the first section header,
    after the usage line.
    """
    desc_lines = []

    for i in range(usage_end, len(lines)):
        line = lines[i]
        parsed = _parse_line(line)

        if parsed.is_section_header:
            break

        stripped = line.strip()
        if stripped:
            desc_lines.append(stripped)
        elif desc_lines:
            # Empty line after content means end of description
            break

    return " ".join(desc_lines)


def _parse_item_line(line: str) -> tuple[str, str] | None:
    """Try to parse a line as an item with description.

    Handles formats like:
    - --option    Description here
    - command     Description here
    - -o, --opt   Description here

    Returns:
        Tuple of (item, description) or None if not an item line
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Pattern 1: Starts with dash(es) - options/flags
    # e.g., "--help, -h    Show this help"
    option_pattern = re.compile(r"^(-[\w-]+(?:\s*,\s*-[\w-]+)*(?:\s+<?\w+>?)?)\s{2,}(.+)$")
    match = option_pattern.match(stripped)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Pattern 2: Simple word followed by spaces and description
    # e.g., "search    Search the knowledge base"
    command_pattern = re.compile(r"^([\w-]+)\s{2,}(.+)$")
    match = command_pattern.match(stripped)
    if match:
        item = match.group(1)
        # Skip if it looks like a sentence fragment
        if item[0].isupper() and " " not in item:
            return None
        return item, match.group(2).strip()

    return None


def _parse_sections(lines: list[str]) -> list[HelpSection]:
    """Parse help output into sections."""
    sections = []
    current_section: str | None = None
    current_content: list[str] = []
    current_items: dict[str, str] = {}

    for line in lines:
        parsed = _parse_line(line)

        if parsed.is_section_header:
            # Save previous section if any
            if current_section:
                sections.append(
                    HelpSection(
                        name=current_section,
                        content="\n".join(current_content).strip(),
                        items=current_items,
                    )
                )
            # Start new section
            current_section = parsed.section_name
            current_content = []
            current_items = {}
        elif current_section:
            # Inside a section
            current_content.append(line)

            # Try to parse as item
            item = _parse_item_line(line)
            if item:
                current_items[item[0]] = item[1]

    # Save final section
    if current_section:
        sections.append(
            HelpSection(
                name=current_section,
                content="\n".join(current_content).strip(),
                items=current_items,
            )
        )

    return sections


def parse_help_output(tool_name: str, raw_output: str) -> ToolHelp:
    """Parse raw help output into structured ToolHelp.

    Handles various common help output formats from CLI tools.

    Args:
        tool_name: Name of the tool
        raw_output: Raw --help output string

    Returns:
        Structured ToolHelp with parsed sections
    """
    lines = raw_output.split("\n")

    # Extract usage
    usage, usage_end = _extract_usage(lines)

    # Extract description
    description = _extract_description(lines, usage_end)

    # Parse sections
    sections = _parse_sections(lines)

    return ToolHelp(
        tool_name=tool_name,
        description=description,
        usage=usage,
        sections=sections,
        raw_output=raw_output,
    )


def format_help_for_agent(help_info: ToolHelp, include_raw: bool = False) -> str:
    """Format ToolHelp as context for an agent prompt.

    This creates a structured representation that agents can
    easily parse and reference when providing feedback.

    Args:
        help_info: Parsed help information
        include_raw: Whether to include the raw output

    Returns:
        Formatted string for agent context
    """
    lines = [f"# Tool: {help_info.tool_name}"]

    if help_info.description:
        lines.append(f"\n## Description\n{help_info.description}")

    if help_info.usage:
        lines.append(f"\n## Usage\n```\n{help_info.usage}\n```")

    for section in help_info.sections:
        lines.append(f"\n## {section.name}")
        if section.items:
            for item, desc in section.items.items():
                lines.append(f"- `{item}`: {desc}")
        elif section.content:
            lines.append(section.content)

    if include_raw and help_info.raw_output:
        lines.append("\n## Raw Help Output\n```")
        lines.append(help_info.raw_output)
        lines.append("```")

    return "\n".join(lines)


def extract_subcommands(help_info: ToolHelp) -> list[str]:
    """Extract subcommand names from help info.

    Args:
        help_info: Parsed help information

    Returns:
        List of subcommand names
    """
    subcommands = []

    for section in help_info.sections:
        name_lower = section.name.lower()
        if "command" in name_lower or "subcommand" in name_lower:
            subcommands.extend(section.items.keys())

    return subcommands


def extract_options(help_info: ToolHelp) -> list[str]:
    """Extract option names from help info.

    Args:
        help_info: Parsed help information

    Returns:
        List of option strings (e.g., ["--help", "-v, --verbose"])
    """
    options = []

    for section in help_info.sections:
        name_lower = section.name.lower()
        if "option" in name_lower or "flag" in name_lower:
            options.extend(section.items.keys())

    return options
