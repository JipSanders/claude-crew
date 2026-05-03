"""
Rich terminal UI for claude-crew.
Handles all display logic — the rest of the code just fires on_event() callbacks.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.table import Table
from rich import box

console = Console()

# Per-agent colours and emoji
AGENT_STYLE: dict[str, tuple[str, str]] = {
    "orchestrator": ("bold magenta", "🧠"),
    "coder":        ("bold cyan",    "💻"),
    "marketer":     ("bold magenta", "📣"),
    "designer":     ("bold yellow",  "🎨"),
    "analyst":      ("bold green",   "🔍"),
    "sales":        ("bold red",     "🤝"),
}


def _style(agent: str) -> tuple[str, str]:
    return AGENT_STYLE.get(agent, ("bold white", "🤖"))


def print_banner(goal: str) -> None:
    banner = Text()
    banner.append("  CLAUDE CREW  ", style="bold white on #1a0a2e")
    console.print()
    console.print(Panel(
        banner,
        subtitle="[dim]Orchestrated multi-agent AI team[/dim]",
        border_style="bright_magenta",
        padding=(0, 2),
    ))
    console.print()
    console.print(f"  [dim]Goal:[/dim] [bold white]{goal}[/bold white]")
    console.print()


def on_event(kind: str, agent: str, message: str) -> None:
    color, emoji = _style(agent)
    label = agent.upper()

    if kind == "orchestrator_start":
        console.print(Rule(style="dim"))
        console.print(f"  {emoji} [bold bright_magenta]ORCHESTRATOR[/bold bright_magenta]  [dim]Analysing goal...[/dim]")
        console.print()

    elif kind == "orchestrator_thinking":
        console.print(f"  {emoji} [bold bright_magenta]ORCHESTRATOR[/bold bright_magenta]  [dim]{message}[/dim]")

    elif kind == "orchestrator_done":
        console.print()
        console.print(Rule(style="dim"))

    elif kind == "start":
        console.print()
        console.print(f"  {emoji} [{color}]{label}[/{color}]  [dim]Starting task...[/dim]")

    elif kind == "file":
        console.print(f"       [dim]→ saved[/dim] [dim cyan]workspace/{message}[/dim cyan]")

    elif kind == "reddit":
        console.print(f"       [dim]→ searching Reddit:[/dim] [dim]{message[:60]}[/dim]")

    elif kind == "code":
        console.print(f"       [dim]→ running python snippet[/dim]")

    elif kind == "done":
        console.print(f"       [dim]✓[/dim] [{color}]done[/{color}]")


def print_summary(result) -> None:
    console.print()

    # Agents used table
    if result.agent_results:
        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold dim",
            border_style="dim",
            padding=(0, 2),
        )
        table.add_column("Agent", style="bold")
        table.add_column("Task")
        table.add_column("Artifacts", style="dim cyan")

        for r in result.agent_results:
            color, emoji = _style(r.agent_name)
            agent_label = Text(f"{emoji} {r.agent_name}", style=color)
            artifacts = "\n".join(Path(a).name for a in r.artifacts) or "—"
            task_short = r.task[:60] + "…" if len(r.task) > 60 else r.task
            table.add_row(agent_label, task_short, artifacts)

        console.print(Panel(table, title="[bold]Crew Summary[/bold]", border_style="bright_magenta", padding=(1, 2)))

    # Final synthesis
    if result.summary:
        console.print(Panel(
            f"[dim]{result.summary}[/dim]",
            title="[bold]Orchestrator Synthesis[/bold]",
            border_style="magenta",
            padding=(1, 2),
        ))

    # Workspace
    workspace = Path("workspace")
    if workspace.exists():
        all_files = sorted(workspace.rglob("*"))
        file_list = [f for f in all_files if f.is_file()]
        if file_list:
            console.print(
                f"\n  [dim]All artifacts saved to[/dim] [bold cyan]workspace/[/bold cyan]  "
                f"[dim]({len(file_list)} file{'s' if len(file_list) != 1 else ''})[/dim]\n"
            )
