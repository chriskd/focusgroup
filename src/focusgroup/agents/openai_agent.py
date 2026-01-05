"""OpenAI agent implementation using the Responses API."""

import os
import time
from collections.abc import AsyncIterator

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError

from focusgroup.config import AgentConfig, AgentMode, AgentProvider

from .base import (
    AgentError,
    AgentResponse,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
)

# Default model for OpenAI
DEFAULT_OPENAI_MODEL = "gpt-4o"


class OpenAIAgent(BaseAgent):
    """OpenAI agent using the Responses API.

    Uses the openai SDK to call OpenAI models via API.
    The Responses API provides a simpler interface for
    single-turn agent interactions.
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the OpenAI agent.

        Args:
            config: Agent configuration

        Raises:
            AgentUnavailableError: If OPENAI_API_KEY is not set
        """
        super().__init__(config)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise AgentUnavailableError(
                "OPENAI_API_KEY environment variable not set",
                agent_name=self.name,
            )

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = config.model or DEFAULT_OPENAI_MODEL

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a complete response from OpenAI via API.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Returns:
            Complete AgentResponse with OpenAI's reply
        """
        full_prompt = self._build_full_prompt(prompt, context)
        start_time = time.perf_counter()

        try:
            # Build messages with optional system prompt
            messages = []
            system_prompt = self._config.system_prompt or self._get_default_system_prompt()
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": full_prompt})

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4096,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract content from response
            content = response.choices[0].message.content or ""

            # Get usage stats
            tokens_in = response.usage.prompt_tokens if response.usage else None
            tokens_out = response.usage.completion_tokens if response.usage else None

            return AgentResponse(
                content=content,
                agent_name=self.name,
                model=self._model,
                mode=AgentMode.API,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                metadata={
                    "finish_reason": response.choices[0].finish_reason or "",
                    "provider": "openai",
                },
            )

        except APIConnectionError as e:
            raise AgentUnavailableError(
                f"Failed to connect to OpenAI API: {e}",
                agent_name=self.name,
            ) from e
        except RateLimitError as e:
            raise AgentError(
                f"Rate limited by OpenAI API: {e}",
                agent_name=self.name,
            ) from e
        except APIStatusError as e:
            raise AgentError(
                f"OpenAI API error: {e}",
                agent_name=self.name,
            ) from e

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from OpenAI via API.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as the response is generated
        """
        full_prompt = self._build_full_prompt(prompt, context)

        try:
            # Build messages with optional system prompt
            messages = []
            system_prompt = self._config.system_prompt or self._get_default_system_prompt()
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": full_prompt})

            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4096,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content,
                        is_final=False,
                    )

                # Check for final chunk with usage
                if chunk.usage:
                    yield StreamChunk(
                        content="",
                        is_final=True,
                        metadata={
                            "tokens_in": chunk.usage.prompt_tokens,
                            "tokens_out": chunk.usage.completion_tokens,
                        },
                    )

        except APIConnectionError as e:
            raise AgentUnavailableError(
                f"Failed to connect to OpenAI API: {e}",
                agent_name=self.name,
            ) from e
        except APIStatusError as e:
            raise AgentError(
                f"OpenAI API error during streaming: {e}",
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


def create_openai_agent(config: AgentConfig) -> BaseAgent:
    """Factory function to create an OpenAI agent.

    Args:
        config: Agent configuration

    Returns:
        OpenAIAgent instance

    Note: OpenAI only supports API mode in this implementation.
    For CLI-based OpenAI agent, use Codex provider.
    """
    if config.provider != AgentProvider.OPENAI:
        raise ValueError(f"Expected OpenAI provider, got {config.provider}")

    if config.mode == AgentMode.CLI:
        raise ValueError(
            "OpenAI provider only supports API mode. Use 'codex' provider for CLI access."
        )

    return OpenAIAgent(config)
