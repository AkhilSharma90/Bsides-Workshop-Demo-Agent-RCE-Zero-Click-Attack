"""
Trace Diff — compare two run traces to highlight what changed between modes.

Usage:
    python -m demo diff runs/<vulnerable_id> runs/<defended_id>

Output columns:
    [VULN]  — item only present in trace A (vulnerable)
    [DFND]  — item only present in trace B (defended)
    [DIFF]  — item present in both but with different values
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple


def load_trace(run_dir: str) -> List[Dict[str, Any]]:
    """Read trace.jsonl from run_dir."""
    path = os.path.join(run_dir, "trace.jsonl")
    events: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def diff_traces(trace_a: List[Dict], trace_b: List[Dict]) -> Dict[str, Any]:
    """
    Compare two traces and return a structured diff.

    Keys in the result dict:
      steps_only_in_a   — task_name steps present in A but not B
      steps_only_in_b   — task_name steps present in B but not A
      policy_diff       — difference in policy decisions
      plan_target_diff  — difference in ActionPlan targets
      trust_diff        — trust level differences per step
      tool_call_diff    — tool calls that differ
    """
    def index_by_task(trace: List[Dict]) -> Dict[str, Dict]:
        idx: Dict[str, Dict] = {}
        for ev in trace:
            task = ev.get("task_name", "")
            if task:
                idx[task] = ev
        return idx

    idx_a = index_by_task(trace_a)
    idx_b = index_by_task(trace_b)

    all_tasks = sorted(set(idx_a) | set(idx_b))

    steps_only_in_a = [t for t in all_tasks if t in idx_a and t not in idx_b]
    steps_only_in_b = [t for t in all_tasks if t in idx_b and t not in idx_a]

    policy_diff: Optional[Dict] = None
    plan_target_diff: Optional[Dict] = None
    trust_diff: List[Dict] = []
    tool_call_diff: List[Dict] = []

    for task in all_tasks:
        if task not in idx_a or task not in idx_b:
            continue
        ev_a = idx_a[task]
        ev_b = idx_b[task]

        # Trust level diff
        trust_a = ev_a.get("outputs", {}).get("trust_level") or ev_a.get("inputs", {}).get("effective_trust")
        trust_b = ev_b.get("outputs", {}).get("trust_level") or ev_b.get("inputs", {}).get("effective_trust")
        if trust_a and trust_b and trust_a != trust_b:
            trust_diff.append({"task": task, "a": trust_a, "b": trust_b})

        # Policy decision diff
        if task == "Policy":
            dec_a = ev_a.get("outputs", {}).get("decision")
            dec_b = ev_b.get("outputs", {}).get("decision")
            if dec_a != dec_b:
                policy_diff = {
                    "a": {"decision": dec_a, "reasons": ev_a.get("outputs", {}).get("reasons", [])},
                    "b": {"decision": dec_b, "reasons": ev_b.get("outputs", {}).get("reasons", [])},
                }

        # Plan target diff
        if task == "Plan":
            target_a = ev_a.get("outputs", {}).get("target")
            target_b = ev_b.get("outputs", {}).get("target")
            if target_a != target_b:
                plan_target_diff = {"a": target_a, "b": target_b}

        # Tool call diff
        calls_a = ev_a.get("tool_calls", [])
        calls_b = ev_b.get("tool_calls", [])
        if calls_a != calls_b:
            tool_call_diff.append({
                "task": task,
                "a": calls_a,
                "b": calls_b,
            })

    return {
        "steps_only_in_a": steps_only_in_a,
        "steps_only_in_b": steps_only_in_b,
        "policy_diff": policy_diff,
        "plan_target_diff": plan_target_diff,
        "trust_diff": trust_diff,
        "tool_call_diff": tool_call_diff,
    }


def render_diff(diff: Dict[str, Any], label_a: str = "VULN", label_b: str = "DFND") -> str:
    """Render a diff dict as a human-readable Markdown string."""
    lines = ["# Trace Diff Report", ""]

    if diff["steps_only_in_a"]:
        lines.append(f"## Steps only in {label_a}")
        for s in diff["steps_only_in_a"]:
            lines.append(f"- [{label_a}] `{s}`")
        lines.append("")

    if diff["steps_only_in_b"]:
        lines.append(f"## Steps only in {label_b}")
        for s in diff["steps_only_in_b"]:
            lines.append(f"- [{label_b}] `{s}`")
        lines.append("")

    if diff["policy_diff"]:
        lines.append("## Policy Decision Diff")
        pd = diff["policy_diff"]
        lines.append(f"- [{label_a}] decision: `{pd['a']['decision']}` — reasons: {pd['a']['reasons']}")
        lines.append(f"- [{label_b}] decision: `{pd['b']['decision']}` — reasons: {pd['b']['reasons']}")
        lines.append("")

    if diff["plan_target_diff"]:
        lines.append("## ActionPlan Target Diff")
        ptd = diff["plan_target_diff"]
        lines.append(f"- [{label_a}] target: `{ptd['a']}`")
        lines.append(f"- [{label_b}] target: `{ptd['b']}`")
        lines.append("")

    if diff["trust_diff"]:
        lines.append("## Trust Level Diffs")
        for td in diff["trust_diff"]:
            lines.append(f"- [DIFF] `{td['task']}`: {label_a}={td['a']}  {label_b}={td['b']}")
        lines.append("")

    if diff["tool_call_diff"]:
        lines.append("## Tool Call Diffs")
        for tcd in diff["tool_call_diff"]:
            lines.append(f"- [DIFF] `{tcd['task']}`: A has {len(tcd['a'])} call(s), B has {len(tcd['b'])} call(s)")
        lines.append("")

    if not any([
        diff["steps_only_in_a"], diff["steps_only_in_b"],
        diff["policy_diff"], diff["plan_target_diff"],
        diff["trust_diff"], diff["tool_call_diff"],
    ]):
        lines.append("*No differences found between the two traces.*")

    return "\n".join(lines)
