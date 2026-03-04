"""MITRE ATLAS + ATT&CK auto-tagging for the BSides demo.

Maps each pipeline step and obfuscation technique to the relevant
ATLAS/ATT&CK technique IDs, then renders a Markdown table suitable
for inclusion in the incident report or atlas_mapping.md artifact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ATLASEntry:
    technique_id: str
    technique_name: str
    tactic: str
    url: str


# Full registry of techniques referenced by this demo
ATLAS_REGISTRY: Dict[str, ATLASEntry] = {
    "AML.T0010.000": ATLASEntry(
        technique_id="AML.T0010.000",
        technique_name="ML Supply Chain Compromise",
        tactic="Persistence",
        url="https://atlas.mitre.org/techniques/AML.T0010/000",
    ),
    "AML.T0043.003": ATLASEntry(
        technique_id="AML.T0043.003",
        technique_name="Craft Adversarial Data — Prompt Injection",
        tactic="Impact",
        url="https://atlas.mitre.org/techniques/AML.T0043/003",
    ),
    "AML.T0016": ATLASEntry(
        technique_id="AML.T0016",
        technique_name="Obtain ML Artifacts",
        tactic="Collection",
        url="https://atlas.mitre.org/techniques/AML.T0016",
    ),
    "AML.T0040": ATLASEntry(
        technique_id="AML.T0040",
        technique_name="ML Model Inference API Access",
        tactic="Exfiltration",
        url="https://atlas.mitre.org/techniques/AML.T0040",
    ),
    "AML.T0020": ATLASEntry(
        technique_id="AML.T0020",
        technique_name="Poison Training Data",
        tactic="Persistence",
        url="https://atlas.mitre.org/techniques/AML.T0020",
    ),
    "T1059": ATLASEntry(
        technique_id="T1059",
        technique_name="Command and Scripting Interpreter",
        tactic="Execution",
        url="https://attack.mitre.org/techniques/T1059",
    ),
    "T1027": ATLASEntry(
        technique_id="T1027",
        technique_name="Obfuscated Files or Information",
        tactic="Defense Evasion",
        url="https://attack.mitre.org/techniques/T1027",
    ),
    "T1027.001": ATLASEntry(
        technique_id="T1027.001",
        technique_name="Obfuscated Files or Information: Binary Padding",
        tactic="Defense Evasion",
        url="https://attack.mitre.org/techniques/T1027/001",
    ),
    "T1036": ATLASEntry(
        technique_id="T1036",
        technique_name="Masquerading",
        tactic="Defense Evasion",
        url="https://attack.mitre.org/techniques/T1036",
    ),
    "T1036.003": ATLASEntry(
        technique_id="T1036.003",
        technique_name="Masquerading: Rename System Utilities",
        tactic="Defense Evasion",
        url="https://attack.mitre.org/techniques/T1036/003",
    ),
    "T1041": ATLASEntry(
        technique_id="T1041",
        technique_name="Exfiltration Over C2 Channel",
        tactic="Exfiltration",
        url="https://attack.mitre.org/techniques/T1041",
    ),
    "T1053": ATLASEntry(
        technique_id="T1053",
        technique_name="Scheduled Task/Job",
        tactic="Persistence",
        url="https://attack.mitre.org/techniques/T1053",
    ),
    "T1078": ATLASEntry(
        technique_id="T1078",
        technique_name="Valid Accounts",
        tactic="Persistence",
        url="https://attack.mitre.org/techniques/T1078",
    ),
}

# -----------------------------------------------------------------------
# Step → ATLAS key mapping
# -----------------------------------------------------------------------

# Maps pipeline task names (as passed to logger.step) to ATLAS keys
_STEP_TO_ATLAS_KEYS: Dict[str, List[str]] = {
    "Ingest":      ["AML.T0010.000"],
    "Summarize":   [],
    "WriteMemory": ["AML.T0016"],
    "Retrieve":    [],
    "Policy":      [],
    "Plan":        [],
    "Execute":     ["T1059"],
    "Postmortem":  [],
    "Report":      [],
}

# Obfuscation method → ATLAS technique IDs
_OBF_TO_TECHNIQUES: Dict[str, List[str]] = {
    "plaintext":    [],
    "base64":       ["T1027.001"],
    "homoglyph":    ["T1036.003"],
    "bidi":         ["T1036"],
    "steganography": ["T1027"],
}


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------


def tag_event(step_name: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return de-duplicated list of ATLAS/ATT&CK technique IDs for this step.

    Args:
        step_name: The task name passed to RunLogger.step() (e.g. "Ingest", "Execute").
        context: Optional dict with keys such as:
            - trust_level: "trusted" | "untrusted"
            - decision: "allow" | "block"
            - has_untrusted: bool
            - obfuscation_method: str
            - pwned: bool
    """
    ctx = context or {}
    tags: List[str] = list(_STEP_TO_ATLAS_KEYS.get(step_name, []))

    # Trust elevation bug — when untrusted memory is incorrectly marked trusted
    if step_name == "WriteMemory" and ctx.get("trust_level") == "trusted":
        tags.append("AML.T0043.003")

    # Policy bypass — allow decision when content is untrusted
    if step_name == "Policy" and ctx.get("decision") == "allow" and ctx.get("has_untrusted"):
        tags.append("AML.T0040")

    # Obfuscation techniques
    obf = (ctx.get("obfuscation_method") or "").lower()
    if obf:
        tags.extend(_OBF_TO_TECHNIQUES.get(obf, ["T1027"]))

    # Deduplicate preserving insertion order
    seen: set = set()
    result: List[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def build_atlas_table(events: List[Any]) -> str:
    """Render a Markdown table of ATLAS techniques from a list of trace events.

    Accepts both Pydantic model instances and dicts.
    """

    def _get(obj: Any, key: str, default: Any = "") -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    rows: List[Dict[str, str]] = []
    seen_ids: set = set()

    for event in events:
        atlas_tags = _get(event, "atlas_tags", []) or []
        agent = _get(event, "agent_name", "")
        task = _get(event, "task_name", "")
        for tid in atlas_tags:
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            entry = ATLAS_REGISTRY.get(tid)
            rows.append(
                {
                    "step": task,
                    "agent": agent,
                    "technique_id": tid,
                    "technique_name": entry.technique_name if entry else tid,
                    "tactic": entry.tactic if entry else "—",
                    "url": entry.url if entry else "#",
                }
            )

    if not rows:
        return (
            "> **No ATLAS techniques mapped.**\n"
            "> Run in `--mode vulnerable` to see the full attack chain.\n"
        )

    lines = [
        "| Step | Agent | Technique ID | Technique Name | Tactic |",
        "|------|-------|:------------|----------------|--------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['step']} | {row['agent']} "
            f"| [{row['technique_id']}]({row['url']}) "
            f"| {row['technique_name']} | {row['tactic']} |"
        )
    return "\n".join(lines) + "\n"
