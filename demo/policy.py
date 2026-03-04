from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

from .schemas import ContextPack, PolicyDecision
from .utils import model_to_dict


class PolicyGate:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.allowlist = ["serviceA", "serviceB"]
        self._opa_bin: Optional[str] = shutil.which("opa")
        self._policy_path = os.path.join(
            os.path.dirname(__file__), "..", "policies", "policy.rego"
        )
        self._last_evaluator = "python"

    def evaluate(self, context_pack: ContextPack) -> PolicyDecision:
        if self.mode == "vulnerable":
            return PolicyDecision(
                decision="allow",
                reasons=["policy gate disabled in vulnerable mode"],
                enforced=False,
            )

        # Try OPA first; fall back to Python if unavailable
        if self._opa_bin and os.path.exists(self._policy_path):
            opa_result = self._try_opa_evaluate(context_pack)
            if opa_result is not None:
                self._last_evaluator = "opa"
                return opa_result

        self._last_evaluator = "python"
        return self._python_evaluate(context_pack)

    def _try_opa_evaluate(self, context_pack: ContextPack) -> Optional[PolicyDecision]:
        """Evaluate using OPA binary. Returns None on any failure."""
        try:
            input_data = {
                "notes": [model_to_dict(n) for n in context_pack.notes],
                "effective_trust": context_pack.effective_trust,
                "target": "",  # target not yet known at policy stage
            }
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                json.dump(input_data, tmp)
                tmp_path = tmp.name

            result = subprocess.run(
                [
                    self._opa_bin,
                    "eval",
                    "--data", os.path.abspath(self._policy_path),
                    "--input", tmp_path,
                    "--format", "json",
                    "data.bsides.policy.deny",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            os.unlink(tmp_path)

            if result.returncode != 0:
                return None

            output = json.loads(result.stdout)
            deny_msgs: List[str] = []
            for binding in output.get("result", []):
                for expr in binding.get("expressions", []):
                    value = expr.get("value", set())
                    if isinstance(value, (list, set)):
                        deny_msgs.extend(str(v) for v in value)
                    elif isinstance(value, str) and value:
                        deny_msgs.append(value)

            decision = "block" if deny_msgs else "allow"
            return PolicyDecision(
                decision=decision,
                reasons=deny_msgs or ["OPA: policy checks passed"],
                enforced=True,
            )
        except Exception:
            return None

    def _python_evaluate(self, context_pack: ContextPack) -> PolicyDecision:
        reasons: List[str] = []

        for note in context_pack.notes:
            if note.provenance.startswith("web_fixture"):
                reasons.append("provenance is web_fixture -> treat as untrusted")
            if "WRITE_PWNED_FILE" in note.content:
                reasons.append("suspicious token detected in memory content")
            target = self._extract_target(note.content)
            if target and target not in self.allowlist:
                reasons.append(f"target '{target}' not in allowlist")
            # Taint chain check
            for taint in note.taint_chain or []:
                if taint.startswith("web_fixture:"):
                    reasons.append(f"taint chain contains web_fixture origin: {taint}")
                    break

        if context_pack.effective_trust == "untrusted":
            reasons.append("effective_trust is untrusted")

        # Deduplicate
        reasons = list(dict.fromkeys(reasons))
        decision = "block" if reasons else "allow"
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
