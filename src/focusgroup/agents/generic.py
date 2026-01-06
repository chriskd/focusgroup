"""Generic CLI agent for custom providers."""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from focusgroup.config import AgentConfig

from .base import (
    AgentError,
    AgentRateLimitError,
    AgentResponse,
    AgentTimeoutError,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
    is_rate_limit_error,
    parse_retry_after,
)


@dataclass
class ProviderConfig:
    """Configuration for a custom CLI provider.

    This defines how to invoke a CLI tool as an agent provider.
    Loaded from ~/.config/focusgroup/providers.toml
    """

    name: str  # Provider name (e.g., "gemini")
    command: str  # CLI command to run (e.g., "gemini")
    prompt_flag: str = "-p"  # Flag for prompt (e.g., "-p" or "--prompt")
    model_flag: str | None = None  # Flag for model selection (e.g., "--model")
    extra_flags: list[str] | None = None  # Additional flags to always include
    timeout: int = 120  # Default timeout in seconds
    exploration_timeout: int = 300  # Timeout for exploration mode
    description: str | None = None  # Human-readable description
    positional_prompt: bool = False  # If True, prompt is positional (no flag)

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "ProviderConfig":
        """Create a ProviderConfig from a dictionary (parsed from TOML)."""
        return cls(
            name=name,
            command=data.get("command", name),
            prompt_flag=data.get("prompt_flag", "-p"),
            model_flag=data.get("model_flag"),
            extra_flags=data.get("extra_flags"),
            timeout=data.get("timeout", 120),
            exploration_timeout=data.get("exploration_timeout", 300),
            description=data.get("description"),
            positional_prompt=data.get("positional_prompt", False),
        )


class GenericCLIAgent(BaseAgent):
    """Generic agent that invokes any CLI tool based on ProviderConfig.

    This allows users to define custom CLI providers in providers.toml
    without writing Python code.
    """

    def __init__(
        self,
        config: AgentConfig,
        provider_config: ProviderConfig,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the generic CLI agent.

        Args:
            config: Agent configuration
            provider_config: Provider configuration defining CLI invocation
            timeout: Override timeout (uses provider_config defaults if None)
            env: Optional environment variables for subprocess
        """
        super().__init__(config, env=env)
        self._provider_config = provider_config
        self._timeout = timeout or provider_config.timeout

    def _build_command(self, prompt: str) -> list[str]:
        """Build the CLI command for invoking the agent."""
        cmd = [self._provider_config.command]

        # Add extra flags first
        if self._provider_config.extra_flags:
            cmd.extend(self._provider_config.extra_flags)

        # Add model flag if specified in agent config and provider supports it
        if self._config.model and self._provider_config.model_flag:
            cmd.extend([self._provider_config.model_flag, self._config.model])

        # Add prompt (either as flag or positional)
        if self._provider_config.positional_prompt:
            cmd.append(prompt)
        elif self._provider_config.prompt_flag:
            cmd.extend([self._provider_config.prompt_flag, prompt])
        else:
            # No prompt flag and not positional - append as last argument
            cmd.append(prompt)

        return cmd

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a response by invoking the CLI tool.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Returns:
            AgentResponse with CLI output
        """
        full_prompt = self._build_full_prompt(prompt, context)
        start_time = time.perf_counter()

        cmd = self._build_command(full_prompt)

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

                # Check for rate limit/quota errors
                if is_rate_limit_error(error_msg):
                    retry_after = parse_retry_after(error_msg)
                    is_quota = "quota" in error_msg.lower() or "usage_limit" in error_msg.lower()
                    raise AgentRateLimitError(
                        f"{self._provider_config.name} API rate limit: {error_msg.strip()}",
                        agent_name=self.name,
                        retry_after=retry_after,
                        is_quota_exceeded=is_quota,
                    )

                raise AgentError(
                    f"{self._provider_config.name} CLI exited with code "
                    f"{process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            content = stdout.decode("utf-8", errors="replace")

            return AgentResponse(
                content=content,
                agent_name=self.name,
                model=self._config.model,
                latency_ms=latency_ms,
                metadata={
                    "provider": self._provider_config.name,
                    "command": self._provider_config.command,
                    "timeout": self._timeout,
                },
            )

        except FileNotFoundError:
            raise AgentUnavailableError(
                f"{self._provider_config.name} CLI ({self._provider_config.command}) "
                "not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None
        except TimeoutError:
            raise AgentTimeoutError(
                f"{self._provider_config.name} CLI timed out after {self._timeout}s",
                agent_name=self.name,
            ) from None

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from the CLI tool.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as output becomes available
        """
        full_prompt = self._build_full_prompt(prompt, context)
        cmd = self._build_command(full_prompt)

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
                        f"{self._provider_config.name} CLI timed out after {self._timeout}s",
                        agent_name=self.name,
                    ) from None

            await process.wait()

            if process.returncode != 0:
                stderr = await process.stderr.read()  # type: ignore[union-attr]
                error_msg = stderr.decode("utf-8", errors="replace")

                # Check for rate limit/quota errors
                if is_rate_limit_error(error_msg):
                    retry_after = parse_retry_after(error_msg)
                    is_quota = "quota" in error_msg.lower() or "usage_limit" in error_msg.lower()
                    raise AgentRateLimitError(
                        f"{self._provider_config.name} API rate limit: {error_msg.strip()}",
                        agent_name=self.name,
                        retry_after=retry_after,
                        is_quota_exceeded=is_quota,
                    )

                raise AgentError(
                    f"{self._provider_config.name} CLI exited with code "
                    f"{process.returncode}: {error_msg}",
                    agent_name=self.name,
                )

            yield StreamChunk(content="", is_final=True)

        except FileNotFoundError:
            raise AgentUnavailableError(
                f"{self._provider_config.name} CLI ({self._provider_config.command}) "
                "not found. Is it installed and in PATH?",
                agent_name=self.name,
            ) from None


def create_generic_agent(
    config: AgentConfig,
    provider_config: ProviderConfig,
    env: dict[str, str] | None = None,
) -> BaseAgent:
    """Factory function to create a generic CLI agent.

    Args:
        config: Agent configuration
        provider_config: Provider configuration defining CLI invocation
        env: Optional environment variables for subprocess

    Returns:
        GenericCLIAgent instance
    """
    # Determine timeout: explicit config > exploration default > standard default
    if config.timeout is not None:
        timeout = config.timeout
    elif config.exploration:
        timeout = provider_config.exploration_timeout
    else:
        timeout = provider_config.timeout

    return GenericCLIAgent(config, provider_config, timeout=timeout, env=env)
