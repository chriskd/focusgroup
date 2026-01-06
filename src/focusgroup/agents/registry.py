"""Agent registry and factory for creating agent instances."""

from collections.abc import Callable
from dataclasses import dataclass

from focusgroup.config import AgentConfig, AgentProvider, load_custom_providers

from .base import BaseAgent
from .claude import ClaudeCLIAgent, create_claude_agent
from .codex import CodexCLIAgent, create_codex_agent
from .generic import GenericCLIAgent, ProviderConfig, create_generic_agent

# Type alias for factory functions that accept config and optional env
AgentFactory = Callable[[AgentConfig, dict[str, str] | None], BaseAgent]


@dataclass
class ProviderInfo:
    """Information about an agent provider.

    Attributes:
        provider: The provider identifier (enum value or custom string)
        name: Human-readable name
        description: Brief description of the provider
        cli_command: The CLI command used to invoke this agent
        factory: Factory function to create agents
        is_builtin: Whether this is a built-in provider
        provider_config: ProviderConfig for custom providers (None for built-ins)
    """

    provider: AgentProvider | str
    name: str
    description: str
    cli_command: str
    factory: AgentFactory
    is_builtin: bool = True
    provider_config: ProviderConfig | None = None


# Registry of built-in providers (CLI-only)
_BUILTIN_PROVIDERS: dict[AgentProvider, ProviderInfo] = {
    AgentProvider.CLAUDE: ProviderInfo(
        provider=AgentProvider.CLAUDE,
        name="Claude",
        description="Anthropic Claude via claude CLI",
        cli_command="claude",
        factory=create_claude_agent,
        is_builtin=True,
    ),
    AgentProvider.CODEX: ProviderInfo(
        provider=AgentProvider.CODEX,
        name="Codex",
        description="OpenAI Codex via codex CLI",
        cli_command="codex",
        factory=create_codex_agent,
        is_builtin=True,
    ),
}

# Cache for custom providers (cleared on reload)
_custom_providers: dict[str, ProviderInfo] | None = None


def _load_custom_providers_registry() -> dict[str, ProviderInfo]:
    """Load custom providers from providers.toml into registry format."""
    custom_data = load_custom_providers()
    providers: dict[str, ProviderInfo] = {}

    for name, config_dict in custom_data.items():
        provider_config = ProviderConfig.from_dict(name, config_dict)

        # Create a factory that captures the provider_config
        def make_factory(pc: ProviderConfig) -> AgentFactory:
            def factory(config: AgentConfig, env: dict[str, str] | None = None) -> BaseAgent:
                return create_generic_agent(config, pc, env)

            return factory

        providers[name] = ProviderInfo(
            provider=name,
            name=provider_config.name,
            description=provider_config.description or f"Custom provider: {name}",
            cli_command=provider_config.command,
            factory=make_factory(provider_config),
            is_builtin=False,
            provider_config=provider_config,
        )

    return providers


def get_custom_providers() -> dict[str, ProviderInfo]:
    """Get custom providers, loading from disk if needed."""
    global _custom_providers
    if _custom_providers is None:
        _custom_providers = _load_custom_providers_registry()
    return _custom_providers


def reload_custom_providers() -> None:
    """Force reload of custom providers from disk."""
    global _custom_providers
    _custom_providers = None


def _get_provider_info(provider: AgentProvider | str) -> ProviderInfo | None:
    """Look up provider info, checking custom providers first, then built-ins."""
    provider_name = provider.value if isinstance(provider, AgentProvider) else provider

    # Check custom providers first (allows user overrides)
    custom = get_custom_providers()
    if provider_name in custom:
        return custom[provider_name]

    # Then check built-ins
    if isinstance(provider, AgentProvider):
        return _BUILTIN_PROVIDERS.get(provider)

    # Try to match string against built-in enum values
    for bp, info in _BUILTIN_PROVIDERS.items():
        if bp.value == provider_name:
            return info

    return None


def create_agent(
    config: AgentConfig,
    env: dict[str, str] | None = None,
) -> BaseAgent:
    """Create an agent instance from configuration.

    This is the main factory function for creating agents.
    It routes to the appropriate provider-specific factory
    based on the config.

    Custom providers from ~/.config/focusgroup/providers.toml are
    checked first, allowing users to override built-in providers.

    Args:
        config: Agent configuration specifying provider, etc.
        env: Optional environment variables to pass to agent subprocess.
             Use this to ensure target tools are in PATH.

    Returns:
        Configured BaseAgent instance

    Raises:
        ValueError: If provider is not supported
        AgentUnavailableError: If agent cannot be initialized
    """
    provider_info = _get_provider_info(config.provider)
    if not provider_info:
        raise ValueError(f"Unknown agent provider: {config.provider}")

    return provider_info.factory(config, env)


def create_agents(
    configs: list[AgentConfig],
    env: dict[str, str] | None = None,
) -> list[BaseAgent]:
    """Create multiple agent instances from configurations.

    Args:
        configs: List of agent configurations
        env: Optional environment variables to pass to agent subprocesses.

    Returns:
        List of configured BaseAgent instances

    Raises:
        ValueError: If any provider is not supported
        AgentUnavailableError: If any agent cannot be initialized
    """
    return [create_agent(config, env) for config in configs]


def list_providers() -> list[ProviderInfo]:
    """List all registered providers (built-in + custom).

    Returns:
        List of ProviderInfo for all available providers
    """
    # Built-ins first, then custom
    all_providers = list(_BUILTIN_PROVIDERS.values())
    all_providers.extend(get_custom_providers().values())
    return all_providers


def list_builtin_providers() -> list[ProviderInfo]:
    """List only built-in providers.

    Returns:
        List of ProviderInfo for built-in providers
    """
    return list(_BUILTIN_PROVIDERS.values())


def get_provider_info(provider: AgentProvider | str) -> ProviderInfo | None:
    """Get information about a specific provider.

    Args:
        provider: The provider to look up (enum or string)

    Returns:
        ProviderInfo if found, None otherwise
    """
    return _get_provider_info(provider)


def validate_config(config: AgentConfig) -> list[str]:
    """Validate an agent configuration.

    Checks that the provider exists (built-in or custom).

    Args:
        config: Agent configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    provider_info = _get_provider_info(config.provider)
    if not provider_info:
        errors.append(f"Unknown provider: {config.provider}")

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
    "list_builtin_providers",
    "get_provider_info",
    "get_custom_providers",
    "reload_custom_providers",
    "validate_config",
    "validate_configs",
    # Info types
    "ProviderInfo",
    "ProviderConfig",
    # Agent classes (for type hints)
    "ClaudeCLIAgent",
    "CodexCLIAgent",
    "GenericCLIAgent",
]
