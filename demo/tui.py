"""Rich-powered TUI components for the BSides demo.

All layout, panel, and banner builders live here so logging.py stays clean.
Import this module only when ui_mode=True — it requires `rich`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# -----------------------------------------------------------------------
# Agent list — must match the order they run in runner.py
# -----------------------------------------------------------------------

AGENT_NAMES: List[str] = [
    "WebFixtureAgent",
    "SummarizerAgent",
    "MemoryWriterAgent",
    "MemoryRetrieverAgent",
    "PolicyGateAgent",
    "PlannerAgent",
    "ExecutorAgent",
    "ForensicsAgent",
]

# -----------------------------------------------------------------------
# State dataclasses
# -----------------------------------------------------------------------


@dataclass
class AgentState:
    name: str
    # pending / running / done / attacked / blocked
    status: str = "pending"
    trust: str = "untrusted"
    message: str = ""


@dataclass
class AttackState:
    mode: str
    fixture: str
    current_step: int = 0
    total_steps: int = 8
    attack_succeeded: bool = False
    obfuscation_method: Optional[str] = None


# -----------------------------------------------------------------------
# Style maps
# -----------------------------------------------------------------------

_STATUS_ICONS = {
    "pending": "○",
    "running": "▶",
    "done": "✓",
    "attacked": "⚡",
    "blocked": "✓",
}

_STATUS_STYLES = {
    "pending": "dim",
    "running": "bold cyan",
    "done": "green",
    "attacked": "bold red",
    "blocked": "bold green",
}

_TRUST_STYLES = {
    "trusted": "green",
    "untrusted": "yellow",
}

# -----------------------------------------------------------------------
# ASCII art for the finale banners
# -----------------------------------------------------------------------

_PWNED_ART = r"""
██████╗ ██╗    ██╗███╗   ██╗███████╗██████╗
██╔══██╗██║    ██║████╗  ██║██╔════╝██╔══██╗
██████╔╝██║ █╗ ██║██╔██╗ ██║█████╗  ██║  ██║
██╔═══╝ ██║███╗██║██║╚██╗██║██╔══╝  ██║  ██║
██║     ╚███╔███╔╝██║ ╚████║███████╗██████╔╝
╚═╝      ╚══╝╚══╝ ╚═╝  ╚═══╝╚══════╝╚═════╝ """.strip()

_BLOCKED_ART = r"""
██████╗ ██╗      ██████╗  ██████╗██╗  ██╗███████╗██████╗
██╔══██╗██║     ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
██████╔╝██║     ██║   ██║██║     █████╔╝ █████╗  ██║  ██║
██╔══██╗██║     ██║   ██║██║     ██╔═██╗ ██╔══╝  ██║  ██║
██████╔╝███████╗╚██████╔╝╚██████╗██║  ██╗███████╗██████╔╝
╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ """.strip()

# -----------------------------------------------------------------------
# Panel builders
# -----------------------------------------------------------------------


def build_agent_chain_panel(states: List[AgentState]) -> Panel:
    """Render the 8-agent pipeline as a vertical chain with trust badges."""
    grid = Table.grid(padding=(0, 1))
    grid.add_column(justify="center", width=2)   # icon
    grid.add_column(min_width=22)                 # name
    grid.add_column(min_width=12)                 # trust badge
    grid.add_column()                             # message

    for i, state in enumerate(states):
        icon = _STATUS_ICONS.get(state.status, "○")
        s_style = _STATUS_STYLES.get(state.status, "dim")
        t_style = _TRUST_STYLES.get(state.trust, "white")

        grid.add_row(
            Text(icon, style=s_style),
            Text(state.name, style=s_style),
            Text(f"[{state.trust}]", style=t_style),
            Text(state.message[:38] if state.message else "", style="dim"),
        )
        # Separator arrow (skip after last agent)
        if i < len(states) - 1:
            grid.add_row(
                Text("↓", style="dim"),
                Text(""),
                Text(""),
                Text(""),
            )

    return Panel(grid, title="[bold blue]Agent Pipeline[/bold blue]", border_style="blue")


def build_output_panel(lines: List[str], max_lines: int = 30) -> Panel:
    """Render the last N output lines in a scrolling panel."""
    visible = lines[-max_lines:] if len(lines) > max_lines else lines
    text = Text()
    for line in visible:
        # Colour-code by keywords in the line
        if "[trusted]" in line or "trusted" in line.lower():
            text.append(line + "\n", style="green")
        elif "PWNED" in line or "pwned" in line or "WRITE_PWNED" in line:
            text.append(line + "\n", style="bold red")
        elif "BLOCKED" in line or "blocked" in line or "rejected" in line:
            text.append(line + "\n", style="bold green")
        elif "[untrusted]" in line or "untrusted" in line.lower():
            text.append(line + "\n", style="yellow")
        else:
            text.append(line + "\n", style="white")
    return Panel(text, title="[bold cyan]Live Output[/bold cyan]", border_style="cyan")


def build_status_bar(state: AttackState) -> Text:
    """One-line status strip shown at the top of the layout."""
    text = Text()
    mode_style = "bold red" if state.mode == "vulnerable" else "bold green"
    text.append(" Mode: ", style="bold")
    text.append(state.mode.upper(), style=mode_style)
    text.append("  │  ", style="dim")
    text.append("Fixture: ", style="bold")
    text.append(state.fixture or "—")
    text.append("  │  ", style="dim")
    text.append("Step: ", style="bold")
    text.append(f"{state.current_step}/{state.total_steps}")
    if state.obfuscation_method:
        text.append("  │  ", style="dim")
        text.append("Obfuscation: ", style="bold")
        text.append(state.obfuscation_method, style="yellow")
    if state.attack_succeeded:
        text.append("  │  ", style="dim")
        text.append("⚡ ATTACK SUCCEEDED", style="bold red")
    return text


def build_layout(
    agent_states: List[AgentState],
    output_lines: List[str],
    attack_state: AttackState,
) -> Layout:
    """Build the full two-column TUI layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="chain", ratio=3),
        Layout(name="output", ratio=7),
    )
    layout["header"].update(Panel(build_status_bar(attack_state), border_style="dim"))
    layout["chain"].update(build_agent_chain_panel(agent_states))
    layout["output"].update(build_output_panel(output_lines))
    return layout


