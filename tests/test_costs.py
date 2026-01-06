"""Tests for cost estimation module."""

from focusgroup.costs import (
    CONFIRM_THRESHOLD,
    WARN_THRESHOLD,
    CostEstimate,
    estimate_cost,
    estimate_from_config,
    get_provider_cost,
    should_confirm,
    should_warn,
)


class TestGetProviderCost:
    """Tests for get_provider_cost function."""

    def test_claude_provider(self):
        """Claude provider returns expected cost."""
        cost = get_provider_cost("claude")
        assert cost == 0.015

    def test_codex_provider(self):
        """Codex provider returns expected cost."""
        cost = get_provider_cost("codex")
        assert cost == 0.010

    def test_unknown_provider_returns_default(self):
        """Unknown provider returns default cost."""
        cost = get_provider_cost("unknown")
        assert cost == 0.015  # DEFAULT_COST_PER_QUERY

    def test_case_insensitive(self):
        """Provider name matching is case-insensitive."""
        assert get_provider_cost("CLAUDE") == get_provider_cost("claude")
        assert get_provider_cost("Codex") == get_provider_cost("codex")


class TestEstimateCost:
    """Tests for estimate_cost function."""

    def test_single_agent_basic(self):
        """Single agent with no extras returns base cost."""
        estimate = estimate_cost(agent_count=1, provider="claude")
        assert estimate.agent_count == 1
        assert estimate.base_cost == 0.015
        assert estimate.exploration_cost == 0.0
        assert estimate.synthesis_cost == 0.0
        assert estimate.total_cost == 0.015
        assert estimate.is_exploration is False
        assert estimate.has_synthesis is False

    def test_multiple_agents(self):
        """Multiple agents multiply base cost."""
        estimate = estimate_cost(agent_count=5, provider="claude")
        assert estimate.agent_count == 5
        assert estimate.base_cost == 0.015 * 5
        assert estimate.total_cost == 0.015 * 5

    def test_exploration_mode_multiplier(self):
        """Exploration mode applies multiplier."""
        estimate = estimate_cost(agent_count=1, provider="claude", exploration=True)
        assert estimate.is_exploration is True
        # Exploration adds 2x on top of base (3x total multiplier)
        assert estimate.exploration_cost > 0
        assert estimate.total_cost > estimate.base_cost

    def test_synthesis_adds_overhead(self):
        """Synthesis adds moderator overhead."""
        estimate = estimate_cost(agent_count=1, provider="claude", synthesis=True)
        assert estimate.has_synthesis is True
        assert estimate.synthesis_cost > 0
        assert estimate.total_cost > estimate.base_cost

    def test_multiple_rounds(self):
        """Multiple rounds multiply agent costs."""
        single_round = estimate_cost(agent_count=1, provider="claude", rounds=1)
        double_round = estimate_cost(agent_count=1, provider="claude", rounds=2)
        assert double_round.base_cost == single_round.base_cost * 2

    def test_combined_features(self):
        """All features combined calculate correctly."""
        estimate = estimate_cost(
            agent_count=3,
            provider="claude",
            exploration=True,
            synthesis=True,
            rounds=2,
        )
        assert estimate.agent_count == 3
        assert estimate.is_exploration is True
        assert estimate.has_synthesis is True
        assert estimate.total_cost > 0
        # Total should be sum of all components
        expected = estimate.base_cost + estimate.exploration_cost + estimate.synthesis_cost
        assert abs(estimate.total_cost - expected) < 0.001

    def test_warnings_for_large_panel(self):
        """Large panel triggers warning."""
        estimate = estimate_cost(agent_count=10, provider="claude")
        assert len(estimate.warnings) > 0
        assert any("large panel" in w.lower() for w in estimate.warnings)

    def test_warnings_for_exploration_with_many_agents(self):
        """Exploration with many agents triggers warning."""
        estimate = estimate_cost(agent_count=5, provider="claude", exploration=True)
        assert len(estimate.warnings) > 0
        assert any("exploration" in w.lower() for w in estimate.warnings)


class TestCostEstimateFormatting:
    """Tests for CostEstimate formatting methods."""

    def test_format_short_basic(self):
        """Short format shows agent count and cost."""
        estimate = estimate_cost(agent_count=3, provider="claude")
        formatted = estimate.format_short()
        assert "3 agents" in formatted
        assert "$" in formatted

    def test_format_short_exploration(self):
        """Short format shows exploration when enabled."""
        estimate = estimate_cost(agent_count=1, provider="claude", exploration=True)
        formatted = estimate.format_short()
        assert "exploration" in formatted

    def test_format_short_synthesis(self):
        """Short format shows synthesis when enabled."""
        estimate = estimate_cost(agent_count=1, provider="claude", synthesis=True)
        formatted = estimate.format_short()
        assert "synthesis" in formatted

    def test_format_short_singular_agent(self):
        """Short format uses singular 'agent' for one agent."""
        estimate = estimate_cost(agent_count=1, provider="claude")
        formatted = estimate.format_short()
        assert "1 agent" in formatted
        assert "1 agents" not in formatted

    def test_format_detailed_shows_breakdown(self):
        """Detailed format shows cost breakdown."""
        estimate = estimate_cost(agent_count=3, provider="claude", exploration=True, synthesis=True)
        formatted = estimate.format_detailed()
        assert "Agents" in formatted
        assert "Exploration" in formatted
        assert "Synthesis" in formatted
        assert "Total" in formatted


