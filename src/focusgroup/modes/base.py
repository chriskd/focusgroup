"""Base session mode protocol and types for focusgroup sessions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from focusgroup.agents.base import AgentResponse

if TYPE_CHECKING:
    from focusgroup.agents.base import BaseAgent


@dataclass
class RoundResult:
    """Result from a single round of agent responses.

    Attributes:
        round_number: The round index (0-based)
        prompt: The prompt sent to agents
        responses: List of agent responses received
        started_at: When the round started
        completed_at: When the round completed
        context: Optional context provided to agents
    """

    round_number: int
    prompt: str
    responses: list[AgentResponse] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    context: str | None = None

    @property
    def duration_ms(self) -> float | None:
        """Total round duration in milliseconds."""
        if self.completed_at is None:
            return None
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000

    def mark_complete(self) -> None:
        """Mark this round as completed."""
        self.completed_at = datetime.now()


@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation.

    Used by discussion and structured modes to track
    the conversation history between agents.

    Attributes:
        agent_name: Which agent made this turn
        content: What they said
        turn_type: Type of turn (response, reply, synthesis)
        timestamp: When this turn occurred
    """

    agent_name: str
    content: str
    turn_type: str = "response"  # response, reply, synthesis
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationHistory:
    """History of a multi-turn conversation.

    Tracks all turns in a discussion, allowing agents
    to see what others have said and build on it.
    """

    turns: list[ConversationTurn] = field(default_factory=list)

    def add_turn(
        self,
        agent_name: str,
        content: str,
        turn_type: str = "response",
    ) -> ConversationTurn:
        """Add a new turn to the conversation.

        Args:
            agent_name: Agent making this turn
            content: Content of the turn
            turn_type: Type of turn

        Returns:
            The created ConversationTurn
        """
        turn = ConversationTurn(
            agent_name=agent_name,
            content=content,
            turn_type=turn_type,
        )
        self.turns.append(turn)
        return turn

    def to_context_string(self, exclude_agent: str | None = None) -> str:
        """Format conversation history as context for agents.

        Args:
            exclude_agent: Optionally exclude a specific agent's turns
                (useful for not showing an agent their own responses)

        Returns:
            Formatted string of the conversation so far
        """
        if not self.turns:
            return ""

        lines = ["## Previous Responses\n"]
        for turn in self.turns:
            if exclude_agent and turn.agent_name == exclude_agent:
                continue
            lines.append(f"### {turn.agent_name}")
            lines.append(turn.content)
            lines.append("")  # Empty line between turns

        return "\n".join(lines)


@runtime_checkable
class SessionMode(Protocol):
    """Protocol defining the session mode interface.

    Session modes control how questions are presented to agents
    and how responses are collected. Different modes support
    different interaction patterns.
    """

    @property
    def name(self) -> str:
        """Display name for this mode."""
        ...

    async def run_round(
        self,
        prompt: str,
        agents: list["BaseAgent"],
        context: str | None = None,
        history: ConversationHistory | None = None,
    ) -> RoundResult:
        """Execute a single round of the session.

        Args:
            prompt: The question/prompt for this round
            agents: List of agents to query
            context: Optional tool context to provide
            history: Optional conversation history for multi-turn modes

        Returns:
            RoundResult with all agent responses
        """
        ...


class BaseSessionMode(ABC):
    """Abstract base class providing common session mode functionality.

    Provides shared implementation while requiring subclasses
    to implement the core run_round method.
    """

    def __init__(self, parallel: bool = True) -> None:
        """Initialize the session mode.

        Args:
            parallel: Whether to query agents in parallel (default True)
        """
        self._parallel = parallel

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for this mode."""
        ...

    @abstractmethod
    async def run_round(
        self,
        prompt: str,
        agents: list["BaseAgent"],
        context: str | None = None,
        history: ConversationHistory | None = None,
    ) -> RoundResult:
        """Execute a single round of the session."""
        ...

    def _build_agent_prompt(
        self,
        base_prompt: str,
        context: str | None = None,
        history: ConversationHistory | None = None,
        agent_name: str | None = None,
    ) -> tuple[str, str | None]:
        """Build the full prompt and context for an agent.

        Args:
            base_prompt: The core question/prompt
            context: Tool context (help output, etc.)
            history: Conversation history for multi-turn modes
            agent_name: Name of agent (for excluding their own history)

        Returns:
            Tuple of (prompt, context) to pass to agent.respond()
        """
        # Build conversation context if we have history
        full_context = context or ""

        if history and history.turns:
            history_str = history.to_context_string(exclude_agent=agent_name)
            if full_context:
                full_context = f"{full_context}\n\n{history_str}"
            else:
                full_context = history_str

        return base_prompt, full_context if full_context else None


class SessionModeError(Exception):
    """Base exception for session mode errors."""

    def __init__(self, message: str, mode_name: str | None = None) -> None:
        self.mode_name = mode_name
        super().__init__(message)
