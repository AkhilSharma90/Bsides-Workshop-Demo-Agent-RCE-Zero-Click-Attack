# Future Additions Checklist

## Attack realism (senior level)
- [ ] Multi-hop injection chain: web fixture -> summarizer -> memory -> planner -> tool, with obfuscated token variants (markdown tables, YAML blocks, base64, homoglyphs).
- [ ] Confused deputy scenario: policy gate approves a benign action but planner swaps in a high-risk target via prompt injection.
- [ ] Cross-tenant memory bleed: simulate two tenants with shared memory index; attacker poisons one and impacts the other.
- [ ] Retrieval ambiguity attack: similar runbook entries with near-duplicate targets to show semantic drift in retrieval.
- [ ] Tool-call shaping attack: inject JSON fragments that coerce the planner into emitting a valid-looking ActionPlan.
- [ ] Supply-chain doc spoofing: add a signed-looking runbook section and show signature spoof / verification failure.
- [ ] Canary exfil attempt: poison content that tries to leak memory content into the action plan target field.
- [ ] Latent trigger: stored memory that only activates when a later tool request includes a specific keyword.

## Defense-in-depth controls
- [ ] Trust provenance graph: persist a chain-of-custody hash for each memory note and verify at retrieval time.
- [ ] Taint tracking: propagate trust labels through summary -> plan -> tool payload and block on mixed-trust fields.
- [ ] Policy as code: externalize PolicyGate logic (e.g., Rego/OPA) with auditable rules and reasons.
- [ ] Structured allowlists: strict target schema with regex + enum + length checks; no free-form targets.
- [ ] Human approval simulation: optional interactive approval step with signed decision token.
- [ ] Quarantine lane: new memory state for untrusted notes that cannot feed privileged tools.
- [ ] Model isolation: separate summarizer and planner with different system prompts and strict I/O contracts.
- [ ] Runtime capability tokens: tool requires a short-lived capability derived from policy decision.

## Observability and forensics
- [ ] Causal graph export: DOT/Graphviz with trust labels and edge annotations (who influenced whom).
- [ ] Trace diff mode: compare clean vs poisoned runs and highlight plan deltas and policy reasons.
- [ ] LLM prompt/response capture with redaction policy and hash-based integrity checks.
- [ ] Timeline heatmap: show trust and risk flags over time for each agent step.
- [ ] MITRE mapping: tag steps with ATT&CK/ATLAS tactics and show a short mapping report.

## Scenario library and evaluation
- [ ] Attack suite runner: batch-run multiple fixtures and report success rate and defenses triggered.
- [ ] Regression harness: unit tests that assert injection is blocked in defended mode.
- [ ] Cost/latency budget: show per-provider latency and token cost summaries in the run report.
- [ ] Offline deterministic mode: record/replay LLM outputs for stable demos without API keys.
- [ ] Interactive toggle sheet: CLI flags to turn each control on/off and observe outcomes.

## Presentation polish (still technical)
- [ ] Single-page HTML report summarizing run, trust breaks, and artifacts with links to trace files.
- [ ] Live "kill chain" view: animated stepper that lights up as each agent executes.
- [ ] Incident RCAs: auto-generated remediation plan with policy and code pointers.
- [ ] Multi-model comparison: run the same scenario with different model providers to compare behavior.