class TestShouldWarnConfirm:
    """Tests for should_warn and should_confirm thresholds."""

    def test_should_warn_below_threshold(self):
        """Should not warn below threshold."""
        estimate = CostEstimate(
            base_cost=0.01,
            exploration_cost=0.0,
            synthesis_cost=0.0,
            total_cost=0.01,
            agent_count=1,
            is_exploration=False,
            has_synthesis=False,
        )
        assert not should_warn(estimate)

    def test_should_warn_at_threshold(self):
        """Should warn at or above threshold."""
        estimate = CostEstimate(
            base_cost=WARN_THRESHOLD,
            exploration_cost=0.0,
            synthesis_cost=0.0,
            total_cost=WARN_THRESHOLD,
            agent_count=1,
            is_exploration=False,
            has_synthesis=False,
        )
        assert should_warn(estimate)

    def test_should_confirm_below_threshold(self):
        """Should not require confirmation below threshold."""
        estimate = CostEstimate(
            base_cost=0.1,
            exploration_cost=0.0,
            synthesis_cost=0.0,
            total_cost=0.1,
            agent_count=1,
            is_exploration=False,
            has_synthesis=False,
        )
        assert not should_confirm(estimate)

    def test_should_confirm_at_threshold(self):
        """Should require confirmation at or above threshold."""
        estimate = CostEstimate(
            base_cost=CONFIRM_THRESHOLD,
            exploration_cost=0.0,
            synthesis_cost=0.0,
            total_cost=CONFIRM_THRESHOLD,
            agent_count=1,
            is_exploration=False,
            has_synthesis=False,
        )
        assert should_confirm(estimate)


class TestEstimateFromConfig:
    """Tests for estimate_from_config function."""

    def test_basic_config(self):
        """Estimate from basic config works."""
        from focusgroup.config import (
            AgentConfig,
            FocusgroupConfig,
            OutputConfig,
            QuestionsConfig,
            SessionConfig,
            ToolConfig,
        )

        config = FocusgroupConfig(
            session=SessionConfig(),
            tool=ToolConfig(command="mytool"),
            agents=[
                AgentConfig(provider="claude"),
                AgentConfig(provider="claude"),
            ],
            questions=QuestionsConfig(rounds=["Question 1?"]),
            output=OutputConfig(),
        )

        estimate = estimate_from_config(config)
        assert estimate.agent_count == 2
        assert estimate.base_cost == 0.015 * 2
        assert not estimate.is_exploration
        assert not estimate.has_synthesis

    def test_config_with_exploration(self):
        """Estimate from config with exploration mode."""
        from focusgroup.config import (
            AgentConfig,
            FocusgroupConfig,
            OutputConfig,
            QuestionsConfig,
            SessionConfig,
            ToolConfig,
        )

        config = FocusgroupConfig(
            session=SessionConfig(exploration=True),
            tool=ToolConfig(command="mytool"),
            agents=[AgentConfig(provider="claude")],
            questions=QuestionsConfig(rounds=["Question 1?"]),
            output=OutputConfig(),
        )

        estimate = estimate_from_config(config)
        assert estimate.is_exploration is True
        assert estimate.exploration_cost > 0

    def test_config_with_moderator(self):
        """Estimate from config with moderator."""
        from focusgroup.config import (
            AgentConfig,
            FocusgroupConfig,
            OutputConfig,
            QuestionsConfig,
            SessionConfig,
            ToolConfig,
        )

        config = FocusgroupConfig(
            session=SessionConfig(moderator=True),
            tool=ToolConfig(command="mytool"),
            agents=[AgentConfig(provider="claude")],
            questions=QuestionsConfig(rounds=["Question 1?"]),
            output=OutputConfig(),
        )

        estimate = estimate_from_config(config)
        assert estimate.has_synthesis is True
        assert estimate.synthesis_cost > 0

    def test_config_with_multiple_rounds_warning(self):
        """Multiple rounds trigger warning."""
        from focusgroup.config import (
            AgentConfig,
            FocusgroupConfig,
            OutputConfig,
            QuestionsConfig,
            SessionConfig,
            ToolConfig,
        )

        config = FocusgroupConfig(
            session=SessionConfig(),
            tool=ToolConfig(command="mytool"),
            agents=[AgentConfig(provider="claude")],
            questions=QuestionsConfig(rounds=["Q1?", "Q2?", "Q3?"]),
            output=OutputConfig(),
        )

        estimate = estimate_from_config(config)
        assert any("round" in w.lower() for w in estimate.warnings)
