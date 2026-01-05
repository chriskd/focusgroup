"""CLI tool wrapper for invoking external command-line tools."""

import asyncio
import shutil
import time
from pathlib import Path

from .base import (
    BaseTool,
    CommandResult,
    ToolExecutionError,
    ToolHelp,
    ToolNotFoundError,
    ToolTimeoutError,
)
from .docs import parse_help_output

# Default timeout for tool commands
DEFAULT_TIMEOUT = 30  # seconds


class CLITool(BaseTool):
    """Wrapper for external CLI tools.

    Executes commands via subprocess and captures output.
    Parses --help output into structured documentation.
    """

    def __init__(
        self,
        name: str,
        command: str,
        help_args: list[str] | None = None,
        working_dir: Path | str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the CLI tool wrapper.

        Args:
            name: Display name for the tool
            command: Base command to invoke (e.g., "memex", "git")
            help_args: Arguments to get help output (default: ["--help"])
            working_dir: Directory to run commands from
            timeout: Command timeout in seconds
            env: Additional environment variables for commands
        """
        super().__init__(name, command)
        self._help_args = help_args if help_args is not None else ["--help"]
        self._working_dir = Path(working_dir) if working_dir else None
        self._timeout = timeout
        self._env = env
        self._cached_help: ToolHelp | None = None

    @property
    def working_dir(self) -> Path | None:
        """Working directory for command execution."""
        return self._working_dir

    @property
    def timeout(self) -> int:
        """Command timeout in seconds."""
        return self._timeout

    async def get_help(self) -> ToolHelp:
        """Get structured help information by running the help command.

        Returns:
            ToolHelp with parsed documentation

        Raises:
            ToolNotFoundError: If the command is not found
            ToolExecutionError: If help command fails
            ToolTimeoutError: If help command times out
        """
        # Return cached help if available
        if self._cached_help is not None:
            return self._cached_help

        # Run help command
        result = await self.run_command(self._help_args)

        # Parse the output (prefer stdout, fall back to stderr for some tools)
        raw_output = result.stdout if result.stdout else result.stderr

        # Parse into structured format
        self._cached_help = parse_help_output(
            tool_name=self._name,
            raw_output=raw_output,
        )

        return self._cached_help

    async def run_command(self, args: list[str]) -> CommandResult:
        """Run a command with the given arguments.

        Args:
            args: Arguments to pass to the tool command

        Returns:
            CommandResult with stdout, stderr, and exit code

        Raises:
            ToolNotFoundError: If the command is not found
            ToolExecutionError: If command execution fails
            ToolTimeoutError: If command times out
        """
        # Verify command exists
        if not self._command_exists():
            raise ToolNotFoundError(
                f"Command '{self._command}' not found in PATH",
                tool_name=self._name,
            )

        # Build full command
        cmd = [self._command, *args]
        cmd_str = " ".join(cmd)

        start_time = time.perf_counter()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._working_dir,
                env=self._get_env() if self._env else None,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return CommandResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode or 0,
                command=cmd_str,
                duration_ms=duration_ms,
            )

        except FileNotFoundError:
            raise ToolNotFoundError(
                f"Command '{self._command}' not found",
                tool_name=self._name,
            ) from None
        except TimeoutError:
            # Try to kill the process
            try:
                process.kill()
            except Exception:
                pass
            raise ToolTimeoutError(
                f"Command timed out after {self._timeout}s: {cmd_str}",
                tool_name=self._name,
                timeout_seconds=self._timeout,
            ) from None
        except OSError as e:
            raise ToolExecutionError(
                f"Failed to execute command: {e}",
                tool_name=self._name,
            ) from e

    async def get_version(self) -> str | None:
        """Try to get the tool's version.

        Attempts common version flags: --version, -v, -V, version

        Returns:
            Version string if found, None otherwise
        """
        version_args = [["--version"], ["-v"], ["-V"], ["version"]]

        for args in version_args:
            try:
                result = await self.run_command(args)
                if result.success and result.stdout:
                    # Extract first line, strip common prefixes
                    line = result.stdout.strip().split("\n")[0]
                    # Remove common prefixes like "toolname version "
                    for prefix in [f"{self._name} version ", f"{self._name} ", "v", "V"]:
                        if line.lower().startswith(prefix.lower()):
                            line = line[len(prefix) :]
                    return line.strip()
            except ToolError:
                continue

        return None

    def invalidate_cache(self) -> None:
        """Clear the cached help information.

        Call this if the tool may have been updated.
        """
        self._cached_help = None

    def _command_exists(self) -> bool:
        """Check if the command exists in PATH."""
        return shutil.which(self._command) is not None

    def _get_env(self) -> dict[str, str]:
        """Get environment variables for subprocess.

        Merges custom env vars with current environment.
        """
        import os

        env = os.environ.copy()
        if self._env:
            env.update(self._env)
        return env


# Import ToolError for re-export
from .base import ToolError  # noqa: E402


def create_cli_tool(
    command: str,
    name: str | None = None,
    help_args: list[str] | None = None,
    working_dir: Path | str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> CLITool:
    """Factory function to create a CLI tool wrapper.

    Args:
        command: Base command to invoke
        name: Display name (defaults to command name)
        help_args: Arguments to get help (default: ["--help"])
        working_dir: Directory to run commands from
        timeout: Command timeout in seconds

    Returns:
        Configured CLITool instance
    """
    tool_name = name or command.split("/")[-1]  # Handle paths
    return CLITool(
        name=tool_name,
        command=command,
        help_args=help_args,
        working_dir=working_dir,
        timeout=timeout,
    )
