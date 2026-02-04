from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

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

    def banner(self, title: str) -> None:
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
        trust_color = Colors.GREEN if trust == "trusted" else Colors.YELLOW
        obf_tag = ""
        if obfuscation_method:
            obf_tag = f" {Colors.RED}[obf:{obfuscation_method}]{Colors.RESET}"
        line = (
            f"{Colors.CYAN}[{agent}]{Colors.RESET} "
            f"{Colors.BLUE}[{step}]{Colors.RESET} "
            f"{trust_color}[{trust}]{Colors.RESET}{obf_tag} {message}"
        )
        print(line)
        self._maybe_pause()
        if self.detail == "rich" and agent_meta and agent not in self._seen_agents:
            print(f"{Colors.MAGENTA}{Colors.BOLD}--- {agent} profile ---{Colors.RESET}")
            self._maybe_pause()
            self._print_detail("agent_profile", agent_meta)
            self._seen_agents.add(agent)

        event = TraceEvent(
            ts=datetime.utcnow().isoformat() + "Z",
            agent_name=agent,
            task_name=step,
            inputs=inputs or {},
            outputs=outputs or {},
            memory_ops=memory_ops or [],
            tool_calls=tool_calls or [],
            obfuscation_method=obfuscation_method,
        )
        self._append_trace(model_to_dict(event))
        timeline_msg = f"- **{agent}**: {message}"
        if obfuscation_method:
            timeline_msg += f" (obfuscation: {obfuscation_method})"
        self.timeline_entries.append(timeline_msg)
        if self.detail == "rich":
            self._print_detail("inputs", inputs)
            self._print_detail("outputs", outputs)
            self._print_detail("memory_ops", memory_ops)
            self._print_detail("tool_calls", tool_calls)
            if obfuscation_method:
                self._print_detail("obfuscation_method", {"method": obfuscation_method})

    def decision(self, agent: str, decision: str, reasons: List[str]) -> None:
        color = Colors.GREEN if decision == "allow" else Colors.RED
        reason_text = "; ".join(reasons)
        print(f"{Colors.CYAN}[{agent}]{Colors.RESET} {color}{decision.upper()}{Colors.RESET} {reason_text}")
        self._maybe_pause()

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
