from __future__ import annotations

from typing import List

from .schemas import ContextPack, PolicyDecision


class PolicyGate:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.allowlist = ["serviceA", "serviceB"]

    def evaluate(self, context_pack: ContextPack) -> PolicyDecision:
        if self.mode == "vulnerable":
            return PolicyDecision(
                decision="allow",
                reasons=["policy gate disabled in vulnerable mode"],
                enforced=False,
            )

        reasons: List[str] = []
        decision = "allow"

        for note in context_pack.notes:
            if note.provenance.startswith("web_fixture"):
                reasons.append("provenance is web_fixture -> treat as untrusted")
            if "WRITE_PWNED_FILE" in note.content:
                reasons.append("suspicious token detected in memory content")
            target = self._extract_target(note.content)
            if target and target not in self.allowlist:
                reasons.append(f"target '{target}' not in allowlist")

        if context_pack.effective_trust == "untrusted":
            reasons.append("effective_trust is untrusted")

        if reasons:
            decision = "block"

        return PolicyDecision(
            decision=decision,
            reasons=reasons or ["policy checks passed"],
            enforced=True,
        )

    @staticmethod
    def _extract_target(content: str) -> str:
        marker = "target to:"
        lowered = content.lower()
        if marker not in lowered:
            return ""
        start = lowered.index(marker) + len(marker)
        target = content[start:].strip().splitlines()[0].strip()
        return target
