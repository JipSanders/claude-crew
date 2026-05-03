#!/usr/bin/env python3
"""
claude-crew: An orchestrated team of specialist AI agents.

Usage:
  python crew.py "Launch my product on Product Hunt"
  python crew.py "Build a REST API for a todo app" --allow-code
  python crew.py --list-agents
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from rich.console import Console
    from src.orchestrator import Orchestrator
    from src import display
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

console = Console()


def list_agents() -> None:
    from src.agents import REGISTRY
    console.print()
    console.print("  [bold]Available agents:[/bold]\n")
    for name, cls in REGISTRY.items():
        color, emoji = display.AGENT_STYLE.get(name, ("white", "🤖"))
        console.print(f"  {emoji} [{color}]{name:<12}[/{color}]  [dim]{cls.description}[/dim]")
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="claude-crew: An orchestrated team of specialist AI agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python crew.py "Write a launch strategy and landing page for my app"
  python crew.py "Build a Python web scraper and marketing copy for the tool"
  python crew.py "Analyse the competitive landscape for productivity apps"
  python crew.py --list-agents
        """,
    )
    parser.add_argument(
        "goal",
        nargs="?",
        help="The goal for the crew to accomplish",
    )
    parser.add_argument(
        "--allow-code",
        action="store_true",
        help="Allow the coder agent to execute Python code (off by default)",
    )
    parser.add_argument(
        "--workspace",
        default="workspace",
        help="Directory for agent artifacts (default: workspace/)",
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available specialist agents and exit",
    )
    args = parser.parse_args()

    if args.list_agents:
        list_agents()
        return

    if not args.goal:
        parser.print_help()
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("\n  [bold red]Error:[/bold red] ANTHROPIC_API_KEY environment variable not set.")
        console.print("  [dim]Export it: export ANTHROPIC_API_KEY=sk-ant-...[/dim]\n")
        sys.exit(1)

    workspace = Path(args.workspace)
    display.print_banner(args.goal)

    try:
        orchestrator = Orchestrator(
            workspace=workspace,
            on_event=display.on_event,
            allow_code_execution=args.allow_code,
        )
        result = orchestrator.run(args.goal)
        display.print_summary(result)

    except KeyboardInterrupt:
        console.print("\n\n  [dim]Interrupted.[/dim]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n  [bold red]Error:[/bold red] {e}\n")
        raise


if __name__ == "__main__":
    main()
