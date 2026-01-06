"""Tests for agent implementations including mock agent."""

import pytest

from focusgroup.agents.base import AgentResponse, StreamChunk
from focusgroup.agents.registry import (
    ProviderInfo,
    create_agents,
    get_provider_info,
    list_providers,
    validate_config,
    validate_configs,
)
from focusgroup.config import AgentConfig, AgentProvider

from .conftest import MockAgent, create_mock_agent


class TestMockAgent:
    """Test the MockAgent implementation."""

    @pytest.fixture(autouse=True)
    def clear_log(self):
        """Clear call log before each test."""
        MockAgent.clear_call_log()

    @pytest.mark.asyncio
    async def test_respond_returns_response(self):
        """Mock agent returns a valid AgentResponse."""
        agent = create_mock_agent(name="TestAgent")
        response = await agent.respond("What do you think?")

        assert isinstance(response, AgentResponse)
        assert response.agent_name == "TestAgent"
        assert response.content is not None
        assert "What do you think" in response.content

    @pytest.mark.asyncio
    async def test_respond_with_context(self):
        """Mock agent handles context parameter."""
        agent = create_mock_agent()
        response = await agent.respond("Question?", context="Some context")

        assert response.metadata["context_provided"] is True
        # Call should be logged
        log = MockAgent.get_call_log()
        assert len(log) == 1
        assert log[0] == ("Question?", "Some context")

    @pytest.mark.asyncio
    async def test_respond_with_custom_template(self):
        """Mock agent uses custom response template."""
        agent = create_mock_agent(response_template="Custom: {prompt} - END")
        response = await agent.respond("Hello")

        assert response.content == "Custom: Hello - END"

    @pytest.mark.asyncio
    async def test_respond_tracks_metadata(self):
        """Mock agent includes token and latency metadata."""
        agent = create_mock_agent(
            latency_ms=250.0,
            tokens_in=100,
            tokens_out=200,
        )
        response = await agent.respond("Test")

        assert response.latency_ms == 250.0
        assert response.tokens_in == 100
        assert response.tokens_out == 200
        assert response.model == "mock-model-v1"

    @pytest.mark.asyncio
    async def test_respond_can_fail(self):
        """Mock agent can simulate failures."""
        agent = create_mock_agent(
            should_fail=True,
            failure_message="Simulated API error",
        )

        with pytest.raises(RuntimeError, match="Simulated API error"):
            await agent.respond("Test")

    @pytest.mark.asyncio
    async def test_stream_respond(self):
        """Mock agent streams response in chunks."""
        agent = create_mock_agent(response_template="Hello world test")

        chunks = []
        async for chunk in agent.stream_respond("Test"):
            chunks.append(chunk)

        # Should have 3 chunks for "Hello world test"
        assert len(chunks) == 3
        assert all(isinstance(c, StreamChunk) for c in chunks)

        # Last chunk should be marked final
        assert chunks[-1].is_final is True
        assert chunks[0].is_final is False

        # Reconstruct full response
        full_response = "".join(c.content for c in chunks)
        assert full_response.strip() == "Hello world test"

    @pytest.mark.asyncio
    async def test_stream_respond_can_fail(self):
        """Mock agent streaming can simulate failures."""
        agent = create_mock_agent(
            should_fail=True,
            failure_message="Stream error",
        )

        with pytest.raises(RuntimeError, match="Stream error"):
            async for _ in agent.stream_respond("Test"):
                pass

    def test_call_log_tracking(self):
        """Call log tracks all agent invocations."""
        import asyncio

        agent1 = create_mock_agent(name="Agent1")
        agent2 = create_mock_agent(name="Agent2")

        asyncio.run(agent1.respond("Q1"))
        asyncio.run(agent2.respond("Q2", context="ctx"))
        asyncio.run(agent1.respond("Q3"))

        log = MockAgent.get_call_log()
        assert len(log) == 3
        assert log[0] == ("Q1", None)
        assert log[1] == ("Q2", "ctx")
        assert log[2] == ("Q3", None)

    def test_call_log_clear(self):
        """Call log can be cleared for test isolation."""
        import asyncio

        agent = create_mock_agent()
        asyncio.run(agent.respond("Before clear"))

        assert len(MockAgent.get_call_log()) == 1

        MockAgent.clear_call_log()
        assert len(MockAgent.get_call_log()) == 0

    def test_agent_name_property(self):
        """Agent name comes from config."""
        agent = create_mock_agent(name="CustomName")
        assert agent.name == "CustomName"

    def test_agent_config_property(self):
        """Agent config is accessible."""
        agent = create_mock_agent(name="Test", provider=AgentProvider.CODEX)
        assert agent.config.provider == AgentProvider.CODEX
        assert agent.config.name == "Test"


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_display_name_with_name(self):
        """Display name uses custom name when set."""
        config = AgentConfig(provider=AgentProvider.CLAUDE, name="MyAgent")
        assert config.display_name == "MyAgent"

    def test_display_name_with_model(self):
        """Display name uses provider:model when no name."""
        config = AgentConfig(provider=AgentProvider.CLAUDE, model="sonnet")
        assert config.display_name == "claude:sonnet"

    def test_display_name_provider_only(self):
        """Display name falls back to provider value."""
        config = AgentConfig(provider=AgentProvider.CODEX)
        assert config.display_name == "codex"


