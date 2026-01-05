"""Base agent protocol and response types for focusgroup."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from focusgroup.config import AgentConfig


@dataclass
class AgentResponse:
    """Response from an agent query.

    Attributes:
        content: The text response from the agent
        agent_name: Display name of the agent that responded
        model: Specific model used (if known)
        tokens_in: Input tokens used (if available)
        tokens_out: Output tokens used (if available)
        latency_ms: Response time in milliseconds
        timestamp: When the response was received
        metadata: Additional provider-specific metadata
    """

    content: str
    agent_name: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: float | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A chunk from a streaming response.

    Attributes:
        content: The text content of this chunk
        is_final: Whether this is the final chunk
        metadata: Additional chunk-specific metadata
    """

    content: str
    is_final: bool = False
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@runtime_checkable
class Agent(Protocol):
    """Protocol defining the agent interface.

    All agent implementations must provide these methods.
    Using Protocol allows structural subtyping - any class with
    matching methods satisfies this interface.
    """

    @property
    def name(self) -> str:
        """Display name for this agent."""
        ...

    @property
    def config(self) -> AgentConfig:
        """The agent's configuration."""
        ...

    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a complete response from the agent.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context (e.g., tool help output)

        Returns:
            Complete AgentResponse with the agent's reply
        """
        ...

    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the agent.

        Args:
            prompt: The question or prompt to send
            context: Optional additional context

        Yields:
            StreamChunk objects as the response is generated
        """
        ...


class BaseAgent(ABC):
    """Abstract base class providing common agent functionality.

    Provides shared implementation details while requiring subclasses
    to implement the core respond/stream methods.
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration from session config
        """
        self._config = config
        self._name = config.display_name

    @property
    def name(self) -> str:
        """Display name for this agent."""
        return self._name

    @property
    def config(self) -> AgentConfig:
        """The agent's configuration."""
        return self._config

    @abstractmethod
    async def respond(self, prompt: str, context: str | None = None) -> AgentResponse:
        """Get a complete response from the agent."""
        ...

    @abstractmethod
    async def stream_respond(
        self, prompt: str, context: str | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the agent."""
        ...

    def _build_full_prompt(self, prompt: str, context: str | None = None) -> str:
        """Combine prompt with optional context.

        Args:
            prompt: The main prompt/question
            context: Optional context like tool documentation

        Returns:
            Combined prompt string
        """
        if context:
            return f"""Context about the tool being evaluated:

{context}

---

{prompt}"""
        return prompt


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, agent_name: str | None = None) -> None:
        self.agent_name = agent_name
        super().__init__(message)


class AgentUnavailableError(AgentError):
    """Raised when an agent cannot be reached or initialized."""

    pass


class AgentResponseError(AgentError):
    """Raised when an agent returns an error response."""

    pass


class AgentTimeoutError(AgentError):
    """Raised when an agent response times out."""

    pass
