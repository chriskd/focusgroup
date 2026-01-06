"""Free-form discussion mode - agents see and respond to each other."""

import asyncio

from focusgroup.agents.base import AgentResponse, BaseAgent

from .base import BaseSessionMode, ConversationHistory, RoundResult, safe_query_with_retry


class DiscussionMode(BaseSessionMode):
    """Free-form discussion mode.

    Agents can see each other's responses and build on them.
    The conversation flows naturally with agents reacting to
    what others have said.

    Flow:
    1. Initial round: All agents respond to the question (parallel)
    2. Follow-up rounds: Agents see previous responses and can
       add reactions, agreements, disagreements, or new ideas

    This is ideal for:
    - Collaborative feedback gathering
    - Identifying consensus and disagreements
    - Generating richer, more nuanced feedback
    """

    def __init__(
        self,
        parallel: bool = True,
        follow_up_rounds: int = 1,
    ) -> None:
        """Initialize discussion mode.

        Args:
            parallel: Whether to query agents in parallel for initial round
            follow_up_rounds: Number of follow-up discussion rounds
        """
        super().__init__(parallel=parallel)
        self._follow_up_rounds = follow_up_rounds

    @property
    def name(self) -> str:
        """Display name for this mode."""
        return "discussion"

    async def run_round(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None = None,
        history: ConversationHistory | None = None,
    ) -> RoundResult:
        """Execute a discussion round.

        First collects initial responses from all agents,
        then runs follow-up rounds where agents can see
        and respond to each other.

        Args:
            prompt: The question to discuss
            agents: List of agents to query
            context: Optional tool context to provide
            history: Conversation history (will be updated)

        Returns:
            RoundResult with all agent responses
        """
        result = RoundResult(
            round_number=0,
            prompt=prompt,
            context=context,
        )

        # Use provided history or create a new one
        conv_history = history or ConversationHistory()

        # Phase 1: Initial responses (parallel or sequential)
        if self._parallel:
            initial_responses = await self._query_parallel(
                prompt=prompt,
                agents=agents,
                context=context,
                history=conv_history,
            )
        else:
            initial_responses = await self._query_sequential(
                prompt=prompt,
                agents=agents,
                context=context,
                history=conv_history,
            )

        # Add initial responses to result and history
        result.responses.extend(initial_responses)
        for response in initial_responses:
            conv_history.add_turn(
                agent_name=response.agent_name,
                content=response.content,
                turn_type="response",
            )

        # Phase 2: Follow-up rounds
        for round_num in range(self._follow_up_rounds):
            follow_up_prompt = self._build_follow_up_prompt(prompt, round_num)

            # Follow-up is always sequential so agents see accumulating responses
            follow_up_responses = await self._query_follow_up(
                prompt=follow_up_prompt,
                agents=agents,
                context=context,
                history=conv_history,
            )

            # Add follow-up responses to result and history
            result.responses.extend(follow_up_responses)
            for response in follow_up_responses:
                conv_history.add_turn(
                    agent_name=response.agent_name,
                    content=response.content,
                    turn_type="reply",
                )

        result.mark_complete()
        return result

    def _build_follow_up_prompt(self, original_prompt: str, round_num: int) -> str:
        """Build a follow-up prompt for discussion rounds.

        Args:
            original_prompt: The original question
            round_num: Which follow-up round this is

        Returns:
            Prompt for follow-up discussion
        """
        return f"""Based on the original question and the responses from other agents above,
please add any additional thoughts, reactions, or perspectives.

You may:
- Build on ideas from other agents
- Note agreements or disagreements
- Add perspectives that weren't covered
- Synthesize common themes

Original question: {original_prompt}

What would you add to this discussion?"""

    async def _query_parallel(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
        history: ConversationHistory,
    ) -> list[AgentResponse]:
        """Query all agents in parallel for initial responses.

        Args:
            prompt: The question to ask
            agents: List of agents to query
            context: Optional context
            history: Conversation history (for context only, not updated)

        Returns:
            List of responses
        """
        # Build combined context
        full_prompt, full_context = self._build_agent_prompt(
            base_prompt=prompt,
            context=context,
            history=history if history.turns else None,
        )

        tasks = [self._safe_query(agent, full_prompt, full_context) for agent in agents]
        return await asyncio.gather(*tasks)

    async def _query_sequential(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
        history: ConversationHistory,
    ) -> list[AgentResponse]:
        """Query agents sequentially, each seeing previous responses.

        Args:
            prompt: The question to ask
            agents: List of agents to query
            context: Optional context
            history: Conversation history (updated as we go)

        Returns:
            List of responses
        """
        responses = []

        for agent in agents:
            # Build context including previous responses in this round
            full_prompt, full_context = self._build_agent_prompt(
                base_prompt=prompt,
                context=context,
                history=history if history.turns else None,
                agent_name=agent.name,  # Exclude own previous turns
            )

            response = await self._safe_query(agent, full_prompt, full_context)
            responses.append(response)

            # Add to history so next agent sees it
            history.add_turn(
                agent_name=response.agent_name,
                content=response.content,
                turn_type="response",
            )

        return responses

    async def _query_follow_up(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
        history: ConversationHistory,
    ) -> list[AgentResponse]:
        """Query agents for follow-up responses.

        Always sequential so each agent sees accumulating discussion.

        Args:
            prompt: The follow-up prompt
            agents: List of agents to query
            context: Optional context
            history: Conversation history

        Returns:
            List of follow-up responses
        """
        responses = []

        for agent in agents:
            # Each agent sees the full history including others' follow-ups
            full_prompt, full_context = self._build_agent_prompt(
                base_prompt=prompt,
                context=context,
                history=history,
                agent_name=agent.name,
            )

            response = await self._safe_query(agent, full_prompt, full_context)
            responses.append(response)

            # Add to history for next agent
            history.add_turn(
                agent_name=response.agent_name,
                content=response.content,
                turn_type="reply",
            )

        return responses

    async def _safe_query(
        self,
        agent: BaseAgent,
        prompt: str,
        context: str | None,
    ) -> AgentResponse:
        """Query an agent with error handling and retry logic.

        Uses safe_query_with_retry which catches agent errors,
        handles rate limits with exponential backoff, and returns
        an error response rather than propagating exceptions.

        Args:
            agent: The agent to query
            prompt: The question to ask
            context: Optional context

        Returns:
            AgentResponse (may contain error information)
        """
        return await safe_query_with_retry(agent, prompt, context)


def create_discussion_mode(
    parallel: bool = True,
    follow_up_rounds: int = 1,
) -> DiscussionMode:
    """Factory function to create a DiscussionMode instance.

    Args:
        parallel: Whether initial round is parallel
        follow_up_rounds: Number of follow-up rounds

    Returns:
        Configured DiscussionMode instance
    """
    return DiscussionMode(parallel=parallel, follow_up_rounds=follow_up_rounds)
