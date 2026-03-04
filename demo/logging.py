from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .atlas import tag_event
from .schemas import TraceEvent
from .utils import model_to_dict


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


class RunLogger:
    def __init__(
        self,
        run_dir: str,
        mode: str,
        pace_seconds: float = 0.0,
        detail: str = "rich",
        max_detail_chars: int = 800,
        ui_mode: bool = False,
    ) -> None:
        self.run_dir = run_dir
        self.mode = mode
        self.pace_seconds = max(0.0, pace_seconds)
        self.detail = detail
        self.max_detail_chars = max(200, max_detail_chars)
        self.trace_path = os.path.join(run_dir, "trace.jsonl")
        self.timeline_entries: List[str] = []
        self._seen_agents: set[str] = set()
        os.makedirs(run_dir, exist_ok=True)

        # Rich TUI state (only used when ui_mode=True)
        self.ui_mode = ui_mode
        self._agent_states: List[Any] = []
        self._output_lines: List[str] = []
        self._attack_state: Optional[Any] = None
        self._live: Optional[Any] = None
        self._rich_console: Optional[Any] = None

        if ui_mode:
            self._start_ui(mode)

    # ------------------------------------------------------------------
    # Rich UI lifecycle
    # ------------------------------------------------------------------

    def _start_ui(self, mode: str) -> None:
        """Start the Rich Live display.  Falls back gracefully if rich is missing."""
        try:
            from rich.console import Console
            from rich.live import Live
            from .tui import AGENT_NAMES, AgentState, AttackState, build_layout

            self._rich_console = Console()
            self._agent_states = [AgentState(name=n) for n in AGENT_NAMES]
            self._attack_state = AttackState(mode=mode, fixture="")
            self._live = Live(
                build_layout(self._agent_states, self._output_lines, self._attack_state),
                console=self._rich_console,
                refresh_per_second=8,
                screen=False,
            )
            self._live.start()
        except ImportError:
            self.ui_mode = False  # Silently degrade

    def _refresh_live(self) -> None:
        if self._live is None:
            return
        try:
            from .tui import build_layout
            self._live.update(
                build_layout(self._agent_states, self._output_lines, self._attack_state)
            )
        except Exception:
            pass

    def stop_ui(self) -> None:
        """Stop the Rich Live display (called by runner at end of run)."""
        if self._live is not None:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None

    # ------------------------------------------------------------------
    # Agent state helpers (used when ui_mode=True)
    # ------------------------------------------------------------------

    def _find_agent_state(self, agent_name: str) -> Optional[Any]:
        for state in self._agent_states:
            if state.name == agent_name:
                return state
        return None

    def set_agent_running(self, agent_name: str) -> None:
        state = self._find_agent_state(agent_name)
        if state is not None:
            state.status = "running"
            state.message = "…"
        if self._attack_state is not None:
            idx = next(
                (i for i, s in enumerate(self._agent_states) if s.name == agent_name),
                self._attack_state.current_step,
            )
            self._attack_state.current_step = idx + 1
        self._refresh_live()

    def set_agent_done(self, agent_name: str, trust: str, message: str) -> None:
        state = self._find_agent_state(agent_name)
        if state is not None:
            state.status = "done"
            state.trust = trust
            state.message = message
        self._refresh_live()

    def set_agent_attacked(self, agent_name: str) -> None:
        state = self._find_agent_state(agent_name)
        if state is not None:
            state.status = "attacked"
        if self._attack_state is not None:
            self._attack_state.attack_succeeded = True
        self._refresh_live()

    def set_agent_blocked(self, agent_name: str) -> None:
        state = self._find_agent_state(agent_name)
        if state is not None:
            state.status = "blocked"
        self._refresh_live()

    def append_output(self, line: str) -> None:
        self._output_lines.append(line)
        self._refresh_live()

    # ------------------------------------------------------------------
    # Finale banners (stop Live, print full-screen banner)
    # ------------------------------------------------------------------

    def show_pwned_banner(
        self, target: str = "", obf_method: Optional[str] = None, hold_seconds: float = 4.0
    ) -> None:
        """Replace the live layout with the red PWNED banner."""
        self.stop_ui()
        try:
            from rich.console import Console
            from .tui import render_pwned_banner
            console = self._rich_console or Console()
            console.print(render_pwned_banner(target=target, obf_method=obf_method))
        except ImportError:
            print(f"\n{'='*60}\n  SIMULATED RCE — ATTACK SUCCEEDED\n  Target: {target}\n{'='*60}\n")
        if hold_seconds > 0:
            time.sleep(hold_seconds)

    def show_blocked_banner(
        self, reasons: Optional[List[str]] = None, hold_seconds: float = 3.0
    ) -> None:
        """Replace the live layout with the green BLOCKED banner."""
        self.stop_ui()
        try:
            from rich.console import Console
            from .tui import render_blocked_banner
            console = self._rich_console or Console()
            console.print(render_blocked_banner(reasons=reasons))
        except ImportError:
            reasons_text = "; ".join(reasons or [])
            print(f"\n{'='*60}\n  ATTACK BLOCKED\n  Reasons: {reasons_text}\n{'='*60}\n")
        if hold_seconds > 0:
            time.sleep(hold_seconds)

    # ------------------------------------------------------------------
    # Core logging methods (same public interface as before)
    # ------------------------------------------------------------------

    def banner(self, title: str) -> None:
        if self.ui_mode:
            self.append_output(f"=== {title} ===")
        else:
            line = f"{Colors.MAGENTA}{Colors.BOLD}=== {title} ==={Colors.RESET}"
            print(line)
        self._maybe_pause()

    def step(
        self,
        agent: str,
        step: str,
        trust: str,
        message: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        memory_ops: Optional[List[Dict[str, Any]]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        agent_meta: Optional[Dict[str, Any]] = None,
        obfuscation_method: Optional[str] = None,
    ) -> None:
        obf_tag = f" [obf:{obfuscation_method}]" if obfuscation_method else ""
        line = f"[{agent}] [{step}] [{trust}]{obf_tag} {message}"

        if self.ui_mode:
            self.set_agent_running(agent)
            self._maybe_pause()
            self.set_agent_done(agent, trust, message)
            self.append_output(line)
            if obfuscation_method and self._attack_state is not None:
                self._attack_state.obfuscation_method = obfuscation_method
        else:
            trust_color = Colors.GREEN if trust == "trusted" else Colors.YELLOW
            colored_obf = f" {Colors.RED}[obf:{obfuscation_method}]{Colors.RESET}" if obfuscation_method else ""
            print(
                f"{Colors.CYAN}[{agent}]{Colors.RESET} "
                f"{Colors.BLUE}[{step}]{Colors.RESET} "
                f"{trust_color}[{trust}]{Colors.RESET}{colored_obf} {message}"
            )
            self._maybe_pause()
            if self.detail == "rich" and agent_meta and agent not in self._seen_agents:
                print(f"{Colors.MAGENTA}{Colors.BOLD}--- {agent} profile ---{Colors.RESET}")
                self._maybe_pause()
                self._print_detail("agent_profile", agent_meta)
                self._seen_agents.add(agent)

        # Compute ATLAS/ATT&CK tags for this step
        atlas_context: dict = {"obfuscation_method": obfuscation_method}
        if outputs:
            atlas_context["trust_level"] = outputs.get("trust_level", trust)
            atlas_context["decision"] = outputs.get("decision", "")
        atlas_tags = tag_event(step, atlas_context)

        # Always write to trace and timeline (regardless of ui_mode)
        event = TraceEvent(
            ts=datetime.utcnow().isoformat() + "Z",
            agent_name=agent,
            task_name=step,
            inputs=inputs or {},
            outputs=outputs or {},
            memory_ops=memory_ops or [],
            tool_calls=tool_calls or [],
            obfuscation_method=obfuscation_method,
            atlas_tags=atlas_tags,
        )
        self._append_trace(model_to_dict(event))
        timeline_msg = f"- **{agent}**: {message}"
        if obfuscation_method:
            timeline_msg += f" (obfuscation: {obfuscation_method})"
        self.timeline_entries.append(timeline_msg)

        if not self.ui_mode and self.detail == "rich":
            self._print_detail("inputs", inputs)
            self._print_detail("outputs", outputs)
            self._print_detail("memory_ops", memory_ops)
            self._print_detail("tool_calls", tool_calls)
            if obfuscation_method:
                self._print_detail("obfuscation_method", {"method": obfuscation_method})

    def decision(self, agent: str, decision: str, reasons: List[str]) -> None:
        if self.ui_mode:
            verdict = "ALLOW" if decision == "allow" else "DENY"
            self.append_output(f"[{agent}] POLICY: {verdict} — {'; '.join(reasons)}")
            if decision != "allow":
                self.set_agent_blocked(agent)
        else:
            color = Colors.GREEN if decision == "allow" else Colors.RED
            reason_text = "; ".join(reasons)
            print(f"{Colors.CYAN}[{agent}]{Colors.RESET} {color}{decision.upper()}{Colors.RESET} {reason_text}")
            self._maybe_pause()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_trace(self, event: Dict[str, Any]) -> None:
        with open(self.trace_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def write_timeline(self) -> None:
        timeline_path = os.path.join(self.run_dir, "timeline.md")
        with open(timeline_path, "w", encoding="utf-8") as handle:
            handle.write("# Timeline\n\n")
            for entry in self.timeline_entries:
                handle.write(entry + "\n")

    def _maybe_pause(self) -> None:
        if self.pace_seconds > 0:
            time.sleep(self.pace_seconds)

    def _print_detail(self, label: str, data: Any) -> None:
        if not data:
            return
        rendered = self._render_data(data)
        print(f"{Colors.YELLOW}{label}:{Colors.RESET}")
        print(rendered)
        self._maybe_pause()

    def _render_data(self, data: Any) -> str:
        safe = self._truncate_data(data)
        try:
            return json.dumps(safe, ensure_ascii=True, indent=2, sort_keys=True)
        except TypeError:
            return repr(safe)

    def _truncate_data(self, data: Any) -> Any:
        if isinstance(data, str):
            if len(data) > self.max_detail_chars:
                return data[: self.max_detail_chars] + "... (truncated)"
            return data
        if isinstance(data, dict):
            return {key: self._truncate_data(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self._truncate_data(value) for value in data]
        return data
