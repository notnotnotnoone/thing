from typing import Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
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
        """Display proposal as formatted raw text with full visibility."""
        color = self.get_agent_color(agent_id)
        title = f"PROPOSAL BY {agent_id} (V{version})"
        
        # Show the raw AI response with proper formatting
        self.console.print(f"\n[bold {color}]═══════════════════════════════════════════════════════════[/bold {color}]")
        self.console.print(f"[bold {color}] {title}[/bold {color}]")
        self.console.print(f"[dim]{role}[/dim]")
        self.console.print(f"[bold {color}]═══════════════════════════════════════════════════════════[/bold {color}]")
        self.console.print(f"[white]{content}[/white]")
        self.console.print(f"[bold {color}]═══════════════════════════════════════════════════════════[/bold {color}]\n")

    def display_critique(self, agent_id: str, role: str, content: str):
        """Display critique as formatted raw text with full visibility."""
        color = self.get_agent_color(agent_id)
        self.console.print(f"\n[dim {color}]┌─ {agent_id} ({role}) Critique ────────────────────────────────[/dim {color}]")
        self.console.print(f"[white]{content}[/white]")
        self.console.print(f"[dim {color}]└────────────────────────────────────────────────────────────[/dim {color}]\n")

    def display_verdict(self, agent_id: str, role: str, content: str):
        """Display verdict as formatted raw text with full visibility."""
        self.console.print(f"\n[bold yellow]╔═══════════════════════════════════════════════════════════╗[/bold yellow]")
        self.console.print(f"[bold yellow]║ ⚖ FINAL VERDICT BY CHIEF JUSTICE                              ║[/bold yellow]")
        self.console.print(f"[bold yellow]║ {agent_id} ({role})                                           ║[/bold yellow]")
        self.console.print(f"[bold yellow]╠═══════════════════════════════════════════════════════════╣[/bold yellow]")
        self.console.print(f"[white]{content}[/white]")
        self.console.print(f"[bold yellow]╚═══════════════════════════════════════════════════════════╝[/bold yellow]\n")

    def log_action(self, action: str, details: str = ""):
        """Display a visible system log entry for full transparency."""
        msg = f"[bold cyan][SYSTEM][/bold cyan] [white]{action}[/white]"
        if details:
            msg += f": [yellow]{details}[/yellow]"
        self.console.print(msg)

    def display_odds(self, bookie_role: str, odds_data: Dict[str, str], raw_response: str):
        """Display odds response as formatted raw text with full visibility."""
        self.console.print(f"\n[bold yellow]┌─ BETTING ANALYSIS BY {bookie_role} ────────────────────────────────[/bold yellow]")
        self.console.print(f"[white]{raw_response}[/white]")
        self.console.print(f"[bold yellow]└────────────────────────────────────────────────────────────┘[/bold yellow]\n")
        
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
        
        if sorted_props and sorted_props[0].answer_v2:
            winner = sorted_props[0]
            self.console.print(f"\n[bold gold3]╔═══════════════════════════════════════════════════════════╗[/bold gold3]")
            self.console.print(f"[bold gold3]║ 👑 CHAMPION MASTERPIECE 👑                                    ║[/bold gold3]")
            self.console.print(f"[bold gold3]║ {winner.id} ({winner.role}) - Score: {winner.score}                          ║[/bold gold3]")
            self.console.print(f"[bold gold3]╠═══════════════════════════════════════════════════════════╣[/bold gold3]")
            self.console.print(f"[white]{winner.answer_v2}[/white]")
            self.console.print(f"[bold gold3]╚═══════════════════════════════════════════════════════════╝[/bold gold3]\n")
