"""Agent registry and factory for creating agent instances."""

from collections.abc import Callable
from dataclasses import dataclass

from focusgroup.config import AgentConfig, AgentMode, AgentProvider

from .base import BaseAgent
from .claude import ClaudeAPIAgent, ClaudeCLIAgent, create_claude_agent
from .codex import CodexCLIAgent, create_codex_agent
from .openai_agent import OpenAIAgent, create_openai_agent


@dataclass
class ProviderInfo:
    """Information about an agent provider.

    Attributes:
        provider: The provider enum value
        name: Human-readable name
        description: Brief description of the provider
        supports_api: Whether API mode is supported
        supports_cli: Whether CLI mode is supported
        factory: Factory function to create agents
    """

    provider: AgentProvider
    name: str
    description: str
    supports_api: bool
    supports_cli: bool
    factory: Callable[[AgentConfig], BaseAgent]


# Registry of all available providers
_PROVIDERS: dict[AgentProvider, ProviderInfo] = {
    AgentProvider.CLAUDE: ProviderInfo(
        provider=AgentProvider.CLAUDE,
        name="Claude",
        description="Anthropic Claude models (API and CLI)",
        supports_api=True,
        supports_cli=True,
        factory=create_claude_agent,
    ),
    AgentProvider.OPENAI: ProviderInfo(
        provider=AgentProvider.OPENAI,
        name="OpenAI",
        description="OpenAI GPT models (API only)",
        supports_api=True,
        supports_cli=False,
        factory=create_openai_agent,
    ),
    AgentProvider.CODEX: ProviderInfo(
        provider=AgentProvider.CODEX,
        name="Codex",
        description="OpenAI Codex CLI agent (CLI only)",
        supports_api=False,
        supports_cli=True,
        factory=create_codex_agent,
    ),
}


def create_agent(config: AgentConfig) -> BaseAgent:
    """Create an agent instance from configuration.

    This is the main factory function for creating agents.
    It routes to the appropriate provider-specific factory
    based on the config.

    Args:
        config: Agent configuration specifying provider, mode, etc.

    Returns:
        Configured BaseAgent instance

    Raises:
        ValueError: If provider is not supported or mode is invalid
        AgentUnavailableError: If agent cannot be initialized
    """
    provider_info = _PROVIDERS.get(config.provider)
    if not provider_info:
        raise ValueError(f"Unknown agent provider: {config.provider}")

    # Validate mode support
    if config.mode == AgentMode.API and not provider_info.supports_api:
        raise ValueError(
            f"Provider {config.provider.value} does not support API mode. Use CLI mode instead."
        )
    if config.mode == AgentMode.CLI and not provider_info.supports_cli:
        raise ValueError(
            f"Provider {config.provider.value} does not support CLI mode. Use API mode instead."
        )

    return provider_info.factory(config)


def create_agents(configs: list[AgentConfig]) -> list[BaseAgent]:
    """Create multiple agent instances from configurations.

    Args:
        configs: List of agent configurations

    Returns:
        List of configured BaseAgent instances

    Raises:
        ValueError: If any provider is not supported
        AgentUnavailableError: If any agent cannot be initialized
    """
    return [create_agent(config) for config in configs]


def list_providers() -> list[ProviderInfo]:
    """List all registered providers.

    Returns:
        List of ProviderInfo for all available providers
    """
    return list(_PROVIDERS.values())


def get_provider_info(provider: AgentProvider) -> ProviderInfo | None:
    """Get information about a specific provider.

    Args:
        provider: The provider to look up

    Returns:
        ProviderInfo if found, None otherwise
    """
    return _PROVIDERS.get(provider)


def validate_config(config: AgentConfig) -> list[str]:
    """Validate an agent configuration.

    Checks that the provider exists and supports the requested mode.

    Args:
        config: Agent configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    provider_info = _PROVIDERS.get(config.provider)
    if not provider_info:
        errors.append(f"Unknown provider: {config.provider}")
        return errors

    if config.mode == AgentMode.API and not provider_info.supports_api:
        errors.append(f"Provider {config.provider.value} does not support API mode")
    if config.mode == AgentMode.CLI and not provider_info.supports_cli:
        errors.append(f"Provider {config.provider.value} does not support CLI mode")

    return errors


def validate_configs(configs: list[AgentConfig]) -> dict[int, list[str]]:
    """Validate multiple agent configurations.

    Args:
        configs: List of agent configurations to validate

    Returns:
        Dictionary mapping config index to list of errors
        (only includes configs with errors)
    """
    all_errors = {}
    for i, config in enumerate(configs):
        errors = validate_config(config)
        if errors:
            all_errors[i] = errors
    return all_errors


# Exports for direct class access
__all__ = [
    # Factory functions
    "create_agent",
    "create_agents",
    # Registry functions
    "list_providers",
    "get_provider_info",
    "validate_config",
    "validate_configs",
    # Info type
    "ProviderInfo",
    # Agent classes (for type hints)
    "ClaudeAPIAgent",
    "ClaudeCLIAgent",
    "CodexCLIAgent",
    "OpenAIAgent",
]
