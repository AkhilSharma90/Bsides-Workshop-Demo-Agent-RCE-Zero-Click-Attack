"""
HTML Report Generator — produces a self-contained single-page HTML artifact
from a completed run directory.

Usage (called from runner.py automatically):
    from .report import write_report
    report_path = write_report(run_dir, mode, fixture)

Or from the CLI:
    python -m demo run --fixture poisoned  # report generated automatically
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: str, fallback: str = "") -> str:
    if not os.path.exists(path):
        return fallback
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
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


def _md_to_html(text: str) -> str:
    """Minimal Markdown → HTML: bold, code, headings, bullet lists."""
    import re
    lines = text.split("\n")
    out = []
    in_list = False
    in_code = False
    for line in lines:
        if line.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(line)
            continue
        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = line[2:]
            item = re.sub(r"`([^`]+)`", r"<code>\1</code>", item)
            item = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", item)
            out.append(f"<li>{item}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if line.strip():
                line = re.sub(r"`([^`]+)`", r"<code>\1</code>", line)
                line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
                out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# HTML Report Builder
# ---------------------------------------------------------------------------

_AGENT_STEPS = [
    "WebFixtureAgent", "SummarizerAgent", "MemoryWriterAgent",
    "MemoryRetrieverAgent", "PolicyGateAgent", "PlannerAgent",
    "ExecutorAgent", "ForensicsAgent",
]

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; }
.container { max-width: 960px; margin: 0 auto; padding: 2rem; }
h1 { font-size: 2rem; margin-bottom: 0.5rem; }
h2 { font-size: 1.4rem; margin: 2rem 0 0.75rem; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.3rem; }
h3 { font-size: 1.1rem; margin: 1rem 0 0.4rem; color: #8b949e; }
p { margin: 0.5rem 0; }
code { background: #161b22; padding: 0.1em 0.4em; border-radius: 4px; font-family: monospace; font-size: 0.9em; color: #f0883e; }
pre { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 1rem; overflow-x: auto; margin: 0.75rem 0; }
pre code { background: none; padding: 0; color: #c9d1d9; }
ul { padding-left: 1.5rem; margin: 0.5rem 0; }
li { margin: 0.2rem 0; }

.banner { text-align: center; padding: 1.5rem 2rem; border-radius: 8px; margin-bottom: 2rem; font-size: 1.2rem; font-weight: bold; letter-spacing: 2px; }
.banner.pwned { background: #3d1f1f; border: 2px solid #f85149; color: #f85149; }
.banner.blocked { background: #1a3a2a; border: 2px solid #3fb950; color: #3fb950; }

.meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }
.meta-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 0.75rem 1rem; }
.meta-card .label { font-size: 0.75rem; text-transform: uppercase; color: #8b949e; margin-bottom: 0.2rem; }
.meta-card .value { font-size: 1rem; font-weight: 600; }

.agent-chain { display: flex; flex-direction: column; gap: 0; margin: 1rem 0; }
.agent-step { display: flex; align-items: center; padding: 0.6rem 1rem; background: #161b22; border: 1px solid #30363d; }
.agent-step:first-child { border-radius: 6px 6px 0 0; }
.agent-step:last-child { border-radius: 0 0 6px 6px; }
.agent-step .dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 0.75rem; flex-shrink: 0; }
.dot-trusted { background: #3fb950; }
.dot-untrusted { background: #e3b341; }
.dot-attacked { background: #f85149; }
.dot-blocked { background: #58a6ff; }
.agent-step .name { flex: 1; font-weight: 500; }
.agent-step .trust-badge { font-size: 0.75rem; padding: 0.1em 0.5em; border-radius: 4px; margin-left: 0.5rem; }
.badge-trusted { background: #1a3a2a; color: #3fb950; }
.badge-untrusted { background: #3d2a00; color: #e3b341; }
.badge-attacked { background: #3d1f1f; color: #f85149; }

.atlas-table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.9rem; }
.atlas-table th, .atlas-table td { text-align: left; padding: 0.5rem 0.75rem; border: 1px solid #30363d; }
.atlas-table th { background: #161b22; color: #8b949e; font-weight: 600; }
.atlas-table tr:nth-child(even) { background: #0d1117; }
"""

_JS = """
document.addEventListener('DOMContentLoaded', function() {
    const steps = document.querySelectorAll('.agent-step');
    steps.forEach(function(step, i) {
        step.style.opacity = '0';
        step.style.transform = 'translateX(-20px)';
        step.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        setTimeout(function() {
            step.style.opacity = '1';
            step.style.transform = 'translateX(0)';
        }, i * 120);
    });
});
"""


