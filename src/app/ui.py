from typing import Any
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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
        # Ensure no truncation: overflow="fold" and crop=False
        self.console.print(content, style="white", markup=False, soft_wrap=True)
        self.console.print(f"[bold {color}]═══════════════════════════════════════════════════════════[/bold {color}]\n")

    def display_critique(self, agent_id: str, role: str, content: str):
        """Display critique as formatted raw text with full visibility."""
        color = self.get_agent_color(agent_id)
        self.console.print(f"\n[dim {color}]┌─ {agent_id} ({role}) Critique ────────────────────────────────[/dim {color}]")
        self.console.print(content, style="white", markup=False, soft_wrap=True)
        self.console.print(f"[dim {color}]└────────────────────────────────────────────────────────────[/dim {color}]\n")

    def display_verdict(self, agent_id: str, role: str, content: str):
        """Display verdict as formatted raw text with full visibility."""
        self.console.print("\n[bold yellow]╔═══════════════════════════════════════════════════════════╗[/bold yellow]")
        self.console.print("[bold yellow]║ ⚖ FINAL VERDICT BY CHIEF JUSTICE                              ║[/bold yellow]")
        self.console.print(f"[bold yellow]║ {agent_id} ({role})                                           ║[/bold yellow]")
        self.console.print("[bold yellow]╠═══════════════════════════════════════════════════════════╣[/bold yellow]")
        self.console.print(content, style="white", markup=False, soft_wrap=True)
        self.console.print("[bold yellow]╚═══════════════════════════════════════════════════════════╝[/bold yellow]\n")

    def log_action(self, action: str, details: str = ""):
        """Display a visible system log entry for full transparency."""
        msg = f"[bold cyan][SYSTEM][/bold cyan] [white]{action}[/white]"
        if details:
            msg += f": [yellow]{details}[/yellow]"
        self.console.print(msg)

    def log_payload(self, title: str, data: Any):
        """Display raw JSON-like data with syntax highlighting for wire-level transparency."""
        from rich.syntax import Syntax
        import json
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        # Using a higher line limit or ensuring it expands
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True, word_wrap=True)
        
        panel = Panel(
            syntax,
            title=f"[bold magenta]{title}[/bold magenta]",
            border_style="magenta",
            padding=(0, 1),
            expand=True
        )
        self.console.print(panel)

    def display_system_state(self, router: Any):
        """Display the internal sliding window state for all models with 'Requests Left' bars."""
        from rich.progress import ProgressBar
        from rich.columns import Columns
        
        table = Table(title="[bold cyan]MODEL-LEVEL QUOTAS (GLASS BOX)[/]", box=box.ROUNDED, expand=True)
        table.add_column("Provider:Model", style="magenta")
        table.add_column("RPM Usage", justify="right")
        table.add_column("Available Capacity", justify="center", width=30)
        table.add_column("Remaining", justify="right")
        
        providers = router.providers
        provider_stats = {} # p_name -> {used, limit}
        
        for p_name, p_data in providers.items():
            p_limit = p_data.get("rate_limit", 0)
            p_used = 0
            
            for tier, models in p_data["models"].items():
                for model_cfg in models:
                    m_name = model_cfg["name"]
                    m_limit = model_cfg["rpm"]
                    m_id = f"{p_name}:{m_name}"
                    
                    window = router.engine.model_windows.get(m_id)
                    rpm, _ = window.get_usage() if window else (0, 0)
                    p_used += rpm
                    
                    # Calculate remaining
                    remaining = max(0, m_limit - rpm)
                    
                    # Create a progress bar for "Requests Left"
                    if m_limit > 0:
                        bar = ProgressBar(total=m_limit, completed=remaining, width=30)
                        rem_str = f"[bold green]{int(remaining)}[/]/[dim]{int(m_limit)}[/]"
                    else:
                        bar = "[dim]Unlimited[/dim]"
                        rem_str = "∞"
                        
                    table.add_row(m_id, str(rpm), bar, rem_str)
            
            provider_stats[p_name] = {"used": p_used, "limit": p_limit}
            
        self.console.print(table)
        
        # Provider Aggregate Dashboard
        dash = Table(title="[bold yellow]PROVIDER AGGREGATE LOAD[/]", box=box.SIMPLE, expand=True)
        dash.add_column("Provider", style="yellow")
        dash.add_column("Total Active Requests", justify="right")
        dash.add_column("Load Bar", justify="center", width=40)
        
        for p_name, stats in provider_stats.items():
            u, l = stats["used"], stats["limit"]
            # Even if we don't strictly enforce provider-wide RPM anymore, it's good for viz
            # We'll use the provider's base rate_limit as the visual reference
            if l > 0:
                bar = ProgressBar(total=l, completed=max(0, l - u), width=40)
            else:
                bar = "[dim]No Limit Set[/dim]"
            dash.add_row(p_name, str(u), bar)
            
        self.console.print(dash)

    def display_odds(self, bookie_role: str, odds_data: dict[str, str], raw_response: str):
        """Display odds response as formatted raw text with full visibility."""
        self.console.print(f"\n[bold yellow]┌─ BETTING ANALYSIS BY {bookie_role} ────────────────────────────────[/bold yellow]")
        self.console.print(f"[white]{raw_response}[/white]")
        self.console.print("[bold yellow]└────────────────────────────────────────────────────────────┘[/bold yellow]\n")

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
            self.console.print("\n[bold gold3]╔═══════════════════════════════════════════════════════════╗[/bold gold3]")
            self.console.print("[bold gold3]║ 👑 CHAMPION MASTERPIECE 👑                                    ║[/bold gold3]")
            self.console.print(f"[bold gold3]║ {winner.id} ({winner.role}) - Score: {winner.score}                          ║[/bold gold3]")
            self.console.print("[bold gold3]╠═══════════════════════════════════════════════════════════╣[/bold gold3]")
            self.console.print(f"[white]{winner.answer_v2}[/white]")
            self.console.print("[bold gold3]╚═══════════════════════════════════════════════════════════╝[/bold gold3]\n")
