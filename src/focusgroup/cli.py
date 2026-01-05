"""CLI interface for focusgroup."""

import asyncio
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from focusgroup import __version__
from focusgroup.config import (
    AgentConfig,
    AgentMode,
    AgentProvider,
    FocusgroupConfig,
    OutputConfig,
    QuestionsConfig,
    SessionConfig,
    ToolConfig,
    get_agents_dir,
    list_agent_presets,
    load_agent_preset,
    load_config,
)
from focusgroup.modes.orchestrator import SessionOrchestrator
from focusgroup.output import format_session, get_formatter
from focusgroup.storage.session_log import get_default_storage
from focusgroup.tools.cli import create_cli_tool

app = typer.Typer(
    name="focusgroup",
    help="Gather feedback from multiple LLM agents on tools designed for agent use.",
    no_args_is_help=True,
)

agents_app = typer.Typer(help="Manage agent presets.")
logs_app = typer.Typer(help="View and manage session logs.")

app.add_typer(agents_app, name="agents")
app.add_typer(logs_app, name="logs")

console = Console()


def resolve_context(context: str) -> str:
    """Resolve context from a file path or shell command.

    Args:
        context: Either "@path/to/file" to read a file, or a shell command to run

    Returns:
        The file contents or command output

    Raises:
        typer.Exit: If file not found or command fails
    """
    if context.startswith("@"):
        # Read from file
        file_path = Path(context[1:]).expanduser()
        if not file_path.exists():
            console.print(f"[red]Context file not found: {file_path}[/red]")
            raise typer.Exit(1)
        try:
            return file_path.read_text()
        except Exception as e:
            console.print(f"[red]Failed to read context file: {e}[/red]")
            raise typer.Exit(1) from None
    else:
        # Run as shell command
        try:
            result = subprocess.run(
                context,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Combine stdout and stderr (some tools output help to stderr)
            output = result.stdout
            if result.stderr and not output:
                output = result.stderr
            elif result.stderr:
                output = f"{output}\n{result.stderr}"

            if not output.strip():
                console.print("[yellow]Warning: Context command produced no output[/yellow]")

            return output
        except subprocess.TimeoutExpired:
            console.print("[red]Context command timed out after 30s[/red]")
            raise typer.Exit(1) from None
        except Exception as e:
            console.print(f"[red]Failed to run context command: {e}[/red]")
            raise typer.Exit(1) from None


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"focusgroup {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """Focusgroup: LLM agent feedback for tool developers."""
    pass


@app.command()
def ask(
    tool: Annotated[str, typer.Argument(help="Tool name for session labeling (e.g., 'mx')")],
    question: Annotated[str, typer.Argument(help="Question to ask the agent panel")],
    context: Annotated[
        str,
        typer.Option(
            "--context",
            "-x",
            help="Context command or file: 'mytool --help' or '@README.md'",
        ),
    ],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to config file for agent settings"),
    ] = None,
    agents: Annotated[
        int,
        typer.Option("--agents", "-n", help="Number of agents to query"),
    ] = 3,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: json, markdown, or text"),
    ] = "text",
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help="Agent provider: claude, openai, or codex"),
    ] = "claude",
    cli_mode: Annotated[
        bool,
        typer.Option("--cli", help="Use CLI mode instead of API mode"),
    ] = False,
    explore: Annotated[
        bool,
        typer.Option("--explore", "-e", help="Enable exploration (agents can run tool)"),
    ] = False,
    synthesize_with: Annotated[
        str | None,
        typer.Option(
            "--synthesize-with", "-s", help="Moderator: codex, claude, claude-cli, openai"
        ),
    ] = None,
) -> None:
    """Quick ad-hoc query to an agent panel about a tool.

    Provide context via --context: either a shell command to run (e.g., 'mytool --help')
    or a file path prefixed with @ (e.g., '@README.md').
    """
    # Resolve context upfront (file or command)
    resolved_context = resolve_context(context)

    asyncio.run(
        _ask_impl(
            tool,
            question,
            resolved_context,
            config,
            agents,
            output,
            provider,
            cli_mode,
            explore,
            synthesize_with,
        )
    )


def _parse_synthesize_with(synthesize_with: str | None) -> AgentConfig | None:
    """Parse --synthesize-with into an AgentConfig.

    Args:
        synthesize_with: String like 'codex', 'claude', 'claude-cli', 'openai'

    Returns:
        AgentConfig for the moderator, or None if not specified
    """
    if not synthesize_with:
        return None

    synthesize_with = synthesize_with.lower().strip()

    # Map string to provider/mode
    provider_map = {
        "codex": (AgentProvider.CODEX, AgentMode.CLI),
        "claude": (AgentProvider.CLAUDE, AgentMode.API),
        "claude-cli": (AgentProvider.CLAUDE, AgentMode.CLI),
        "openai": (AgentProvider.OPENAI, AgentMode.API),
    }

    if synthesize_with not in provider_map:
        console.print(f"[red]Unknown synthesizer: {synthesize_with}[/red]")
        console.print("Valid options: codex, claude, claude-cli, openai")
        raise typer.Exit(1)

    provider, mode = provider_map[synthesize_with]
    return AgentConfig(
        provider=provider,
        mode=mode,
        name="Moderator",
    )


async def _ask_impl(
    tool: str,
    question: str,
    context: str,
    config_path: Path | None,
    num_agents: int,
    output_format: str,
    provider_str: str,
    cli_mode: bool = False,
    explore: bool = False,
    synthesize_with: str | None = None,
) -> None:
    """Implementation of the ask command."""
    # Parse --synthesize-with into moderator config
    moderator_config = _parse_synthesize_with(synthesize_with)
    enable_moderator = moderator_config is not None

    # If config provided, load it but override with command-line args
    if config_path:
        try:
            fg_config = load_config(config_path)
            # Override questions
            fg_config.questions = QuestionsConfig(rounds=[question])
            fg_config.output.format = output_format  # type: ignore
            # Override moderator if --synthesize-with provided
            if moderator_config:
                fg_config.session.moderator = True
                fg_config.session.moderator_agent = moderator_config
        except Exception as e:
            console.print(f"[red]Failed to load config: {e}[/red]")
            raise typer.Exit(1) from None
    else:
        # Build a quick config
        try:
            prov = AgentProvider(provider_str.lower())
        except ValueError:
            console.print(f"[red]Unknown provider: {provider_str}[/red]")
            console.print("Valid options: claude, openai, codex")
            raise typer.Exit(1) from None

        # Determine mode: Codex is always CLI, others use --cli flag or API
        if prov == AgentProvider.CODEX:
            mode = AgentMode.CLI
        else:
            mode = AgentMode.CLI if cli_mode else AgentMode.API

        # Create N agents with different names
        agent_configs = [
            AgentConfig(
                provider=prov,
                mode=mode,
                name=f"Agent-{i + 1}",
            )
            for i in range(num_agents)
        ]

        fg_config = FocusgroupConfig(
            session=SessionConfig(
                name=f"Quick: {tool}",
                exploration=explore,
                moderator=enable_moderator,
                moderator_agent=moderator_config,
            ),
            tool=ToolConfig(command=tool),
            agents=agent_configs,
            questions=QuestionsConfig(rounds=[question]),
            output=OutputConfig(format=output_format, save_log=True),  # type: ignore
        )

    # Create the tool wrapper (still used for exploration mode)
    cli_tool = create_cli_tool(tool)

    # Run the session with explicit context
    orchestrator = SessionOrchestrator(fg_config, cli_tool, context=context)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(f"Setting up with {len(fg_config.agents)} agents...", total=None)
        try:
            await orchestrator.setup()
        except Exception as e:
            console.print(f"[red]Setup failed: {e}[/red]")
            raise typer.Exit(1) from None

        progress.add_task(f"Asking about {tool}...", total=None)
        async for _result in orchestrator.run_session():
            # Results stream in, but we wait for all
            pass

    # Save the session
    session_path = orchestrator.save()
    session = orchestrator.session

    # Output based on format
    formatted = format_session(session, output_format)
    console.print(formatted)

    # Show where session was saved
    console.print(f"\n[dim]Session saved: {session_path}[/dim]")


@app.command()
def run(
    config_file: Annotated[
        Path,
        typer.Argument(help="Path to session config TOML file"),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Directory for session output"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing"),
    ] = False,
    format: Annotated[
        str | None,
        typer.Option("--format", "-f", help="Output format override: json, markdown, or text"),
    ] = None,
) -> None:
    """Run a full feedback session from a config file."""
    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise typer.Exit(1)

    try:
        fg_config = load_config(config_file)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        raise typer.Exit(1) from None

    # Override format if specified
    if format:
        fg_config.output.format = format  # type: ignore

    if dry_run:
        _show_session_plan(fg_config)
    else:
        asyncio.run(_run_impl(fg_config, output_dir))


def _show_session_plan(config: FocusgroupConfig) -> None:
    """Show what would be done in a session."""
    console.print("\n[bold]Session Plan[/bold]")
    console.print(f"Tool: [cyan]{config.tool.command}[/cyan]")
    console.print(f"Mode: {config.session.mode.value}")
    console.print(f"Moderator: {'enabled' if config.session.moderator else 'disabled'}")
    console.print(f"Output format: {config.output.format}")

    console.print(f"\n[bold]Agents ({len(config.agents)}):[/bold]")
    for agent in config.agents:
        mode_str = f"({agent.mode.value})"
        model_str = f"[{agent.model}]" if agent.model else ""
        console.print(f"  - {agent.display_name} {mode_str} {model_str}")

    console.print(f"\n[bold]Questions ({len(config.questions.rounds)}):[/bold]")
    for i, q in enumerate(config.questions.rounds):
        console.print(f"  {i + 1}. {q[:80]}{'...' if len(q) > 80 else ''}")


async def _run_impl(config: FocusgroupConfig, output_dir: Path | None) -> None:
    """Implementation of the run command."""
    # Create the tool wrapper
    cli_tool = create_cli_tool(config.tool.command)

    # Determine output directory
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Run the session
    orchestrator = SessionOrchestrator(config, cli_tool)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        setup_task = progress.add_task("Setting up session...", total=None)
        await orchestrator.setup()
        progress.remove_task(setup_task)

        agent_count = len(orchestrator.agents)
        console.print(f"[green]✓[/green] Session initialized with {agent_count} agents\n")

        round_count = len(config.questions.rounds)
        for round_num, result in enumerate(await _collect_results(orchestrator)):
            prompt_preview = result.prompt[:60]
            console.print(f"[bold]Round {round_num + 1}/{round_count}:[/bold] {prompt_preview}...")
            for resp in result.responses:
                console.print(f"  [cyan]{resp.agent_name}[/cyan]: {len(resp.content)} chars")

    # Save the session
    session_path = orchestrator.save()
    session = orchestrator.session

    console.print("\n[green]✓[/green] Session complete")

    # Write output files if directory specified
    if output_dir:
        formatter = get_formatter(config.output.format)
        ext = "json" if config.output.format == "json" else "md"
        output_file = output_dir / f"{session.display_id}.{ext}"
        formatter.write(session, output_file)
        console.print(f"[green]✓[/green] Report saved: {output_file}")

    # Always show where session log was saved
    console.print(f"[dim]Session log: {session_path}[/dim]")

    # Print final synthesis if available
    if session.final_synthesis:
        console.print("\n[bold]Final Synthesis:[/bold]")
        console.print(session.final_synthesis)


async def _collect_results(orchestrator: SessionOrchestrator) -> list:
    """Collect all results from the orchestrator.

    Helper to iterate async generator into a list while
    allowing per-round output.
    """
    results = []
    async for result in orchestrator.run_session():
        results.append(result)
    return results


# --- Agents subcommand group ---


@agents_app.command("list")
def agents_list(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed agent information"),
    ] = False,
) -> None:
    """List available agent presets."""
    presets = list_agent_presets()

    if not presets:
        console.print("[dim]No agent presets found.[/dim]")
        console.print(f"[dim]Create presets in: {get_agents_dir()}[/dim]")
        return

    if verbose:
        for name, path in presets:
            console.print(f"\n[bold]{name}[/bold]")
            try:
                preset = load_agent_preset(path)
                console.print(f"  Provider: {preset.provider.value}")
                console.print(f"  Mode: {preset.mode.value}")
                if preset.model:
                    console.print(f"  Model: {preset.model}")
                if preset.system_prompt:
                    preview = preset.system_prompt[:60]
                    console.print(f"  System: {preview}...")
            except Exception as e:
                console.print(f"  [red]Error loading: {e}[/red]")
    else:
        table = Table(title="Agent Presets")
        table.add_column("Name", style="cyan")
        table.add_column("Provider")
        table.add_column("Mode")

        for name, path in presets:
            try:
                preset = load_agent_preset(path)
                table.add_row(name, preset.provider.value, preset.mode.value)
            except Exception:
                table.add_row(name, "[red]error[/red]", "")

        console.print(table)


@agents_app.command("show")
def agents_show(
    name: Annotated[str, typer.Argument(help="Agent preset name")],
) -> None:
    """Show details of an agent preset."""
    agents_dir = get_agents_dir()
    preset_path = agents_dir / f"{name}.toml"

    if not preset_path.exists():
        console.print(f"[red]Preset not found: {name}[/red]")
        console.print(f"[dim]Looked in: {preset_path}[/dim]")
        raise typer.Exit(1)

    try:
        preset = load_agent_preset(preset_path)
    except Exception as e:
        console.print(f"[red]Failed to load preset: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(f"\n[bold]Agent Preset: {name}[/bold]\n")
    console.print(f"Provider: [cyan]{preset.provider.value}[/cyan]")
    console.print(f"Mode: {preset.mode.value}")
    if preset.model:
        console.print(f"Model: {preset.model}")
    if preset.name:
        console.print(f"Display Name: {preset.name}")
    if preset.system_prompt:
        console.print(f"\nSystem Prompt:\n[dim]{preset.system_prompt}[/dim]")


# --- Logs subcommand group ---


@logs_app.command("list")
def logs_list(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of logs to show"),
    ] = 10,
    tool: Annotated[
        str | None,
        typer.Option("--tool", "-t", help="Filter by tool name"),
    ] = None,
) -> None:
    """List past session logs."""
    storage = get_default_storage()
    sessions = storage.list_sessions(limit=limit, tool_filter=tool)

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        if tool:
            console.print(f"[dim]Filtered by tool: {tool}[/dim]")
        return

    table = Table(title="Recent Sessions")
    table.add_column("ID", style="cyan")
    table.add_column("Tool")
    table.add_column("Mode")
    table.add_column("Agents", justify="right")
    table.add_column("Rounds", justify="right")
    table.add_column("Status")

    for session in sessions:
        status = "[green]✓[/green]" if session.is_complete else "[yellow]○[/yellow]"
        table.add_row(
            session.display_id,
            session.tool,
            session.mode,
            str(session.agent_count),
            str(len(session.rounds)),
            status,
        )

    console.print(table)


@logs_app.command("show")
def logs_show(
    session_id: Annotated[str, typer.Argument(help="Session ID to show")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json, markdown, or text"),
    ] = "text",
) -> None:
    """Show details of a past session."""
    storage = get_default_storage()

    try:
        session = storage.load(session_id)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {session_id}[/red]")
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    formatted = format_session(session, format)
    console.print(formatted)


@logs_app.command("export")
def logs_export(
    session_id: Annotated[str, typer.Argument(help="Session ID to export")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json or markdown"),
    ] = "markdown",
) -> None:
    """Export a session to a file."""
    storage = get_default_storage()

    try:
        session = storage.load(session_id)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {session_id}[/red]")
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    # Determine output path
    if output is None:
        ext = "json" if format == "json" else "md"
        output = Path(f"{session.display_id}.{ext}")

    # Get formatter and write
    try:
        formatter = get_formatter(format)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    formatter.write(session, output)
    console.print(f"[green]✓[/green] Exported to: {output}")


@logs_app.command("delete")
def logs_delete(
    session_id: Annotated[str, typer.Argument(help="Session ID to delete")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Delete without confirmation"),
    ] = False,
) -> None:
    """Delete a session log."""
    storage = get_default_storage()

    # Verify session exists first
    try:
        session = storage.load(session_id)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {session_id}[/red]")
        raise typer.Exit(1) from None

    if not force:
        confirm = typer.confirm(f"Delete session {session.display_id} ({session.tool})?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    if storage.delete(session.display_id):
        console.print(f"[green]✓[/green] Deleted: {session.display_id}")
    else:
        console.print("[red]Failed to delete session.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
