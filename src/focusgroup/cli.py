"""CLI interface for focusgroup."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from focusgroup import __version__

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
    tool: Annotated[str, typer.Argument(help="Tool command to get feedback on (e.g., 'mx')")],
    question: Annotated[str, typer.Argument(help="Question to ask the agent panel")],
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
) -> None:
    """Quick ad-hoc query to an agent panel about a tool."""
    console.print(f"[dim]Asking {agents} agents about [bold]{tool}[/bold]...[/dim]")
    console.print(f"[dim]Question: {question}[/dim]")
    # TODO: Implement actual agent queries
    console.print("[yellow]Not yet implemented[/yellow]")


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
) -> None:
    """Run a full feedback session from a config file."""
    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Loading session config from [bold]{config_file}[/bold]...[/dim]")

    if dry_run:
        console.print("[yellow]Dry run mode - not executing[/yellow]")
        # TODO: Show session plan
    else:
        # TODO: Run session
        console.print("[yellow]Not yet implemented[/yellow]")


# --- Agents subcommand group ---


@agents_app.command("list")
def agents_list(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed agent information"),
    ] = False,
) -> None:
    """List available agent presets."""
    console.print("[dim]Available agent presets:[/dim]")
    # TODO: List from config directory
    console.print("[yellow]Not yet implemented[/yellow]")


@agents_app.command("show")
def agents_show(
    name: Annotated[str, typer.Argument(help="Agent preset name")],
) -> None:
    """Show details of an agent preset."""
    console.print(f"[dim]Agent preset: {name}[/dim]")
    # TODO: Show preset details
    console.print("[yellow]Not yet implemented[/yellow]")


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
    console.print(f"[dim]Recent sessions (limit: {limit}):[/dim]")
    # TODO: List from storage
    console.print("[yellow]Not yet implemented[/yellow]")


@logs_app.command("show")
def logs_show(
    session_id: Annotated[str, typer.Argument(help="Session ID to show")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json, markdown, or text"),
    ] = "text",
) -> None:
    """Show details of a past session."""
    console.print(f"[dim]Session: {session_id}[/dim]")
    # TODO: Load and display session
    console.print("[yellow]Not yet implemented[/yellow]")


@logs_app.command("export")
def logs_export(
    session_id: Annotated[str, typer.Argument(help="Session ID to export")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output file path"),
    ] = Path("session-export.md"),
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: json or markdown"),
    ] = "markdown",
) -> None:
    """Export a session to a file."""
    console.print(f"[dim]Exporting session {session_id} to {output}...[/dim]")
    # TODO: Export session
    console.print("[yellow]Not yet implemented[/yellow]")


if __name__ == "__main__":
    app()
