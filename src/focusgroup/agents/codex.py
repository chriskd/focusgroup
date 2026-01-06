"""Codex CLI agent implementation."""

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

# Default timeouts for Codex CLI (seconds)
DEFAULT_CODEX_CLI_TIMEOUT = 120
DEFAULT_CODEX_CLI_EXPLORATION_TIMEOUT = 300  # Longer for exploration mode


class CodexCLIAgent(BaseAgent):
    """Codex agent using the OpenAI Codex CLI tool.

    Invokes `codex` subprocess to get responses. Codex is
    OpenAI's terminal-based coding agent.
    """

    def __init__(
        self,
        config: AgentConfig,
        timeout: int = DEFAULT_CODEX_CLI_TIMEOUT,
    ) -> None:
        """Initialize the Codex CLI agent.

        Args:
            config: Agent configuration
            timeout: Command timeout in seconds
        """
        super().__init__(config)
        self._timeout = timeout

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a response by invoking Codex CLI.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Returns:
            AgentResponse with Codex CLI's output
        """
        full_prompt = self._build_full_prompt(prompt, context)
        start_time = time.perf_counter()

        # Build command - codex uses `exec` subcommand for non-interactive mode
        # Use permissive sandbox for exploration mode to allow running arbitrary CLIs
        if self._config.exploration:
            # danger-full-access allows running arbitrary commands without sandbox restrictions
            cmd = ["codex", "exec", "--sandbox", "danger-full-access", full_prompt]
        else:
            cmd = ["codex", "exec", "--full-auto", full_prompt]

        # Add model if specified
        if self._config.model:
            cmd.extend(["--model", self._config.model])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                raise AgentError(
                    f"Codex CLI exited with code {process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            content = stdout.decode("utf-8", errors="replace")

            return AgentResponse(
                content=content,
                agent_name=self.name,
                model=self._config.model,
                latency_ms=latency_ms,
                metadata={
                    "provider": "codex-cli",
                    "timeout": self._timeout,
                },
            )

        except FileNotFoundError:
            raise AgentUnavailableError(
                "Codex CLI not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None
        except TimeoutError:
            raise AgentTimeoutError(
                f"Codex CLI timed out after {self._timeout}s",
                agent_name=self.name,
            ) from None

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Codex CLI.

        Note: CLI mode reads stdout incrementally but doesn't
        provide true token-level streaming.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as output becomes available
        """
        full_prompt = self._build_full_prompt(prompt, context)

        # Use permissive sandbox for exploration mode
        if self._config.exploration:
            cmd = ["codex", "exec", "--sandbox", "danger-full-access", full_prompt]
        else:
            cmd = ["codex", "exec", "--full-auto", full_prompt]
        if self._config.model:
            cmd.extend(["--model", self._config.model])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
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
                        f"Codex CLI timed out after {self._timeout}s",
                        agent_name=self.name,
                    ) from None

            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()  # type: ignore[union-attr]
                error_msg = stderr.decode("utf-8", errors="replace")
                raise AgentError(
                    f"Codex CLI exited with code {process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            yield StreamChunk(content="", is_final=True)

        except FileNotFoundError:
            raise AgentUnavailableError(
                "Codex CLI not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None


def create_codex_agent(config: AgentConfig) -> BaseAgent:
    """Factory function to create a Codex agent.

    Args:
        config: Agent configuration

    Returns:
        CodexCLIAgent instance
    """
    if config.provider != AgentProvider.CODEX:
        raise ValueError(f"Expected Codex provider, got {config.provider}")

    # Determine timeout: explicit config > exploration default > standard default
    if config.timeout is not None:
        timeout = config.timeout
    elif config.exploration:
        timeout = DEFAULT_CODEX_CLI_EXPLORATION_TIMEOUT
    else:
        timeout = DEFAULT_CODEX_CLI_TIMEOUT

    return CodexCLIAgent(config, timeout=timeout)
