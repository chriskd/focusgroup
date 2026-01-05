"""Shared pytest fixtures and mock agent for testing."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import ClassVar

import pytest

from focusgroup.agents.base import AgentResponse, BaseAgent, StreamChunk
from focusgroup.config import AgentConfig, AgentMode, AgentProvider
from focusgroup.storage.session_log import (
    AgentResponse as SessionAgentResponse,
)
from focusgroup.storage.session_log import (
    QuestionRound,
    SessionLog,
)


class MockAgent(BaseAgent):
    """Mock agent for testing that returns predictable responses.

    This agent doesn't make any API calls and is useful for:
    - Unit testing orchestrator logic
    - Integration tests without API keys
    - Testing output formatters with consistent data
    """

    # Class-level tracking of all responses for testing
    _call_log: ClassVar[list[tuple[str, str | None]]] = []

    def __init__(
        self,
        config: AgentConfig,
        response_template: str = "Mock response to: {prompt}",
        latency_ms: float = 100.0,
        tokens_in: int = 50,
        tokens_out: int = 100,
        should_fail: bool = False,
        failure_message: str = "Mock agent failure",
    ) -> None:
        """Initialize the mock agent.

        Args:
            config: Agent configuration
            response_template: Template for responses, {prompt} replaced with actual prompt
            latency_ms: Simulated latency in milliseconds
            tokens_in: Simulated input token count
            tokens_out: Simulated output token count
            should_fail: Whether respond() should raise an exception
            failure_message: Message for the exception if should_fail=True
        """
        super().__init__(config)
        self._response_template = response_template
        self._latency_ms = latency_ms
        self._tokens_in = tokens_in
        self._tokens_out = tokens_out
        self._should_fail = should_fail
        self._failure_message = failure_message

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Return a mock response.

        Args:
            prompt: The question or prompt
            context: Optional context (logged but not used)

        Returns:
            Mock AgentResponse

        Raises:
            RuntimeError: If should_fail=True
        """
        # Log the call for test verification
        MockAgent._call_log.append((prompt, context))

        if self._should_fail:
            raise RuntimeError(self._failure_message)

        # Build full prompt (for potential future use in more realistic mocking)
        _ = self._build_full_prompt(prompt, context)
        response_text = self._response_template.format(prompt=prompt[:50])

        return AgentResponse(
            content=response_text,
            agent_name=self.name,
            model="mock-model-v1",
            mode=self.config.mode,
            tokens_in=self._tokens_in,
            tokens_out=self._tokens_out,
            latency_ms=self._latency_ms,
            timestamp=datetime.now(),
            metadata={"mock": True, "context_provided": context is not None},
        )

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream a mock response in chunks.

        Args:
            prompt: The question or prompt
            context: Optional context

        Yields:
            StreamChunk objects simulating streaming
        """
        MockAgent._call_log.append((prompt, context))

        if self._should_fail:
            raise RuntimeError(self._failure_message)

        response_text = self._response_template.format(prompt=prompt[:50])

        # Split into word chunks
        words = response_text.split()
        for i, word in enumerate(words):
            is_final = i == len(words) - 1
            yield StreamChunk(
                content=word + (" " if not is_final else ""),
                is_final=is_final,
                metadata={"chunk_index": i},
            )

    @classmethod
    def clear_call_log(cls) -> None:
        """Clear the call log for test isolation."""
        cls._call_log = []

    @classmethod
    def get_call_log(cls) -> list[tuple[str, str | None]]:
        """Get the call log for assertions."""
        return cls._call_log.copy()


def create_mock_agent(
    name: str = "MockAgent",
    provider: AgentProvider = AgentProvider.CLAUDE,
    response_template: str = "Mock response to: {prompt}",
    **kwargs,
) -> MockAgent:
    """Factory function to create a mock agent.

    Args:
        name: Display name for the agent
        provider: Provider to simulate
        response_template: Template for responses
        **kwargs: Additional kwargs passed to MockAgent

    Returns:
        Configured MockAgent instance
    """
    config = AgentConfig(
        provider=provider,
        mode=AgentMode.API,
        name=name,
    )
    return MockAgent(config, response_template=response_template, **kwargs)


# --- Pytest Fixtures ---


@pytest.fixture
def mock_agent() -> MockAgent:
    """Provide a basic mock agent for testing."""
    MockAgent.clear_call_log()
    return create_mock_agent()


@pytest.fixture
def mock_agent_factory():
    """Provide a factory for creating mock agents with custom config."""
    MockAgent.clear_call_log()
    return create_mock_agent


@pytest.fixture
def sample_session() -> SessionLog:
    """Create a sample session with realistic data."""
    now = datetime.now()
    return SessionLog(
        id="test123",
        name="Test Focusgroup Session",
        tool="mx",
        created_at=now,
        mode="single",
        agent_count=2,
        rounds=[
            QuestionRound(
                round_number=0,
                question="How usable is this CLI?",
                responses=[
                    SessionAgentResponse(
                        agent_name="Claude",
                        provider="claude",
                        model="claude-sonnet-4-20250514",
                        prompt="How usable is this CLI?",
                        response="The CLI is well-designed with clear help text.",
                        duration_ms=1500,
                        tokens_used=150,
                    ),
                    SessionAgentResponse(
                        agent_name="GPT-4",
                        provider="openai",
                        model="gpt-4o",
                        prompt="How usable is this CLI?",
                        response="Good structure overall, could use more examples.",
                        duration_ms=2000,
                        tokens_used=200,
                    ),
                ],
            ),
        ],
    )


@pytest.fixture
def minimal_config_dict() -> dict:
    """Provide a minimal valid config dictionary."""
    return {
        "tool": {"command": "test-tool"},
        "agents": [{"provider": "claude"}],
        "questions": {"rounds": ["What do you think?"]},
    }


@pytest.fixture
def full_config_dict() -> dict:
    """Provide a full config dictionary with all options."""
    return {
        "session": {
            "name": "Test Session",
            "mode": "discussion",
            "moderator": True,
            "parallel_agents": True,
        },
        "tool": {
            "type": "cli",
            "command": "mx",
            "help_args": ["--help"],
        },
        "agents": [
            {
                "provider": "claude",
                "mode": "api",
                "model": "claude-sonnet-4-20250514",
                "name": "Claude Expert",
            },
            {
                "provider": "openai",
                "mode": "api",
                "model": "gpt-4o",
                "name": "GPT Expert",
            },
        ],
        "questions": {
            "rounds": [
                "How usable is this CLI?",
                "What would you improve?",
            ],
        },
        "output": {
            "format": "json",
            "directory": "./output",
            "save_log": True,
        },
    }
