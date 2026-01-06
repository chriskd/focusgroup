"""Claude CLI agent implementation."""

import asyncio
import time
from collections.abc import AsyncIterator

from focusgroup.config import AgentConfig, AgentProvider

from .base import (
    AgentError,
    AgentResponse,
    AgentTimeoutError,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
)

# Default timeouts for Claude CLI (seconds)
DEFAULT_CLAUDE_CLI_TIMEOUT = 120
DEFAULT_CLAUDE_CLI_EXPLORATION_TIMEOUT = 300  # Longer for exploration mode


class ClaudeCLIAgent(BaseAgent):
    """Claude agent using the Claude Code CLI tool.

    Invokes `claude -p <prompt>` subprocess to get responses.
    This provides "authentic" agent behavior since it uses
    the actual Claude Code tool that agents would use.
    """

    def __init__(
        self,
        config: AgentConfig,
        timeout: int = DEFAULT_CLAUDE_CLI_TIMEOUT,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the Claude CLI agent.

        Args:
            config: Agent configuration
            timeout: Command timeout in seconds
            env: Optional environment variables for subprocess
        """
        super().__init__(config, env=env)
        self._timeout = timeout

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a response by invoking Claude CLI.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Returns:
            AgentResponse with Claude CLI's output
        """
        full_prompt = self._build_full_prompt(prompt, context)
        start_time = time.perf_counter()

        # Build command
        cmd = ["claude", "-p", full_prompt, "--dangerously-skip-permissions"]

        # Add model if specified
        if self._config.model:
            cmd.extend(["--model", self._config.model])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise AgentError(
                    f"Claude CLI exited with code {process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            content = stdout.decode("utf-8", errors="replace")

            return AgentResponse(
                content=content,
                agent_name=self.name,
                model=self._config.model,
                latency_ms=latency_ms,
                metadata={
                    "provider": "claude-cli",
                    "timeout": self._timeout,
                },
            )

        except FileNotFoundError:
            raise AgentUnavailableError(
                "Claude CLI not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None
        except TimeoutError:
            raise AgentTimeoutError(
                f"Claude CLI timed out after {self._timeout}s",
                agent_name=self.name,
            ) from None

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Claude CLI.

        Note: CLI mode reads stdout incrementally but doesn't
        provide true token-level streaming.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as output becomes available
        """
        full_prompt = self._build_full_prompt(prompt, context)

        cmd = ["claude", "-p", full_prompt, "--dangerously-skip-permissions"]
        if self._config.model:
            cmd.extend(["--model", self._config.model])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )

            # Read stdout in chunks
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        process.stdout.read(1024),  # type: ignore[union-attr]
                        timeout=self._timeout,
                    )
                    if not chunk:
                        break
                    yield StreamChunk(
                        content=chunk.decode("utf-8", errors="replace"),
                        is_final=False,
                    )
                except TimeoutError:
                    process.kill()
                    raise AgentTimeoutError(
                        f"Claude CLI timed out after {self._timeout}s",
                        agent_name=self.name,
                    ) from None

            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()  # type: ignore[union-attr]
                error_msg = stderr.decode("utf-8", errors="replace")
                raise AgentError(
                    f"Claude CLI exited with code {process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            yield StreamChunk(content="", is_final=True)

        except FileNotFoundError:
            raise AgentUnavailableError(
                "Claude CLI not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None


def create_claude_agent(
    config: AgentConfig,
    env: dict[str, str] | None = None,
) -> BaseAgent:
    """Factory function to create a Claude CLI agent.

    Args:
        config: Agent configuration
        env: Optional environment variables for subprocess

    Returns:
        ClaudeCLIAgent instance
    """
    if config.provider != AgentProvider.CLAUDE:
        raise ValueError(f"Expected Claude provider, got {config.provider}")

    # Determine timeout: explicit config > exploration default > standard default
    if config.timeout is not None:
        timeout = config.timeout
    elif config.exploration:
        timeout = DEFAULT_CLAUDE_CLI_EXPLORATION_TIMEOUT
    else:
        timeout = DEFAULT_CLAUDE_CLI_TIMEOUT

    return ClaudeCLIAgent(config, timeout=timeout, env=env)