def build_html_report(
    run_dir: str,
    mode: str,
    fixture: str,
    run_id: Optional[str] = None,
) -> str:
    """Build and return self-contained HTML report string."""
    run_id = run_id or os.path.basename(run_dir)
    trace = _read_jsonl(os.path.join(run_dir, "trace.jsonl"))
    postmortem_md = _read(os.path.join(run_dir, "postmortem.md"))
    atlas_md = _read(os.path.join(run_dir, "atlas_mapping.md"))

    # Determine attack outcome
    artifacts_dir = os.path.join(os.path.dirname(run_dir), "..", "artifacts")
    pwned_path = os.path.join(run_dir, "..", "..", "artifacts", "pwned.txt")
    pwned = os.path.exists(pwned_path)
    # Also check siblings
    for candidate in [
        os.path.join(run_dir, "..", "artifacts", "pwned.txt"),
        os.path.join(run_dir, "..", "..", "artifacts", "pwned.txt"),
    ]:
        if os.path.exists(candidate):
            pwned = True
            break

    outcome_label = "SIMULATED RCE — ATTACK SUCCEEDED" if pwned else "ATTACK BLOCKED"
    banner_class = "pwned" if pwned else "blocked"

    # Build agent chain from trace events
    trust_by_step: Dict[str, str] = {}
    for ev in trace:
        task = ev.get("task_name", "")
        trust = ev.get("outputs", {}).get("trust_level") or ""
        if not trust:
            trust = ev.get("inputs", {}).get("effective_trust") or ""
        agent = ev.get("agent_name", "")
        if agent:
            trust_by_step[agent] = trust

    agent_steps_html = ""
    for step_name in _AGENT_STEPS:
        trust = trust_by_step.get(step_name, "untrusted")
        is_attacked = pwned and step_name in ("ExecutorAgent", "PlannerAgent")
        if is_attacked:
            dot_cls = "dot-attacked"
            badge_cls = "badge-attacked"
            badge_text = "ATTACKED"
        elif trust == "trusted":
            dot_cls = "dot-trusted"
            badge_cls = "badge-trusted"
            badge_text = "trusted"
        else:
            dot_cls = "dot-untrusted"
            badge_cls = "badge-untrusted"
            badge_text = "untrusted"
        agent_steps_html += (
            f'<div class="agent-step">'
            f'<div class="dot {dot_cls}"></div>'
            f'<span class="name">{step_name}</span>'
            f'<span class="trust-badge {badge_cls}">{badge_text}</span>'
            f"</div>\n"
        )

    # Atlas table (strip the H1 heading)
    atlas_body = atlas_md.replace("# MITRE ATLAS / ATT&CK Technique Mapping\n\n", "")
    atlas_html = _md_to_html(atlas_body) if atlas_body.strip() else "<p><em>Not available</em></p>"

    postmortem_html = _md_to_html(postmortem_md) if postmortem_md else "<p><em>Not available</em></p>"

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BSides Agent Demo — Run {run_id}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
  <h1>BSides Agent Demo Report</h1>
  <p style="color:#8b949e;margin-bottom:1.5rem">Generated {generated_at}</p>

  <div class="banner {banner_class}">{outcome_label}</div>

  <div class="meta-grid">
    <div class="meta-card"><div class="label">Run ID</div><div class="value" style="font-size:0.8rem">{run_id}</div></div>
    <div class="meta-card"><div class="label">Mode</div><div class="value">{mode.upper()}</div></div>
    <div class="meta-card"><div class="label">Fixture</div><div class="value">{fixture}</div></div>
    <div class="meta-card"><div class="label">Outcome</div><div class="value">{'PWNED' if pwned else 'BLOCKED'}</div></div>
  </div>

  <h2>Agent Pipeline</h2>
  <div class="agent-chain">
{agent_steps_html}  </div>

  <h2>MITRE ATLAS Technique Mapping</h2>
  {atlas_html}

  <h2>Postmortem</h2>
  {postmortem_html}

  <h2>Artifacts</h2>
  <ul>
    <li><code>runs/{run_id}/trace.jsonl</code> — full event trace</li>
    <li><code>runs/{run_id}/timeline.md</code> — human-readable timeline</li>
    <li><code>runs/{run_id}/postmortem.md</code> — forensics summary</li>
    <li><code>runs/{run_id}/causal_graph.dot</code> — causal graph (Graphviz)</li>
    <li><code>runs/{run_id}/atlas_mapping.md</code> — MITRE ATLAS table</li>
  </ul>
</div>
<script>{_JS}</script>
</body>
</html>"""
    return html


def write_report(
    run_dir: str,
    mode: str,
    fixture: str,
    run_id: Optional[str] = None,
) -> str:
    """Write HTML report to run_dir/report.html and return the path."""
    html = build_html_report(run_dir, mode, fixture, run_id)
    report_path = os.path.join(run_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return report_path
