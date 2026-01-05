"""Session orchestrator - coordinates agents, tools, and modes."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import TYPE_CHECKING

from focusgroup.agents.base import AgentResponse as AgentModuleResponse
from focusgroup.agents.base import BaseAgent
from focusgroup.agents.registry import create_agents
from focusgroup.config import FocusgroupConfig, SessionMode
from focusgroup.storage.session_log import (
    AgentResponse as StorageAgentResponse,
)
from focusgroup.storage.session_log import (
    QuestionRound,
    SessionLog,
    SessionStorage,
    get_default_storage,
)
from focusgroup.tools.base import Tool, ToolHelp

from .base import ConversationHistory, RoundResult, SessionModeError
from .single import SingleMode

if TYPE_CHECKING:
    from .base import SessionMode as SessionModeProtocol


class SessionOrchestrator:
    """Orchestrates a focusgroup session.

    The orchestrator is responsible for:
    - Creating agents from configuration
    - Fetching tool help/context
    - Running the appropriate session mode
    - Managing conversation history
    - Recording results to the session log
    - Invoking the moderator (if enabled)
    """

    def __init__(
        self,
        config: FocusgroupConfig,
        tool: Tool,
        storage: SessionStorage | None = None,
    ) -> None:
        """Initialize the session orchestrator.

        Args:
            config: Complete session configuration
            tool: The tool being evaluated
            storage: Optional storage backend (defaults to file storage)
        """
        self._config = config
        self._tool = tool
        self._storage = storage or get_default_storage()

        # Will be initialized in setup()
        self._agents: list[BaseAgent] = []
        self._tool_help: ToolHelp | None = None
        self._mode: SessionModeProtocol | None = None
        self._history = ConversationHistory()
        self._moderator: BaseAgent | None = None

        # Session log
        self._session = SessionLog(
            name=config.session.name,
            tool=tool.command,
            mode=config.session.mode.value,
            agent_count=len(config.agents),
        )

    @property
    def session(self) -> SessionLog:
        """Get the current session log."""
        return self._session

    @property
    def agents(self) -> list[BaseAgent]:
        """Get the list of agents."""
        return self._agents

    async def setup(self) -> None:
        """Set up the session - create agents and fetch tool context.

        Should be called before run_session(). Separating setup
        allows for better error handling and progress reporting.

        Raises:
            SessionModeError: If setup fails
            AgentUnavailableError: If agent initialization fails
        """
        # Create agents from config
        self._agents = create_agents(self._config.agents)
        self._session.agent_count = len(self._agents)

        # Fetch tool help for context
        try:
            self._tool_help = await self._tool.get_help()
        except Exception as e:
            raise SessionModeError(
                f"Failed to get tool help: {e}",
                mode_name="setup",
            ) from e

        # Create the appropriate session mode
        self._mode = self._create_mode()

        # Create moderator agent if enabled
        if self._config.session.moderator:
            self._moderator = await self._create_moderator()

    def _create_mode(self) -> "SessionModeProtocol":
        """Create the appropriate session mode based on config.

        Returns:
            Configured session mode instance
        """
        # Import here to avoid circular imports
        from .discussion import DiscussionMode
        from .structured import StructuredMode

        parallel = self._config.session.parallel_agents
        mode_type = self._config.session.mode

        if mode_type == SessionMode.SINGLE:
            return SingleMode(parallel=parallel)
        elif mode_type == SessionMode.DISCUSSION:
            return DiscussionMode(parallel=parallel)
        elif mode_type == SessionMode.STRUCTURED:
            return StructuredMode(parallel=parallel)
        else:
            # Default to single mode
            return SingleMode(parallel=parallel)

    async def _create_moderator(self) -> BaseAgent | None:
        """Create a moderator agent for synthesis.

        The moderator is a special agent that synthesizes
        feedback from all other agents.

        Returns:
            Configured moderator agent, or None if not enabled
        """
        from focusgroup.config import AgentConfig, AgentMode, AgentProvider

        # Import here to avoid circular imports
        from .moderator import create_moderator_agent

        # Use a Claude agent as moderator with special config
        moderator_config = AgentConfig(
            provider=AgentProvider.CLAUDE,
            mode=AgentMode.API,
            name="Moderator",
            system_prompt="""You are a moderator synthesizing feedback from multiple AI agents.
Your role is to:
1. Identify common themes across responses
2. Highlight unique or particularly valuable insights
3. Note any disagreements or tensions between agent perspectives
4. Provide a clear, actionable summary

