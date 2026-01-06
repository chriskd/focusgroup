"""Agent implementations for CLI-based LLM providers.

This module provides a unified interface for interacting with
LLM agents (Claude, Codex) via their CLI tools.

Quick usage:
    from focusgroup.agents import create_agent
    from focusgroup.config import AgentConfig, AgentProvider

    config = AgentConfig(provider=AgentProvider.CLAUDE)
    agent = create_agent(config)
    response = await agent.respond("Your question here")
"""

from .base import (
    Agent,
    AgentError,
    AgentRateLimitError,
    AgentResponse,
    AgentResponseError,
    AgentTimeoutError,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
    is_rate_limit_error,
    parse_retry_after,
)
from .claude import ClaudeCLIAgent, create_claude_agent
from .codex import CodexCLIAgent, create_codex_agent
from .registry import (
    ProviderInfo,
    create_agent,
    create_agents,
    get_provider_info,
    list_providers,
    validate_config,
    validate_configs,
)

__all__ = [
    # Core types
    "Agent",
    "BaseAgent",
    "AgentResponse",
    "StreamChunk",
    # Exceptions
    "AgentError",
    "AgentUnavailableError",
    "AgentResponseError",
    "AgentTimeoutError",
    "AgentRateLimitError",
    # Rate limit helpers
    "is_rate_limit_error",
    "parse_retry_after",
    # Factory functions
    "create_agent",
    "create_agents",
    "create_claude_agent",
    "create_codex_agent",
    # Agent implementations
    "ClaudeCLIAgent",
    "CodexCLIAgent",
    # Registry
    "ProviderInfo",
    "list_providers",
    "get_provider_info",
    "validate_config",
    "validate_configs",
]
