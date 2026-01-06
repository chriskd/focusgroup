"""Single question round mode - one question, all agents respond once."""

import asyncio

from focusgroup.agents.base import AgentResponse, BaseAgent

from .base import BaseSessionMode, ConversationHistory, RoundResult, safe_query_with_retry


class SingleMode(BaseSessionMode):
    """Single question round mode.

    The simplest session mode: send one question to all agents,
    collect all responses, and return them. No multi-turn
    conversation or agent-to-agent interaction.

    This is ideal for:
    - Quick feedback rounds
    - Initial impressions gathering
    - Isolated questions that don't need discussion
    """

    @property
    def name(self) -> str:
        """Display name for this mode."""
        return "single"

    async def run_round(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None = None,
        history: ConversationHistory | None = None,
    ) -> RoundResult:
        """Execute a single round of questions.

        Sends the prompt to all agents (in parallel by default)
        and collects their responses.

        Args:
            prompt: The question to ask all agents
            agents: List of agents to query
            context: Optional tool context to provide
            history: Ignored in single mode (no multi-turn)

        Returns:
            RoundResult with all agent responses
        """
        result = RoundResult(
            round_number=0,  # Single mode always uses round 0
            prompt=prompt,
            context=context,
        )

        if self._parallel:
            # Query all agents in parallel
            responses = await self._query_parallel(prompt, agents, context)
        else:
            # Query agents sequentially
            responses = await self._query_sequential(prompt, agents, context)

        result.responses = responses
        result.mark_complete()
        return result

    async def _query_parallel(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
    ) -> list[AgentResponse]:
        """Query all agents in parallel.

        Args:
            prompt: The question to ask
            agents: List of agents to query
            context: Optional context

        Returns:
            List of responses (may include error responses)
        """
        tasks = [self._safe_query(agent, prompt, context) for agent in agents]
        return await asyncio.gather(*tasks)

    async def _query_sequential(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
    ) -> list[AgentResponse]:
        """Query agents one at a time.

        Args:
            prompt: The question to ask
            agents: List of agents to query
            context: Optional context

        Returns:
            List of responses (may include error responses)
        """
        responses = []
        for agent in agents:
            response = await self._safe_query(agent, prompt, context)
            responses.append(response)
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


def create_single_mode(parallel: bool = True) -> SingleMode:
    """Factory function to create a SingleMode instance.

    Args:
        parallel: Whether to query agents in parallel

    Returns:
        Configured SingleMode instance
    """
    return SingleMode(parallel=parallel)
