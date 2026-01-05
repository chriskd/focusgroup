"""Memex knowledge base CLI integration.

This module provides a specialized wrapper for the memex (mx) CLI tool.
It serves as a concrete example of a tool integration and can be used
for testing focusgroup with a real agent-targeted CLI.
"""

from dataclasses import dataclass
from pathlib import Path

from .base import CommandResult, ToolHelp
from .cli import CLITool


@dataclass
class SearchResult:
    """A search result from memex.

    Attributes:
        path: Path to the entry
        title: Entry title
        snippet: Matching text snippet
        score: Relevance score
    """

    path: str
    title: str
    snippet: str = ""
    score: float = 0.0


@dataclass
class EntryInfo:
    """Information about a memex entry.

    Attributes:
        path: Path to the entry
        title: Entry title
        tags: List of tags
        content: Full content (if loaded)
        created: Creation date string
    """

    path: str
    title: str
    tags: list[str]
    content: str = ""
    created: str = ""


class MemexTool(CLITool):
    """Specialized wrapper for the memex (mx) CLI.

    Provides high-level methods for common memex operations
    while still allowing arbitrary command execution.

    Example:
        tool = MemexTool()
        help_info = await tool.get_help()

        # High-level operations
        results = await tool.search("deployment")
        entry = await tool.get_entry("tooling/beads.md")

        # Arbitrary command
        result = await tool.run_command(["tags"])
    """

    def __init__(
        self,
        command: str = "mx",
        working_dir: Path | str | None = None,
        timeout: int = 30,
    ) -> None:
        """Initialize the memex tool wrapper.

        Args:
            command: CLI command to use (default: "mx")
            working_dir: Directory to run commands from
            timeout: Command timeout in seconds
        """
        super().__init__(
            name="memex",
            command=command,
            help_args=["--help"],
            working_dir=working_dir,
            timeout=timeout,
        )

    async def search(
        self,
        query: str,
        tags: list[str] | None = None,
        limit: int = 10,
        mode: str | None = None,
    ) -> list[SearchResult]:
        """Search the knowledge base.

        Args:
            query: Search query string
            tags: Optional tags to filter by
            limit: Maximum results to return
            mode: Search mode ("hybrid", "semantic", "keyword")

        Returns:
            List of SearchResult objects
        """
        args = ["search", query, f"--limit={limit}"]

        if tags:
            args.extend([f"--tags={','.join(tags)}"])
        if mode:
            args.extend([f"--mode={mode}"])

        result = await self.run_command(args)
        return self._parse_search_results(result)

    async def get_entry(self, path: str, metadata_only: bool = False) -> EntryInfo:
        """Get a knowledge base entry.

        Args:
            path: Path to the entry (e.g., "tooling/beads.md")
            metadata_only: If True, only fetch metadata

        Returns:
            EntryInfo with entry details
        """
        args = ["get", path]
        if metadata_only:
            args.append("--metadata")

        result = await self.run_command(args)
        return self._parse_entry(path, result)

    async def list_entries(
        self,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[str]:
        """List knowledge base entries.

        Args:
            tag: Optional tag to filter by
            limit: Maximum entries to return

        Returns:
            List of entry paths
        """
        args = ["list", f"--limit={limit}"]
        if tag:
            args.extend([f"--tag={tag}"])

        result = await self.run_command(args)
        # Parse output - one path per line
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    async def get_tree(self) -> str:
        """Get the knowledge base directory structure.

        Returns:
            Tree structure as string
        """
        result = await self.run_command(["tree"])
        return result.stdout

    async def get_info(self) -> str:
        """Get knowledge base configuration and stats.

        Returns:
            Info output as string
        """
        result = await self.run_command(["info"])
        return result.stdout

    async def health_check(self) -> CommandResult:
        """Run a health check on the knowledge base.

        Returns:
            CommandResult with health check output
        """
        return await self.run_command(["health"])

    async def get_subcommand_help(self, subcommand: str) -> ToolHelp:
        """Get help for a specific subcommand.

        Args:
            subcommand: The subcommand to get help for

        Returns:
            ToolHelp with parsed help for the subcommand
        """
        from .docs import parse_help_output

        result = await self.run_command([subcommand, "--help"])
        raw = result.stdout if result.stdout else result.stderr
        return parse_help_output(f"{self._name} {subcommand}", raw)

    def _parse_search_results(self, result: CommandResult) -> list[SearchResult]:
        """Parse search command output into SearchResult objects."""
        results = []

        if not result.success:
            return results

        # Parse each result line
        # Format varies but typically: "path: title" or similar
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("Found") or line.startswith("---"):
                continue

            # Simple parsing - extract path and any description
            parts = line.split(":", 1)
            if len(parts) >= 1:
                path = parts[0].strip()
                title = parts[1].strip() if len(parts) > 1 else path
                results.append(
                    SearchResult(
                        path=path,
                        title=title,
                        snippet="",
                        score=0.0,
                    )
                )

        return results

    def _parse_entry(self, path: str, result: CommandResult) -> EntryInfo:
        """Parse get command output into EntryInfo."""
        content = result.stdout
        title = path.split("/")[-1].replace(".md", "").replace("-", " ").title()
        tags: list[str] = []

        # Try to extract metadata from frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                # Extract title
                for line in frontmatter.splitlines():
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("tags:"):
                        # Tags might be inline [a, b] or multiline
                        tag_part = line.split(":", 1)[1].strip()
                        if tag_part.startswith("["):
                            tag_part = tag_part.strip("[]")
                            tags = [t.strip().strip("\"'") for t in tag_part.split(",")]

        return EntryInfo(
            path=path,
            title=title,
            tags=tags,
            content=content,
        )


def create_memex_tool(
    command: str = "mx",
    working_dir: Path | str | None = None,
    timeout: int = 30,
) -> MemexTool:
    """Factory function to create a memex tool wrapper.

    Args:
        command: CLI command to use (default: "mx")
        working_dir: Directory to run commands from
        timeout: Command timeout in seconds

    Returns:
        Configured MemexTool instance
    """
    return MemexTool(
        command=command,
        working_dir=working_dir,
        timeout=timeout,
    )
