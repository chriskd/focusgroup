"""Agent implementations for different LLM providers.

This module provides a unified interface for interacting with various
LLM agents (Claude, OpenAI, Codex) in both API and CLI modes.

Quick usage:
    from focusgroup.agents import create_agent
    from focusgroup.config import AgentConfig, AgentProvider, AgentMode

    config = AgentConfig(provider=AgentProvider.CLAUDE, mode=AgentMode.API)
    agent = create_agent(config)
    response = await agent.respond("Your question here")
"""

from .base import (
    Agent,
    AgentError,
    AgentResponse,
    AgentResponseError,
    AgentTimeoutError,
    AgentUnavailableError,
    BaseAgent,
    StreamChunk,
)
from .claude import ClaudeAPIAgent, ClaudeCLIAgent, create_claude_agent
from .codex import CodexCLIAgent, create_codex_agent
from .openai_agent import OpenAIAgent, create_openai_agent
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
    # Factory functions
    "create_agent",
    "create_agents",
    "create_claude_agent",
    "create_openai_agent",
    "create_codex_agent",
    # Agent implementations
    "ClaudeAPIAgent",
    "ClaudeCLIAgent",
    "OpenAIAgent",
    "CodexCLIAgent",
    # Registry
    "ProviderInfo",
    "list_providers",
    "get_provider_info",
    "validate_config",
    "validate_configs",
]
