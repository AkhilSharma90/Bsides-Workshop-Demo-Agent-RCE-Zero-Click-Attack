"""Rich-powered TUI components for the BSides demo.

All layout, panel, and banner builders live here so logging.py stays clean.
Import this module only when ui_mode=True — it requires `rich`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
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
    started_at: Optional[float] = None  # time.monotonic() when set to running


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


def build_progress_panel(states: List[AgentState], attack_state: AttackState) -> Panel:
    """Render a progress bar with current agent, elapsed time, and pipeline status."""
    total = len(states)
    done_count = sum(1 for s in states if s.status in ("done", "attacked", "blocked"))
    running = next((s for s in states if s.status == "running"), None)

    # Fraction complete: running agent counts as half-done
    completed = done_count + (0.5 if running else 0)
    pct = completed / total if total else 0.0

    # Build bar manually so it works inside a Panel without a Progress context
    bar_width = 40
    filled = int(pct * bar_width)
    bar_char_filled = "█"
    bar_char_empty = "░"
    bar_str = bar_char_filled * filled + bar_char_empty * (bar_width - filled)
    pct_label = f"{int(pct * 100):3d}%"

    text = Text()

    # Progress bar row
    bar_style = "bold red" if attack_state.attack_succeeded else "bold cyan"
    text.append(f" {pct_label}  ", style="bold")
    text.append(bar_str, style=bar_style)
    text.append(f"  {done_count}/{total} agents", style="dim")

    # Current agent thinking indicator
    if running:
        elapsed = time.monotonic() - running.started_at if running.started_at else 0.0
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinner_frames[int(elapsed * 10) % len(spinner_frames)]
        text.append("\n")
        text.append(f" {spinner} ", style="bold cyan")
        text.append(f"{running.name}", style="bold cyan")
        text.append("  thinking…", style="dim cyan")
        text.append(f"  ({elapsed:.1f}s)", style="dim")
    elif done_count == total:
        text.append("\n")
        text.append("  Pipeline complete", style="bold green")

    return Panel(text, title="[bold yellow]Execution Progress[/bold yellow]", border_style="yellow", padding=(0, 1))


def build_output_panel(lines: List[str], max_lines: int = 28) -> Panel:
    """Render the last N output lines in a scrolling panel with icons and better formatting."""
    visible = lines[-max_lines:] if len(lines) > max_lines else lines
    text = Text()
    for line in visible:
        # Detect event type and pick icon + style
        if "PWNED" in line or "pwned" in line or "WRITE_PWNED" in line:
            icon = "⚡"
            style = "bold red"
        elif "BLOCKED" in line or "ATTACK BLOCKED" in line:
            icon = "🛡"
            style = "bold green"
        elif "rejected" in line.lower() or "denied" in line.lower() or "DENY" in line:
            icon = "✗"
            style = "bold yellow"
        elif "POLICY" in line or "policy" in line.lower():
            icon = "🛡"
            style = "green"
        elif "[trusted]" in line:
            icon = "✓"
            style = "green"
        elif "[untrusted]" in line:
            icon = "⚠"
            style = "yellow"
        elif "[LLM]" in line or "thinking" in line.lower() or "calling" in line.lower():
            icon = "◌"
            style = "dim cyan"
        elif line.startswith("==="):
            icon = "»"
            style = "bold magenta"
        else:
            icon = "·"
            style = "white"

        text.append(f" {icon} ", style=style)
        text.append(line + "\n", style=style)

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
        Layout(name="progress", size=5),
        Layout(name="body"),
    )
    layout["body"].split_row(
        Layout(name="chain", ratio=3),
        Layout(name="output", ratio=7),
    )
    layout["header"].update(Panel(build_status_bar(attack_state), border_style="dim"))
    layout["progress"].update(build_progress_panel(agent_states, attack_state))
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
