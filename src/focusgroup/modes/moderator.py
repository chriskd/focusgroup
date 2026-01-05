"""Optional moderator agent for synthesizing feedback."""

from focusgroup.agents.base import AgentResponse, BaseAgent
from focusgroup.agents.registry import create_agent
from focusgroup.config import AgentConfig, AgentProvider

from .base import ConversationHistory

# Default system prompt for the moderator
DEFAULT_MODERATOR_PROMPT = """\
You are a moderator synthesizing feedback from multiple AI agents \
evaluating a CLI tool.

Your role is to:
1. Identify common themes and patterns across all agent responses
2. Highlight unique or particularly valuable insights from individual agents
3. Note any disagreements, tensions, or different perspectives between agents
4. Provide a clear, actionable summary organized by priority

Structure your synthesis as follows:

## Key Themes
[Common patterns and shared observations]

## Notable Insights
[Unique or particularly valuable points from specific agents]

## Areas of Disagreement
[Where agents had different perspectives, and what can be learned from each]

## Priority Recommendations
[Top 3-5 actionable items, ordered by importance]

## Overall Assessment
[Brief summary of the tool's current state and path forward]

Be concise but comprehensive. Focus on what's most useful for improving the tool.
Attribute specific insights to agents when relevant."""


def create_moderator_agent(
    config: AgentConfig | None = None,
) -> BaseAgent:
    """Create a moderator agent for synthesizing feedback.

    The moderator is a specialized agent with a system prompt
    designed for synthesis and summary tasks.

    Args:
        config: Optional agent config. If not provided, uses Claude CLI
            with the default moderator system prompt.

    Returns:
        Configured BaseAgent for moderation
    """
    if config is None:
        config = AgentConfig(
            provider=AgentProvider.CLAUDE,
            name="Moderator",
            system_prompt=DEFAULT_MODERATOR_PROMPT,
        )
    elif config.system_prompt is None:
        # If config provided but no system prompt, use default
        config = AgentConfig(
            provider=config.provider,
            model=config.model,
            name=config.name or "Moderator",
            system_prompt=DEFAULT_MODERATOR_PROMPT,
        )

    return create_agent(config)


async def synthesize_feedback(
    moderator: BaseAgent,
    history: ConversationHistory,
    tool_name: str,
    question: str | None = None,
) -> str:
    """Have the moderator synthesize all feedback.

    Args:
        moderator: The moderator agent
        history: Conversation history with all agent responses
        tool_name: Name of the tool being evaluated
        question: Optional specific question to focus on

    Returns:
        Synthesis text from the moderator
    """
    # Build the synthesis prompt
    prompt = _build_synthesis_prompt(history, tool_name, question)

    # Get moderator's synthesis
    response = await moderator.respond(prompt)
    return response.content


def _build_synthesis_prompt(
    history: ConversationHistory,
    tool_name: str,
    question: str | None = None,
) -> str:
    """Build the prompt for the moderator to synthesize feedback.

    Args:
        history: Conversation history with all responses
        tool_name: Name of the tool
        question: Optional focus question

    Returns:
        Prompt string for the moderator
    """
    lines = [
        f"# Feedback Synthesis Request: {tool_name}",
        "",
    ]

    if question:
        lines.extend(
            [
                "## Focus Question",
                question,
                "",
            ]
        )

    lines.extend(
        [
            "## Agent Responses",
            "",
        ]
    )

    # Group responses by agent for clearer presentation
    agent_responses: dict[str, list[str]] = {}
    for turn in history.turns:
        if turn.agent_name not in agent_responses:
            agent_responses[turn.agent_name] = []
        agent_responses[turn.agent_name].append(f"[{turn.turn_type}] {turn.content}")

    for agent_name, responses in agent_responses.items():
        lines.append(f"### {agent_name}")
        for response in responses:
            lines.append(response)
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "Please synthesize the above feedback following your moderation guidelines.",
            "Focus on actionable insights and clear priorities.",
        ]
    )

    return "\n".join(lines)


async def quick_synthesize(
    responses: list[AgentResponse],
    tool_name: str,
    moderator_config: AgentConfig | None = None,
) -> str:
    """Quick synthesis of a list of agent responses.

    Convenience function when you have a list of responses
    rather than a full ConversationHistory.

    Args:
        responses: List of agent responses to synthesize
        tool_name: Name of the tool being evaluated
        moderator_config: Optional config for the moderator

    Returns:
        Synthesis text from the moderator
    """
    # Build a history from responses
    history = ConversationHistory()
    for response in responses:
        history.add_turn(
            agent_name=response.agent_name,
            content=response.content,
            turn_type="response",
        )

    # Create moderator and synthesize
    moderator = create_moderator_agent(moderator_config)
    return await synthesize_feedback(moderator, history, tool_name)


class ModeratorConfig:
    """Configuration options for the moderator.

    Provides sensible defaults and customization options
    for moderator behavior.
    """

    def __init__(
        self,
        provider: AgentProvider = AgentProvider.CLAUDE,
        model: str | None = None,
        custom_prompt: str | None = None,
    ) -> None:
        """Initialize moderator configuration.

        Args:
            provider: Which agent provider to use
            model: Specific model to use
            custom_prompt: Custom system prompt (replaces default)
        """
        self.provider = provider
        self.model = model
        self.custom_prompt = custom_prompt

    def to_agent_config(self) -> AgentConfig:
        """Convert to an AgentConfig.

        Returns:
            AgentConfig for creating the moderator agent
        """
        return AgentConfig(
            provider=self.provider,
            model=self.model,
            name="Moderator",
            system_prompt=self.custom_prompt or DEFAULT_MODERATOR_PROMPT,
        )

    @classmethod
    def default(cls) -> "ModeratorConfig":
        """Get the default moderator configuration.

        Returns:
            Default ModeratorConfig
        """
        return cls()
