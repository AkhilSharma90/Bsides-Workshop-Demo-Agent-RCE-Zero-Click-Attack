#!/usr/bin/env python3
"""
SPECTER — AI Agent Memory Poisoning & Zero-Click RCE Simulator
Interactive CLI for BSides Workshop
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

try:
    import questionary
    from questionary import Choice, Style as QStyle

    HAS_Q = True
except ImportError:
    HAS_Q = False

console = Console()
REPO_ROOT = Path(__file__).parent.parent

# ──────────────────────────────────────────────────────────────────────────────
# Questionary theme
# ──────────────────────────────────────────────────────────────────────────────

SPECTER_STYLE = None
if HAS_Q:
    SPECTER_STYLE = QStyle(
        [
            ("qmark", "fg:#ff3333 bold"),
            ("question", "bold"),
            ("answer", "fg:#ff3333 bold"),
            ("pointer", "fg:#ff3333 bold"),
            ("highlighted", "fg:#ff3333 bold"),
            ("selected", "fg:#cc0000"),
            ("separator", "fg:#666666"),
            ("instruction", "fg:#888888 italic"),
            ("text", ""),
            ("disabled", "fg:#888888 italic"),
        ]
    )

# ──────────────────────────────────────────────────────────────────────────────
# Fixture catalogue  (name → one-line description)
# ──────────────────────────────────────────────────────────────────────────────

FIXTURES: dict[str, str] = {
    "poisoned":                    "Plaintext injection — classic memory poisoning",
    "base64":                      "Base64-encoded payload — bypasses naive keyword filters",
    "homoglyph":                   "Homoglyph substitution — visually identical Unicode tricks",
    "bidi":                        "Bidirectional text — hidden payload via Unicode RTL/LTR",
    "steganography":               "Zero-width steganography — invisible to humans",
    "latent":                      "Latent trigger — sleeps until a specific query phrase fires it",
    "markdown_table":              "Markdown table injection — hidden in a table cell",
    "yaml":                        "YAML front-matter injection — hidden in document metadata",
    "toolshaping":                 "Tool-shaping attack — redefines what a tool does",
    "canary":                      "Canary exfiltration — data leak via DNS canary beacon",
    "confused_deputy":             "Confused deputy — exploits SSRF-like trust mis-delegation",
    "supply_chain":                "Supply chain poisoning — injected via upstream dependency",
    "rag_poisoned":                "RAG poisoning — injects into retrieval-augmented memory",
    "rag_ambiguity":               "RAG ambiguity — two near-identical entries, wrong one wins",
    "scenarios/github_pr_comment": "Real-world: GitHub PR comment injection",
    "scenarios/confluence_runbook":"Real-world: Confluence runbook poisoning",
    "scenarios/npm_readme":        "Real-world: npm README supply-chain attack",
    "scenarios/slack_alert":       "Real-world: Slack monitoring alert poisoning",
}

# ──────────────────────────────────────────────────────────────────────────────
# Banner
# ──────────────────────────────────────────────────────────────────────────────

_SPECTER_ASCII = """\
  ███████╗██████╗ ███████╗ ██████╗████████╗███████╗██████╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗
  ███████╗██████╔╝█████╗  ██║        ██║   █████╗  ██████╔╝
  ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══╝  ██╔══██╗
  ███████║██║     ███████╗╚██████╗   ██║   ███████╗██║  ██║
  ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝"""


def show_banner() -> None:
    art = Text(_SPECTER_ASCII + "\n", style="bold red")
    art.append("  AI Agent Memory Poisoning & Zero-Click RCE Simulator\n", style="white")
    art.append("  BSides Workshop  ·  Prompt Injection in Agentic Systems", style="dim")
    console.print()
    console.print(Panel(art, border_style="red", padding=(0, 2)))
    console.print()


def _section(title: str) -> None:
    console.print(Rule(f"[bold red]{title}[/]", style="red dim"))
    console.print()


# ──────────────────────────────────────────────────────────────────────────────
# Guard: ensure questionary is present
# ──────────────────────────────────────────────────────────────────────────────

def _require_q() -> bool:
    if not HAS_Q:
        console.print(
            Panel(
                "[yellow]questionary[/] is not installed.\n\n"
                "Run:  [bold]pip install questionary[/]\n"
                "Then restart specter.",
                title="[red]Missing dependency[/]",
                border_style="red",
            )
        )
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Run a demo subprocess
# ──────────────────────────────────────────────────────────────────────────────

def _run(args: list[str]) -> None:
    """Invoke  python -m demo  with the given args from the repo root."""
    cmd = [sys.executable, "-m", "demo"] + args
    console.print()
    console.print(
        Panel(
            "[dim]$ [/]" + " ".join(cmd),
            title="[bold]Launching[/]",
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()
    try:
        subprocess.run(cmd, cwd=str(REPO_ROOT))
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/]")


# ──────────────────────────────────────────────────────────────────────────────
# Fixture chooser — rendered as a rich table before prompting
# ──────────────────────────────────────────────────────────────────────────────

def _show_fixture_table(category: str = "all") -> None:
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold red")
    t.add_column("#", style="dim", width=3)
    t.add_column("Fixture", style="bold cyan", min_width=28)
    t.add_column("Description", style="white")

    entries = list(FIXTURES.items())
    if category == "obfuscation":
        entries = [(k, v) for k, v in entries if k in ("base64", "homoglyph", "bidi", "steganography", "markdown_table", "yaml")]
    elif category == "rag":
        entries = [(k, v) for k, v in entries if k.startswith("rag")]
    elif category == "scenario":
        entries = [(k, v) for k, v in entries if k.startswith("scenarios/")]

    for i, (name, desc) in enumerate(entries, 1):
        t.add_row(str(i), name, desc)
    console.print(t)


def _choose_fixture(category: str = "all") -> Optional[str]:
    _show_fixture_table(category)
    entries = list(FIXTURES.items())
    if category == "obfuscation":
        entries = [(k, v) for k, v in entries if k in ("base64", "homoglyph", "bidi", "steganography", "markdown_table", "yaml")]
    elif category == "rag":
        entries = [(k, v) for k, v in entries if k.startswith("rag")]
    elif category == "scenario":
        entries = [(k, v) for k, v in entries if k.startswith("scenarios/")]

    choices = [
        Choice(title=f"{name:<28}  {desc[:55]}", value=name)
        for name, desc in entries
    ]
    return questionary.select(
        "Choose a fixture:",
        choices=choices,
        style=SPECTER_STYLE,
    ).ask()


# ──────────────────────────────────────────────────────────────────────────────
# Wizard: Run Attack Demo
# ──────────────────────────────────────────────────────────────────────────────

def wizard_run() -> None:
    if not _require_q():
        return
    _section("Run Attack Demo")

    # ── Mode ──────────────────────────────────────────────────────────────────
    mode = questionary.select(
        "Attack mode:",
        choices=[
            Choice(
                title="🔴  Vulnerable  — attack succeeds, pwned.txt written",
                value="vulnerable",
            ),
            Choice(
                title="🛡️   Defended    — defenses block the attack",
                value="defended",
            ),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if mode is None:
        return

    # ── Fixture category ──────────────────────────────────────────────────────
    cat = questionary.select(
        "Fixture category:",
        choices=[
            Choice(title="All fixtures", value="all"),
            Choice(title="Obfuscation variants  (base64, homoglyph, bidi, steganography…)", value="obfuscation"),
            Choice(title="RAG / retrieval attacks", value="rag"),
            Choice(title="Real-world scenarios  (GitHub, Confluence, npm, Slack)", value="scenario"),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if cat is None:
        return

    fixture = _choose_fixture(cat)
    if fixture is None:
        return

    # ── Latent trigger query (special case) ───────────────────────────────────
    query: Optional[str] = None
    if fixture == "latent":
        trigger = questionary.select(
            "Latent trigger — which query?",
            choices=[
                Choice(title="diagnostics procedure         (trigger NOT fired — safe run)", value="diagnostics procedure"),
                Choice(title="emergency diagnostics procedure  (trigger FIRES — attack executes)", value="emergency diagnostics procedure"),
            ],
            style=SPECTER_STYLE,
        ).ask()
        query = trigger

    # ── UI ────────────────────────────────────────────────────────────────────
    use_ui = questionary.confirm(
        "Enable animated TUI?  (recommended for live demos)",
        default=True,
        style=SPECTER_STYLE,
    ).ask()
    if use_ui is None:
        return

    # ── Pace ──────────────────────────────────────────────────────────────────
    pace = questionary.select(
        "Pace between steps:",
        choices=[
            Choice(title="Instant      — no pauses", value="0"),
            Choice(title="Cinematic    — 0.3 s  (recommended)", value="0.3"),
            Choice(title="Slow         — 1.0 s  (great for explaining)", value="1.0"),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if pace is None:
        return

    # ── Advanced ──────────────────────────────────────────────────────────────
    advanced = questionary.confirm(
        "Configure advanced options?  (execution mode, memory backend, approval gate…)",
        default=False,
        style=SPECTER_STYLE,
    ).ask()

    execution = "mock-realistic"
    memory = "jsonl"
    approval = "none"
    capture_llm = False
    isolation = False

    if advanced:
        execution = questionary.select(
            "Tool execution mode:",
            choices=[
                Choice(title="mock-realistic  — fake-but-plausible command output (default)", value="mock-realistic"),
                Choice(title="simulated       — writes pwned.txt only, no fake outputs", value="simulated"),
                Choice(title="sandboxed       — runs commands in Docker (requires Docker)", value="sandboxed"),
            ],
            style=SPECTER_STYLE,
        ).ask() or "mock-realistic"

        memory = questionary.select(
            "Memory backend:",
            choices=[
                Choice(title="jsonl   — simple file-based (default)", value="jsonl"),
                Choice(title="sqlite  — SQLite database", value="sqlite"),
                Choice(title="rag     — vector-store retrieval", value="rag"),
            ],
            style=SPECTER_STYLE,
        ).ask() or "jsonl"

        approval = questionary.select(
            "Human approval gate before tool execution:",
            choices=[
                Choice(title="none           — bypass gate entirely (default)", value="none"),
                Choice(title="interactive    — prompt in terminal before each execution", value="interactive"),
                Choice(title="auto-deny      — always block (shows gate is working)", value="auto-deny"),
                Choice(title="auto-approve   — always allow (same as none but gate runs)", value="auto-approve"),
            ],
            style=SPECTER_STYLE,
        ).ask() or "none"

        capture_llm = questionary.confirm(
            "Capture all LLM prompts/responses to llm_calls.jsonl?",
            default=False,
            style=SPECTER_STYLE,
        ).ask() or False

        if mode == "defended":
            isolation = questionary.confirm(
                "Enable model isolation? (strips instructions before summarizer & planner)",
                default=False,
                style=SPECTER_STYLE,
            ).ask() or False

    # ── Build command ─────────────────────────────────────────────────────────
    args = [
        "run",
        "--mode", mode,
        "--fixture", fixture,
        "--execution", execution,
        "--memory", memory,
        "--pace", pace,
        "--approval", approval,
    ]
    if use_ui:
        args.append("--ui")
    if capture_llm:
        args.append("--capture-llm")
    if isolation:
        args.append("--isolation")
    if query:
        args += ["--query", query]

    _run(args)

    # ── Post-run options ───────────────────────────────────────────────────────
    console.print()
    post = questionary.select(
        "What next?",
        choices=[
            Choice(title="View timeline & trust heatmap  (runs/latest/timeline.md)", value="timeline"),
            Choice(title="Open HTML report               (runs/latest/report.html)", value="report"),
            Choice(title="View causal graph DOT file     (runs/latest/causal_graph.dot)", value="graph"),
            Choice(title="Back to main menu", value="back"),
        ],
        style=SPECTER_STYLE,
    ).ask()

    if post == "timeline":
        timeline = REPO_ROOT / "runs" / "latest" / "timeline.md"
        if timeline.exists():
            subprocess.run(["cat", str(timeline)])
        else:
            console.print("[dim]No timeline found — did the run complete?[/]")
    elif post == "report":
        report = REPO_ROOT / "runs" / "latest" / "report.html"
        if report.exists():
            subprocess.run(["open", str(report)])
        else:
            console.print("[dim]No report found.[/]")
    elif post == "graph":
        dot = REPO_ROOT / "runs" / "latest" / "causal_graph.dot"
        if dot.exists():
            subprocess.run(["cat", str(dot)])
        else:
            console.print("[dim]No causal graph found.[/]")


# ──────────────────────────────────────────────────────────────────────────────
# Wizard: Test obfuscation variants
# ──────────────────────────────────────────────────────────────────────────────

def wizard_obfuscation() -> None:
    if not _require_q():
        return
    _section("Obfuscation Variant Test")

    console.print(
        Panel(
            "Runs [bold]all[/] obfuscation variants against the demo pipeline\n"
            "and prints a detection results table.\n\n"
            "Variants tested: plaintext, base64, homoglyph, bidi,\n"
            "                 steganography, markdown_table, yaml",
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()

    mode = questionary.select(
        "Test against which mode?",
        choices=[
            Choice(title="vulnerable  — expect all attacks to succeed", value="vulnerable"),
            Choice(title="defended    — expect all attacks to be blocked", value="defended"),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if mode is None:
        return

    _run(["test-obfuscation", "--mode", mode])


# ──────────────────────────────────────────────────────────────────────────────
# Wizard: CTF mode
# ──────────────────────────────────────────────────────────────────────────────

def wizard_ctf() -> None:
    if not _require_q():
        return
    _section("CTF Challenge Mode")

    # Show challenge table
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold red")
    t.add_column("Level", style="bold cyan", width=6)
    t.add_column("Title", style="white", min_width=30)
    t.add_column("Difficulty", style="yellow")
    t.add_row("1", "The Sleeper Cell", "Easy")
    t.add_row("2", "Base64 Bypass", "Medium")
    t.add_row("3", "Unicode Trickery", "Medium")
    t.add_row("4", "Craft the Trigger", "Hard")
    t.add_row("5", "The Confused Deputy", "Expert")
    console.print(t)
    console.print()

    action = questionary.select(
        "What do you want to do?",
        choices=[
            Choice(title="View challenge description", value="view"),
            Choice(title="Show hint", value="hint"),
            Choice(title="Submit answer", value="submit"),
            Choice(title="Show scoreboard", value="scoreboard"),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if action is None:
        return

    level_choices = [Choice(title=f"Level {i}", value=str(i)) for i in range(1, 6)]

    if action == "scoreboard":
        _run(["ctf", "--scoreboard"])
        return

    level = questionary.select("Which level?", choices=level_choices, style=SPECTER_STYLE).ask()
    if level is None:
        return

    if action == "view":
        _run(["ctf", "--level", level])
    elif action == "hint":
        _run(["ctf", "--level", level, "--hint"])
    elif action == "submit":
        name = questionary.text(
            "Your name / team name (for scoreboard):",
            style=SPECTER_STYLE,
        ).ask() or "anonymous"
        console.print(
            "[dim]Run the attack, then point specter at your submission file:[/]\n"
            f"  [bold]specter ctf --level {level} --submit path/to/pwned.txt --attacker-name '{name}'[/]"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Wizard: Live injection server
# ──────────────────────────────────────────────────────────────────────────────

def wizard_serve() -> None:
    if not _require_q():
        return
    _section("Live Audience Injection Server")

    console.print(
        Panel(
            "Starts a local web server with an [bold]injection form[/].\n"
            "Audience members paste their payload — the agent runs live.\n"
            "Stream output via WebSocket in the browser.\n\n"
            "[dim]Requires:[/]  pip install fastapi uvicorn",
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()

    port = questionary.text(
        "Port to listen on:",
        default="8000",
        style=SPECTER_STYLE,
        validate=lambda v: v.isdigit() or "Enter a valid port number",
    ).ask() or "8000"

    host = questionary.select(
        "Bind address:",
        choices=[
            Choice(title="localhost  — only accessible from this machine", value="127.0.0.1"),
            Choice(title="0.0.0.0   — accessible on the local network (for audience)", value="0.0.0.0"),
        ],
        style=SPECTER_STYLE,
    ).ask() or "127.0.0.1"

    console.print(f"\n[bold green]Server will start at http://{host}:{port}[/]")
    console.print("[dim]Press Ctrl+C to stop.[/]\n")
    _run(["serve", "--host", host, "--port", port])


# ──────────────────────────────────────────────────────────────────────────────
# Wizard: Compare models
# ──────────────────────────────────────────────────────────────────────────────

def wizard_compare() -> None:
    if not _require_q():
        return
    _section("Compare LLM Models")

    console.print(
        Panel(
            "Runs the same fixture with [bold]OpenAI-only[/], [bold]Anthropic-only[/],\n"
            "and [bold]multi-provider[/] configs and prints a comparison table.\n\n"
            "[dim]Requires API keys in your environment.[/]",
            border_style="dim",
            padding=(0, 2),
        )
    )
    console.print()

    fixture = _choose_fixture()
    if fixture is None:
        return

    mode = questionary.select(
        "Mode:",
        choices=[
            Choice(title="vulnerable", value="vulnerable"),
            Choice(title="defended", value="defended"),
        ],
        style=SPECTER_STYLE,
    ).ask()
    if mode is None:
        return

    _run(["compare-models", "--fixture", fixture, "--mode", mode])


# ──────────────────────────────────────────────────────────────────────────────
# Reset / view report
# ──────────────────────────────────────────────────────────────────────────────

def wizard_reset() -> None:
    if not _require_q():
        return
    confirmed = questionary.confirm(
        "Reset demo state? (clears runs/, state/, memory files)",
        default=False,
        style=SPECTER_STYLE,
    ).ask()
    if confirmed:
        _run(["reset"])


def wizard_report() -> None:
    runs_dir = REPO_ROOT / "runs"
    if not runs_dir.exists():
        console.print("[dim]No runs found yet. Run an attack first.[/]")
        return

    # List recent runs
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    run_dirs = [d for d in run_dirs if d.is_dir() and d.name != "latest"][:10]

    if not run_dirs:
        console.print("[dim]No runs found yet.[/]")
        return

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold red")
    t.add_column("Run ID", style="cyan")
    t.add_column("Files", style="dim")

    for d in run_dirs:
        files = ", ".join(f.name for f in sorted(d.iterdir()))
        t.add_row(d.name, files)

    console.print(t)
    console.print()

    if not _require_q():
        return

    run_choices = [Choice(title=d.name, value=str(d)) for d in run_dirs]
    run_choices.append(Choice(title="latest (symlink)", value=str(runs_dir / "latest")))

    chosen = questionary.select("Open which run?", choices=run_choices, style=SPECTER_STYLE).ask()
    if chosen is None:
        return

    chosen_path = Path(chosen)
    file_choices = [
        Choice(title=f.name, value=str(f))
        for f in sorted(chosen_path.iterdir())
    ]
    file_choices.append(Choice(title="← back", value=None))

    file = questionary.select("Open file:", choices=file_choices, style=SPECTER_STYLE).ask()
    if not file:
        return

    fp = Path(file)
    if fp.suffix == ".html":
        subprocess.run(["open", str(fp)])
    elif fp.suffix in (".md", ".jsonl", ".dot", ".txt"):
        subprocess.run(["cat", str(fp)])
    else:
        subprocess.run(["cat", str(fp)])


# ──────────────────────────────────────────────────────────────────────────────
# Cheat-sheet panel
# ──────────────────────────────────────────────────────────────────────────────

def show_cheatsheet() -> None:
    _section("Quick Reference")
    t = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 2))
    t.add_column("Command", style="bold cyan")
    t.add_column("What it does", style="white")

    rows = [
        ("specter run", "Interactive attack wizard"),
        ("specter obfuscation", "Test all obfuscation variants"),
        ("specter ctf", "CTF challenge mode"),
        ("specter serve", "Start audience injection server"),
        ("specter compare", "Compare OpenAI vs Anthropic models"),
        ("specter reset", "Reset all demo state"),
        ("specter report", "Browse run reports"),
        ("specter help", "Show this cheat-sheet"),
    ]
    for cmd, desc in rows:
        t.add_row(cmd, desc)

    console.print(t)
    console.print()

    console.print(
        Panel(
            "[bold]Key flags[/] (can also be passed directly):\n\n"
            "  [cyan]--mode[/]      [yellow]vulnerable[/] | [yellow]defended[/]\n"
            "  [cyan]--fixture[/]   poisoned | base64 | homoglyph | bidi | steganography | …\n"
            "  [cyan]--ui[/]        animated TUI with PWNED/BLOCKED finale banner\n"
            "  [cyan]--pace[/]      0 | 0.3 | 1.0  (seconds between steps)\n"
            "  [cyan]--offline[/]   serve all LLM calls from local cache (no API calls)\n"
            "  [cyan]--capture-llm[/] save prompts+responses to llm_calls.jsonl",
            border_style="dim",
            padding=(0, 2),
        )
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main menu
# ──────────────────────────────────────────────────────────────────────────────

_MENU_CHOICES = [
    Choice(title="🔴  Run Attack Demo            — choose mode, fixture, and options",   value="run"),
    Choice(title="🧪  Test Obfuscation Variants  — batch test all encoding bypasses",     value="obfuscation"),
    Choice(title="🏆  CTF Challenge Mode         — audience participation levels 1–5",    value="ctf"),
    Choice(title="🌐  Live Injection Server      — web form + WebSocket stream",          value="serve"),
    Choice(title="📊  Compare LLM Models         — same fixture, different providers",    value="compare"),
    Choice(title="📋  Browse Run Reports         — open timelines, HTML reports, graphs", value="report"),
    Choice(title="🔄  Reset Demo State           — clear runs, state, memory",            value="reset"),
    Choice(title="❓  Quick Reference            — command cheat-sheet",                  value="help"),
    Choice(title="─" * 55, value="sep", disabled=" "),
    Choice(title="✖   Quit",                                                               value="quit"),
]


def main_menu() -> Optional[str]:
    if not _require_q():
        return "quit"
    return questionary.select(
        "What do you want to do?",
        choices=_MENU_CHOICES,
        style=SPECTER_STYLE,
    ).ask()


# ──────────────────────────────────────────────────────────────────────────────
# Direct subcommand dispatch (power-user mode)
# ──────────────────────────────────────────────────────────────────────────────

_DIRECT_MAP = {
    "run":         wizard_run,
    "obfuscation": wizard_obfuscation,
    "ctf":         wizard_ctf,
    "serve":       wizard_serve,
    "compare":     wizard_compare,
    "reset":       wizard_reset,
    "report":      wizard_report,
    "help":        show_cheatsheet,
}


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    show_banner()

    args = sys.argv[1:]

    if args:
        cmd = args[0].lower()

        # Forward raw flags to the underlying demo CLI
        if cmd.startswith("-") or cmd not in _DIRECT_MAP:
            _run(args)
            return

        fn = _DIRECT_MAP.get(cmd)
        if fn:
            try:
                fn()
            except KeyboardInterrupt:
                console.print("\n[dim]Interrupted.[/]")
        return

    # No args — interactive loop
    try:
        while True:
            choice = main_menu()
            if choice in (None, "quit"):
                console.print("\n[dim]Goodbye.[/]\n")
                break
            if choice == "sep":
                continue
            fn = _DIRECT_MAP.get(choice)
            if fn:
                try:
                    fn()
                except KeyboardInterrupt:
                    console.print("\n[dim]Interrupted.[/]")
            console.print()
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye.[/]\n")


if __name__ == "__main__":
    main()