Be concise but comprehensive. Focus on what's most useful for improving the tool.""",
        )
        return create_moderator_agent(moderator_config)

    async def run_session(self) -> AsyncIterator[RoundResult]:
        """Run the complete session, yielding results as they complete.

        This is an async generator that yields RoundResult objects
        as each round completes. This allows for streaming output
        and progress updates during long sessions.

        Yields:
            RoundResult for each completed round

        Raises:
            SessionModeError: If session not set up or mode fails
        """
        if not self._mode or not self._agents:
            raise SessionModeError(
                "Session not set up. Call setup() first.",
                mode_name="orchestrator",
            )

        # Get tool context string
        context = self._tool_help.to_context_string() if self._tool_help else None

        # Run each question round
        questions = self._config.questions.rounds
        for i, question in enumerate(questions):
            # Run the round using the configured mode
            result = await self._mode.run_round(
                prompt=question,
                agents=self._agents,
                context=context,
                history=self._history if self._needs_history() else None,
            )

            # Update round number
            result.round_number = i

            # Update conversation history for multi-turn modes
            if self._needs_history():
                for response in result.responses:
                    self._history.add_turn(
                        agent_name=response.agent_name,
                        content=response.content,
                        turn_type="response",
                    )

            # Record to session log
            self._record_round(i, question, result)

            yield result

        # Run moderator synthesis if enabled
        if self._moderator and self._history.turns:
            await self._run_moderator_synthesis()

        # Mark session complete
        self._session.completed_at = datetime.now()

    def _needs_history(self) -> bool:
        """Check if the current mode needs conversation history.

        Returns:
            True if mode uses multi-turn conversations
        """
        mode = self._config.session.mode
        return mode in (SessionMode.DISCUSSION, SessionMode.STRUCTURED)

    def _record_round(
        self,
        round_number: int,
        question: str,
        result: RoundResult,
    ) -> None:
        """Record a completed round to the session log.

        Args:
            round_number: Which round this is
            question: The question asked
            result: The round result with responses
        """
        # Convert agent responses to storage format
        storage_responses = [self._convert_response(r, question) for r in result.responses]

        round_log = QuestionRound(
            round_number=round_number,
            question=question,
            responses=storage_responses,
        )

        self._session.rounds.append(round_log)

    def _convert_response(
        self,
        response: AgentModuleResponse,
        prompt: str,
    ) -> StorageAgentResponse:
        """Convert agent module response to storage format.

        Args:
            response: Response from agent module
            prompt: The prompt that was sent

        Returns:
            StorageAgentResponse for persistence
        """
        return StorageAgentResponse(
            agent_name=response.agent_name,
            provider=str(response.metadata.get("provider", "unknown")),
            model=response.model,
            prompt=prompt,
            response=response.content,
            timestamp=response.timestamp,
            duration_ms=int(response.latency_ms) if response.latency_ms else None,
            tokens_used=(
                (response.tokens_in or 0) + (response.tokens_out or 0)
                if response.tokens_in or response.tokens_out
                else None
            ),
        )

    async def _run_moderator_synthesis(self) -> None:
        """Run the moderator to synthesize all feedback.

        The moderator gets the full conversation history and
        produces a summary that's stored in the session log.
        """
        if not self._moderator:
            return

        # Import here to avoid circular imports
        from .moderator import synthesize_feedback

        synthesis = await synthesize_feedback(
            moderator=self._moderator,
            history=self._history,
            tool_name=self._tool.name,
        )

        self._session.final_synthesis = synthesis

        # Also record in the last round if there is one
        if self._session.rounds:
            self._session.rounds[-1].moderator_synthesis = synthesis

    def save(self) -> str:
        """Save the session log to storage.

        Returns:
            Path to the saved session file
        """
        path = self._storage.save(self._session)
        return str(path)


async def run_focusgroup(
    config: FocusgroupConfig,
    tool: Tool,
) -> SessionLog:
    """Convenience function to run a complete focusgroup session.

    This is the main entry point for running a session.
    It handles setup, execution, and saving.

    Args:
        config: Complete session configuration
        tool: The tool being evaluated

    Returns:
        Completed SessionLog

    Raises:
        SessionModeError: If session fails
    """
    orchestrator = SessionOrchestrator(config, tool)
    await orchestrator.setup()

    # Consume all rounds
    async for _ in orchestrator.run_session():
        pass

    # Save and return
    orchestrator.save()
    return orchestrator.session