# -----------------------------------------------------------------------
# Finale banners
# -----------------------------------------------------------------------


def render_pwned_banner(target: str = "", obf_method: Optional[str] = None) -> Panel:
    """Full-screen red PWNED banner for the attack-succeeded moment."""
    text = Text()
    text.append(_PWNED_ART + "\n", style="bold red")
    text.append("\n")
    text.append("  SIMULATED RCE — ATTACKER TOKEN EXECUTED  (ZERO-CLICK)\n", style="bold red")
    text.append("\n")
    if target:
        text.append(f"  Target   : {target}\n", style="yellow")
    if obf_method and obf_method not in ("none", "plaintext", None):
        text.append(f"  Technique: {obf_method} obfuscation\n", style="yellow")
    text.append("\n")
    text.append("  THIS IS A SAFE DEMO. No real commands were executed.\n", style="dim")
    return Panel(
        text,
        title="[bold red]  ATTACK SUCCEEDED  [/bold red]",
        border_style="red",
        padding=(1, 4),
    )


def render_blocked_banner(reasons: Optional[List[str]] = None) -> Panel:
    """Full-screen green BLOCKED banner for the defense-succeeded moment."""
    text = Text()
    text.append(_BLOCKED_ART + "\n", style="bold green")
    text.append("\n")
    text.append("  DEFENSE LAYER ACTIVATED — ATTACK STOPPED\n", style="bold green")
    text.append("\n")
    if reasons:
        for reason in reasons:
            text.append(f"  • {reason}\n", style="green")
    return Panel(
        text,
        title="[bold green]  ATTACK BLOCKED  [/bold green]",
        border_style="green",
        padding=(1, 4),
    )
