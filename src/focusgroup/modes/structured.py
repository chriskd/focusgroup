"""Structured phases mode - guided feedback in distinct phases."""

import asyncio
from enum import Enum

from focusgroup.agents.base import AgentResponse, BaseAgent

from .base import BaseSessionMode, ConversationHistory, RoundResult, safe_query_with_retry


class Phase(str, Enum):
    """The structured feedback phases."""

    EXPLORE = "explore"  # Initial impressions, understanding
    CRITIQUE = "critique"  # Issues, concerns, problems
    SUGGEST = "suggest"  # Recommendations, improvements
    SYNTHESIZE = "synthesize"  # Final thoughts, summary


# Phase-specific prompts that guide agents
PHASE_PROMPTS = {
    Phase.EXPLORE: """## Phase: Exploration

Focus on understanding and first impressions:
- What is your initial understanding of this tool?
- How does it fit into typical agent workflows?
- What capabilities does it offer?
- What use cases seem most appropriate?

Share your initial impressions and understanding.""",
    Phase.CRITIQUE: """## Phase: Critique

Focus on issues, concerns, and problems:
- What issues or pain points do you see?
- What might be confusing or unclear?
- What could cause errors or frustration?
- What's missing or incomplete?

Be constructively critical - identify real problems.""",
    Phase.SUGGEST: """## Phase: Suggestions

Focus on recommendations and improvements:
- What specific changes would improve this tool?
- How could the issues identified be addressed?
- What new features would add value?
- How could the documentation be better?

Provide actionable recommendations.""",
    Phase.SYNTHESIZE: """## Phase: Synthesis

Provide your final summary:
- What are the key takeaways from this evaluation?
- What should be prioritized for improvement?
- What's the overall assessment of the tool?
- Any final thoughts or recommendations?

Synthesize the discussion into actionable conclusions.""",
}


class StructuredMode(BaseSessionMode):
    """Structured phases feedback mode.

    Guides agents through distinct phases of feedback:
    1. Explore: Initial impressions and understanding
    2. Critique: Issues, concerns, and problems
    3. Suggest: Recommendations and improvements
    4. Synthesize: Final summary and conclusions

    Each phase has a specific prompt that guides agents
    to provide focused, structured feedback.

    This is ideal for:
    - Comprehensive tool evaluations
    - Structured feedback reports
    - When you want thorough, organized feedback
    """

    def __init__(
        self,
        parallel: bool = True,
        phases: list[Phase] | None = None,
    ) -> None:
        """Initialize structured mode.

        Args:
            parallel: Whether to query agents in parallel within phases
            phases: Which phases to run (defaults to all four)
        """
        super().__init__(parallel=parallel)
        self._phases = phases or list(Phase)

    @property
    def name(self) -> str:
        """Display name for this mode."""
        return "structured"

    async def run_round(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None = None,
        history: ConversationHistory | None = None,
    ) -> RoundResult:
        """Execute a structured feedback round.

        Runs each configured phase sequentially, with agents
        seeing the accumulated responses from previous phases.

        Args:
            prompt: The base question/topic for feedback
            agents: List of agents to query
            context: Optional tool context to provide
            history: Conversation history (will be updated)

        Returns:
            RoundResult with all agent responses from all phases
        """
        result = RoundResult(
            round_number=0,
            prompt=prompt,
            context=context,
        )

        # Use provided history or create a new one
        conv_history = history or ConversationHistory()

        # Run each phase
        for phase in self._phases:
            phase_prompt = self._build_phase_prompt(prompt, phase)

            # Run this phase
            if self._parallel:
                phase_responses = await self._query_parallel(
                    prompt=phase_prompt,
                    agents=agents,
                    context=context,
                    history=conv_history,
                    phase=phase,
                )
            else:
                phase_responses = await self._query_sequential(
                    prompt=phase_prompt,
                    agents=agents,
                    context=context,
                    history=conv_history,
                    phase=phase,
                )

            # Add phase responses to result and history
            result.responses.extend(phase_responses)
            for response in phase_responses:
                conv_history.add_turn(
                    agent_name=response.agent_name,
                    content=response.content,
                    turn_type=phase.value,
                )

        result.mark_complete()
        return result

    def _build_phase_prompt(self, base_prompt: str, phase: Phase) -> str:
        """Build the prompt for a specific phase.

        Args:
            base_prompt: The original question/topic
            phase: Which phase this is

        Returns:
            Combined prompt with phase instructions
        """
        phase_instructions = PHASE_PROMPTS.get(phase, "")
        return f"""{phase_instructions}

---

Original question: {base_prompt}"""

    async def _query_parallel(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
        history: ConversationHistory,
        phase: Phase,
    ) -> list[AgentResponse]:
        """Query all agents in parallel for this phase.

        Args:
            prompt: The phase prompt
            agents: List of agents to query
            context: Optional context
            history: Conversation history
            phase: Current phase

        Returns:
            List of responses
        """
        # Build context including previous phases
        full_prompt, full_context = self._build_agent_prompt(
            base_prompt=prompt,
            context=context,
            history=history if history.turns else None,
        )

        tasks = [self._safe_query(agent, full_prompt, full_context, phase) for agent in agents]
        return await asyncio.gather(*tasks)

    async def _query_sequential(
        self,
        prompt: str,
        agents: list[BaseAgent],
        context: str | None,
        history: ConversationHistory,
        phase: Phase,
    ) -> list[AgentResponse]:
        """Query agents sequentially for this phase.

        Args:
            prompt: The phase prompt
            agents: List of agents to query
            context: Optional context
            history: Conversation history
            phase: Current phase

        Returns:
            List of responses
        """
        responses = []

        for agent in agents:
            full_prompt, full_context = self._build_agent_prompt(
                base_prompt=prompt,
                context=context,
                history=history if history.turns else None,
                agent_name=agent.name,
            )

            response = await self._safe_query(agent, full_prompt, full_context, phase)
            responses.append(response)

            # Add to history so next agent sees it
            history.add_turn(
                agent_name=response.agent_name,
                content=response.content,
                turn_type=phase.value,
            )

        return responses

    async def _safe_query(
        self,
        agent: BaseAgent,
        prompt: str,
        context: str | None,
        phase: Phase,
    ) -> AgentResponse:
        """Query an agent with error handling and retry logic.

        Uses safe_query_with_retry which catches agent errors,
        handles rate limits with exponential backoff, and returns
        an error response rather than propagating exceptions.

        Args:
            agent: The agent to query
            prompt: The question to ask
            context: Optional context
            phase: Current phase (for metadata)

        Returns:
            AgentResponse (may contain error information)
        """
        response = await safe_query_with_retry(agent, prompt, context)
        # Add phase to metadata regardless of success or error
        response.metadata["phase"] = phase.value
        return response


def create_structured_mode(
    parallel: bool = True,
    phases: list[Phase] | None = None,
) -> StructuredMode:
    """Factory function to create a StructuredMode instance.

    Args:
        parallel: Whether to query agents in parallel within phases
        phases: Which phases to run (defaults to all four)

    Returns:
        Configured StructuredMode instance
    """
    return StructuredMode(parallel=parallel, phases=phases)
