from typing import Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import box

console = Console()

class UI:
    def __init__(self):
        self.console = console

    def print_banner(self, text: str):
        self.console.print(Panel(f"[bold red]{text}[/bold red]", box=box.DOUBLE))

    def print_rule(self, text: str, color: str = "cyan"):
        self.console.rule(f"[bold {color}]{text}", style=color)

    def get_agent_color(self, agent_id: str) -> str:
        colors = ["cyan", "magenta", "yellow", "green", "blue", "red", "bright_blue", "bright_magenta"]
        idx = sum(ord(c) for c in agent_id) % len(colors)
        return colors[idx]

    def display_proposal(self, agent_id: str, role: str, content: str, version: int = 1):
        color = self.get_agent_color(agent_id)
        title = f"PROPOSAL BY {agent_id} (V{version})"
        self.console.print(Panel(
            Markdown(content),
            title=f"[bold {color}]{title}[/]",
            subtitle=f"[dim]{role}[/]",
            border_style=color,
            box=box.ROUNDED,
            padding=(1, 2)
        ))

    def display_critique(self, agent_id: str, role: str, content: str):
        color = self.get_agent_color(agent_id)
        self.console.print(Panel(
            Markdown(content),
            title=f"[dim {color}]{agent_id} ({role}) Critique[/dim {color}]",
            border_style=f"dim {color}",
            box=box.SIMPLE,
            padding=(0, 2)
        ))

    def display_verdict(self, agent_id: str, role: str, content: str):
        self.console.print(Panel(
            Markdown(content),
            title="[bold yellow]⚖ FINAL VERDICT BY CHIEF JUSTICE[/bold yellow]",
            subtitle=f"[dim yellow]{agent_id} ({role})[/dim yellow]",
            border_style="yellow",
            box=box.DOUBLE,
            padding=(1, 2)
        ))

    def log_action(self, action: str, details: str = ""):
        """Display a subtle system log entry for transparency."""
        msg = f"[dim cyan][SYSTEM][/][dim] {action}[/]"
        if details:
            msg += f": [italic]{details}[/]"
        self.console.print(msg)

    def display_odds(self, bookie_role: str, odds_data: Dict[str, str], raw_response: str):
        self.console.print(Panel(
            Markdown(raw_response),
            title=f"[bold yellow]BETTING ANALYSIS BY {bookie_role}[/]",
            border_style="yellow",
            box=box.ROUNDED
        ))
        table = Table(title="[bold yellow]CURRENT ODDS[/]", box=box.SIMPLE, expand=False)
        table.add_column("Agent", style="cyan")
        table.add_column("Odds", style="green")
        for agent, val in odds_data.items():
            table.add_row(agent, val)
        self.console.print(table)

    def safe_input(self, prompt: str) -> str:
        return self.console.input(f"\n[bold red]{prompt}:[/bold red] ")

    def display_leaderboard(self, proposals: list):
        self.print_rule("FINAL LEADERBOARD", "yellow")
        sorted_props = sorted(proposals, key=lambda x: x.score, reverse=True)
        table = Table(show_header=True, header_style="bold gold3", box=box.MINIMAL, expand=True)
        table.add_column("Rank")
        table.add_column("Agent")
        table.add_column("Role")
        table.add_column("Score")
        for i, p in enumerate(sorted_props[:10]):
            table.add_row(f"#{i+1}", p.id, p.role, str(p.score))
        self.console.print(table)
        
        winner = sorted_props[0]
        self.console.print(Panel(Markdown(winner.answer_v2), title="👑 CHAMPION MASTERPIECE 👑", border_style="gold3"))
