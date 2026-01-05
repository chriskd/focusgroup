"""Claude agent implementations (API and CLI modes)."""

import asyncio
import os
import time
from collections.abc import AsyncIterator

import anthropic

from focusgroup.config import AgentConfig, AgentMode, AgentProvider

from .base import (
    AgentError,
    AgentResponse,
    AgentTimeoutError,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
)

# Default models for Claude
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
DEFAULT_CLAUDE_CLI_TIMEOUT = 120  # seconds


class ClaudeAPIAgent(BaseAgent):
    """Claude agent using the Anthropic API directly.

    Uses the anthropic SDK to call Claude models via API.
    Supports both streaming and non-streaming responses.
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the Claude API agent.

        Args:
            config: Agent configuration

        Raises:
            AgentUnavailableError: If ANTHROPIC_API_KEY is not set
        """
        super().__init__(config)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentUnavailableError(
                "ANTHROPIC_API_KEY environment variable not set",
                agent_name=self.name,
            )

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = config.model or DEFAULT_CLAUDE_MODEL

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a complete response from Claude via API.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Returns:
            Complete AgentResponse with Claude's reply
        """
        full_prompt = self._build_full_prompt(prompt, context)
        start_time = time.perf_counter()

        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=self._config.system_prompt or self._get_default_system_prompt(),
                messages=[{"role": "user", "content": full_prompt}],
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract text content from response
            content = ""
            for block in message.content:
                if hasattr(block, "text"):
                    content += block.text

            return AgentResponse(
                content=content,
                agent_name=self.name,
                model=self._model,
                mode=AgentMode.API,
                tokens_in=message.usage.input_tokens,
                tokens_out=message.usage.output_tokens,
                latency_ms=latency_ms,
                metadata={
                    "stop_reason": message.stop_reason or "",
                    "provider": "anthropic",
                },
            )

        except anthropic.APIConnectionError as e:
            raise AgentUnavailableError(
                f"Failed to connect to Anthropic API: {e}",
                agent_name=self.name,
            ) from e
        except anthropic.RateLimitError as e:
            raise AgentError(
                f"Rate limited by Anthropic API: {e}",
                agent_name=self.name,
            ) from e
        except anthropic.APIStatusError as e:
            raise AgentError(
                f"Anthropic API error: {e}",
                agent_name=self.name,
            ) from e

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from Claude via API.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as the response is generated
        """
        full_prompt = self._build_full_prompt(prompt, context)

        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=self._config.system_prompt or self._get_default_system_prompt(),
                messages=[{"role": "user", "content": full_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text, is_final=False)

                # Final chunk with usage stats
                final_message = await stream.get_final_message()
                yield StreamChunk(
                    content="",
                    is_final=True,
                    metadata={
                        "tokens_in": final_message.usage.input_tokens,
                        "tokens_out": final_message.usage.output_tokens,
                        "stop_reason": final_message.stop_reason or "",
                    },
                )

        except anthropic.APIConnectionError as e:
            raise AgentUnavailableError(
                f"Failed to connect to Anthropic API: {e}",
                agent_name=self.name,
            ) from e
        except anthropic.APIError as e:
            raise AgentError(
                f"Anthropic API error during streaming: {e}",
                agent_name=self.name,
            ) from e

    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for tool evaluation."""
        return """You are an AI agent evaluating a CLI tool designed for use by AI agents.
Your role is to provide constructive feedback from the perspective of an agent user.

Consider:
- Clarity and parseability of output
- Ease of use via command line
- Error messages and handling
- Documentation quality
- Whether the tool's design serves agent workflows

Be specific and actionable in your feedback."""


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
    ) -> None:
        """Initialize the Claude CLI agent.

        Args:
            config: Agent configuration
            timeout: Command timeout in seconds
        """
        super().__init__(config)
        self._timeout = timeout
        # Override name to indicate CLI mode
        self._name = f"{config.display_name} (CLI)"

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
                mode=AgentMode.CLI,
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


def create_claude_agent(config: AgentConfig) -> BaseAgent:
    """Factory function to create the appropriate Claude agent.

    Args:
        config: Agent configuration with mode specified

    Returns:
        ClaudeAPIAgent or ClaudeCLIAgent based on config.mode
    """
    if config.provider != AgentProvider.CLAUDE:
        raise ValueError(f"Expected Claude provider, got {config.provider}")

    if config.mode == AgentMode.CLI:
        return ClaudeCLIAgent(config)
    return ClaudeAPIAgent(config)
