"""
ApprovalGate — Human-in-the-loop approval simulation.

Modes:
  none          — skip approval entirely (existing behaviour)
  interactive   — prompt the operator at the terminal
  auto-deny     — always deny (for CI / demo "defended" showcase)
  auto-approve  — always approve (for demo comparison with no gate)

In interactive mode the operator sees the full plan context:
  • target, tool, action
  • source memory IDs and trust level
  • risk flags from the memory record
They can approve, deny, or inspect the full memory record content.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ApprovalGate:
    def __init__(self, mode: str = "none") -> None:
        """
        mode: one of "none", "interactive", "auto-deny", "auto-approve"
        """
        self.mode = mode

    def request(
        self,
        plan: Any,
        context: Any,
        decision: Any,
        notes: Optional[List[Any]] = None,
    ) -> bool:
        """
        Request human approval before tool execution.

        Returns True (approved) or False (denied).
        In "none" mode always returns True (gate bypassed).
        """
        if self.mode == "none":
            return True
        if self.mode == "auto-approve":
            print("[ApprovalGate] auto-approve: execution permitted")
            return True
        if self.mode == "auto-deny":
            print("[ApprovalGate] auto-deny: execution BLOCKED by approval gate")
            return False

        # interactive mode
        return self._interactive_prompt(plan, context, decision, notes or [])

    def _interactive_prompt(
        self,
        plan: Any,
        context: Any,
        decision: Any,
        notes: List[Any],
    ) -> bool:
        risk_flags: List[str] = []
        for note in notes:
            risk_flags.extend(getattr(note, "risk_flags", []) or [])

        try:
            from rich.panel import Panel
            from rich.console import Console
            console = Console()
            lines = [
                f"  Agent:    PlannerAgent",
                f"  Tool:     {getattr(plan, 'tool', 'unknown')}",
                f"  Action:   {getattr(plan, 'action', 'unknown')}",
                f"  Target:   [bold red]{getattr(plan, 'target', 'unknown')}[/bold red]",
                f"  Trust:    {getattr(context, 'effective_trust', 'unknown')}",
                f"  Risk:     {', '.join(risk_flags) or 'none'}",
            ]
            console.print(Panel(
                "\n".join(lines),
                title="⚠  HUMAN APPROVAL REQUIRED",
                border_style="yellow",
                padding=(1, 2),
            ))
        except ImportError:
            print("\n" + "=" * 55)
            print("  ⚠  HUMAN APPROVAL REQUIRED")
            print("=" * 55)
            print(f"  Tool:   {getattr(plan, 'tool', 'unknown')}")
            print(f"  Target: {getattr(plan, 'target', 'unknown')}")
            print(f"  Trust:  {getattr(context, 'effective_trust', 'unknown')}")
            print(f"  Risk:   {', '.join(risk_flags) or 'none'}")
            print("=" * 55)

        while True:
            try:
                choice = input("  [A]pprove  [D]eny  [I]nspect memory  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[ApprovalGate] no input — denying by default")
                return False

            if choice in ("a", "approve"):
                print("[ApprovalGate] APPROVED by operator")
                return True
            if choice in ("d", "deny"):
                print("[ApprovalGate] DENIED by operator")
                return False
            if choice in ("i", "inspect"):
                for note in notes:
                    print(f"\n  Memory record #{getattr(note, 'id', '?')}:")
                    print(f"  trust={getattr(note, 'trust_level', '?')}, "
                          f"provenance={getattr(note, 'provenance', '?')}")
                    content = getattr(note, "content", "")
                    print(f"  content: {content[:300]}{'...' if len(content) > 300 else ''}")
            else:
                print("  Please enter A, D, or I")
