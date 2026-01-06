"""Cost estimation for focusgroup sessions.

Provides rough estimates of API costs based on session configuration.
These are estimates since actual costs depend on response lengths and
provider pricing which can change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from focusgroup.config import AgentConfig, FocusgroupConfig


# Rough cost estimates per query (input + output) in USD
# Based on typical help text context (~1-2K tokens) and response (~500-1K tokens)
# These are ballpark figures for planning purposes
PROVIDER_COST_PER_QUERY = {
    "claude": 0.015,  # Claude CLI (Sonnet by default)
    "codex": 0.010,  # Codex (GPT-4o class)
}

# Default cost for unknown providers (conservative estimate)
DEFAULT_COST_PER_QUERY = 0.015

# Exploration mode multiplier (agents do more work, longer responses)
EXPLORATION_MULTIPLIER = 3.0

# Synthesis adds one more moderator query with all agent responses as context
SYNTHESIS_OVERHEAD = 0.02


@dataclass
class CostEstimate:
    """Estimated cost breakdown for a session.

    Attributes:
        base_cost: Cost for all agent queries
        exploration_cost: Additional cost from exploration mode
        synthesis_cost: Cost for moderator synthesis
        total_cost: Total estimated cost
        agent_count: Number of agents
        is_exploration: Whether exploration mode is enabled
        has_synthesis: Whether synthesis is enabled
        confidence: Estimate confidence level
    """

    base_cost: float
    exploration_cost: float
    synthesis_cost: float
    total_cost: float
    agent_count: int
    is_exploration: bool
    has_synthesis: bool
    confidence: str = "rough"  # "rough" or "moderate"
    warnings: list[str] = field(default_factory=list)

    def format_short(self) -> str:
        """Format as short inline text."""
        parts = [f"{self.agent_count} agent{'s' if self.agent_count != 1 else ''}"]

        if self.is_exploration:
            parts.append("exploration")

        if self.has_synthesis:
            parts.append("synthesis")

        features = " + ".join(parts)
        return f"{features} (est. ~${self.total_cost:.2f})"

    def format_detailed(self) -> str:
        """Format as detailed breakdown."""
        lines = ["Cost Estimate:"]
        lines.append(f"  Agents ({self.agent_count}): ${self.base_cost:.3f}")

        if self.is_exploration:
            lines.append(f"  Exploration mode: +${self.exploration_cost:.3f}")

        if self.has_synthesis:
            lines.append(f"  Synthesis: +${self.synthesis_cost:.3f}")

        lines.append("  ─────────────────")
        lines.append(f"  Total: ~${self.total_cost:.2f}")

        if self.warnings:
            lines.append("")
            for warning in self.warnings:
                lines.append(f"  Note: {warning}")

        return "\n".join(lines)


def get_provider_cost(provider: str | AgentConfig) -> float:
    """Get estimated cost per query for a provider.

    Args:
        provider: Provider name string or AgentConfig

    Returns:
        Estimated cost in USD per query
    """
    if hasattr(provider, "provider_name"):
        provider_name = provider.provider_name.lower()
    else:
        provider_name = str(provider).lower()

    return PROVIDER_COST_PER_QUERY.get(provider_name, DEFAULT_COST_PER_QUERY)


def estimate_cost(
    agent_count: int,
    provider: str = "claude",
    exploration: bool = False,
    synthesis: bool = False,
    rounds: int = 1,
) -> CostEstimate:
    """Estimate cost for a focusgroup session.

    Args:
        agent_count: Number of agents in the panel
        provider: Provider name (claude, codex, etc.)
        exploration: Whether exploration mode is enabled
        synthesis: Whether moderator synthesis is enabled
        rounds: Number of question rounds

    Returns:
        CostEstimate with breakdown and total
    """
    cost_per_query = get_provider_cost(provider)

    # Base cost: each agent responds to each round
    base_cost = agent_count * rounds * cost_per_query

    # Exploration adds significant cost (longer sessions, more tokens)
    exploration_cost = 0.0
    if exploration:
        exploration_cost = base_cost * (EXPLORATION_MULTIPLIER - 1)

    # Synthesis is one extra query with all responses as context
    synthesis_cost = 0.0
    if synthesis:
        # Moderator sees all responses, so cost scales with agent count
        synthesis_cost = SYNTHESIS_OVERHEAD + (agent_count * 0.002)

    total_cost = base_cost + exploration_cost + synthesis_cost

    # Add warnings for expensive configurations
    warnings = []
    if agent_count > 5:
        warnings.append(f"Large panel ({agent_count} agents) increases cost")
    if exploration and agent_count > 3:
        warnings.append("Exploration mode with many agents can be costly")

    return CostEstimate(
        base_cost=base_cost,
        exploration_cost=exploration_cost,
        synthesis_cost=synthesis_cost,
        total_cost=total_cost,
        agent_count=agent_count,
        is_exploration=exploration,
        has_synthesis=synthesis,
        warnings=warnings,
    )


def estimate_from_config(config: FocusgroupConfig) -> CostEstimate:
    """Estimate cost from a full config object.

    Args:
        config: FocusgroupConfig for the session

    Returns:
        CostEstimate with breakdown and total
    """
    agent_count = len(config.agents)
    exploration = config.session.exploration
    synthesis = config.session.moderator
    rounds = len(config.questions.rounds)

    # Calculate using per-agent costs
    base_cost = sum(get_provider_cost(a) for a in config.agents) * rounds

    exploration_cost = 0.0
    if exploration:
        exploration_cost = base_cost * (EXPLORATION_MULTIPLIER - 1)

    synthesis_cost = 0.0
    if synthesis:
        mod_provider = "claude"
        if config.session.moderator_agent:
            mod_provider = config.session.moderator_agent.provider_name
        mod_cost = get_provider_cost(mod_provider)
        synthesis_cost = mod_cost + (agent_count * 0.002)

    total_cost = base_cost + exploration_cost + synthesis_cost

    warnings = []
    if agent_count > 5:
        warnings.append(f"Large panel ({agent_count} agents) increases cost")
    if exploration and agent_count > 3:
        warnings.append("Exploration mode with many agents can be costly")
    if rounds > 1:
        warnings.append(f"Multiple rounds ({rounds}) multiply agent costs")

    return CostEstimate(
        base_cost=base_cost,
        exploration_cost=exploration_cost,
        synthesis_cost=synthesis_cost,
        total_cost=total_cost,
        agent_count=agent_count,
        is_exploration=exploration,
        has_synthesis=synthesis,
        warnings=warnings,
    )


# Cost thresholds for warnings
WARN_THRESHOLD = 0.10  # Show warning above $0.10
CONFIRM_THRESHOLD = 0.25  # Require confirmation above $0.25


def should_warn(estimate: CostEstimate) -> bool:
    """Check if a warning should be shown for this cost estimate."""
    return estimate.total_cost >= WARN_THRESHOLD


def should_confirm(estimate: CostEstimate) -> bool:
    """Check if user confirmation should be required for this cost estimate."""
    return estimate.total_cost >= CONFIRM_THRESHOLD