class TestAgentRegistry:
    """Test agent registry functions."""

    def test_list_providers(self):
        """list_providers returns all registered providers (built-in + custom)."""
        from focusgroup.agents.registry import list_builtin_providers

        providers = list_providers()
        builtin = list_builtin_providers()

        # At least 2 built-in providers
        assert len(builtin) == 2  # claude and codex
        assert len(providers) >= len(builtin)  # May have custom providers too
        assert all(isinstance(p, ProviderInfo) for p in providers)

        # Check built-in providers are present
        provider_types = [p.provider for p in builtin]
        assert AgentProvider.CLAUDE in provider_types
        assert AgentProvider.CODEX in provider_types

    def test_get_provider_info_claude(self):
        """get_provider_info returns Claude provider info."""
        info = get_provider_info(AgentProvider.CLAUDE)
        assert info is not None
        assert info.name == "Claude"
        assert info.cli_command == "claude"

    def test_get_provider_info_codex(self):
        """get_provider_info returns Codex provider info."""
        info = get_provider_info(AgentProvider.CODEX)
        assert info is not None
        assert info.name == "Codex"
        assert info.cli_command == "codex"

    def test_validate_config_valid_claude(self):
        """Validate valid Claude config."""
        config = AgentConfig(provider=AgentProvider.CLAUDE)
        errors = validate_config(config)
        assert errors == []

    def test_validate_config_valid_codex(self):
        """Validate valid Codex config."""
        config = AgentConfig(provider=AgentProvider.CODEX)
        errors = validate_config(config)
        assert errors == []

    def test_validate_configs_multiple(self):
        """Validate multiple configs at once."""
        configs = [
            AgentConfig(provider=AgentProvider.CLAUDE),
            AgentConfig(provider=AgentProvider.CODEX),
        ]
        errors = validate_configs(configs)
        # All configs are valid
        assert errors == {}

    def test_create_agents_multiple(self):
        """create_agents creates multiple agents."""
        configs = [
            AgentConfig(provider=AgentProvider.CLAUDE, name="Agent1"),
            AgentConfig(provider=AgentProvider.CODEX, name="Agent2"),
        ]
        agents = create_agents(configs)
        assert len(agents) == 2
        assert agents[0].name == "Agent1"
        assert agents[1].name == "Agent2"

    def test_create_agents_empty(self):
        """create_agents with empty list returns empty list."""
        agents = create_agents([])
        assert agents == []


class TestCodexTrustError:
    """Test Codex trust error detection."""

    def test_is_trust_error_detects_trusted_keyword(self):
        """Detects 'trusted' keyword in error messages."""
        from focusgroup.agents.codex import _is_trust_error

        assert _is_trust_error("not in a trusted directory")
        assert _is_trust_error("TRUSTED directory required")

    def test_is_trust_error_detects_approval_keyword(self):
        """Detects 'approval' keyword in error messages."""
        from focusgroup.agents.codex import _is_trust_error

        assert _is_trust_error("approval-mode required")
        assert _is_trust_error("Missing approval for this action")

    def test_is_trust_error_detects_git_repo_message(self):
        """Detects git repository error messages."""
        from focusgroup.agents.codex import _is_trust_error

        assert _is_trust_error("not in a git repo")
        assert _is_trust_error("Not in a Git Repo")

    def test_is_trust_error_returns_false_for_other_errors(self):
        """Returns False for unrelated errors."""
        from focusgroup.agents.codex import _is_trust_error

        assert not _is_trust_error("connection timeout")
        assert not _is_trust_error("API error 500")
        assert not _is_trust_error("rate limited")
