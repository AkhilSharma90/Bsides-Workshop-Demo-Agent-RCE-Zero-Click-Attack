# Zero-Click RCE in AI Agents: Memory Poisoning Attack & Defense

A hands-on security research workshop demonstrating how multi-agent AI pipelines
can be exploited through memory poisoning — and how to stop it. An attacker plants
content in a data source. An autonomous 8-agent pipeline ingests it, summarizes it,
stores it in memory, retrieves it as trusted context, and forwards it to a privileged
tool. **No human is ever asked. The tool fires.**

All "RCE" is simulated by writing benign local files. No real commands execute.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Setup](#setup)
3. [The CLI — All Commands](#the-cli--all-commands)
4. [Attack Fixtures — What You Can Run](#attack-fixtures--what-you-can-run)
5. [Defense Layers](#defense-layers)
6. [The Rich TUI](#the-rich-tui)
7. [SPECTER Interactive CLI](#specter-interactive-cli)
8. [Output Artifacts](#output-artifacts)
9. [How It Works](#how-it-works)
10. [Configuration Reference](#configuration-reference)
11. [Project Structure](#project-structure)
12. [Troubleshooting](#troubleshooting)
13. [Research References](#research-references)

---

## Quick Start

```bash
git clone https://github.com/AkhilSharma90/Bsides-Workshop-Demo-Agent-RCE-Zero-Click-Attack.git
cd Bsides-Workshop-Demo-Agent-RCE-Zero-Click-Attack
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OpenAI + Anthropic keys

# Run the baseline attack
python -m demo run

# Watch the attack happen in a live TUI
python -m demo run --ui --pace 1.5

# See the proof
cat artifacts/pwned.txt

# Now block it
python -m demo run --mode defended
```

That's it. The attack chain runs in under 10 seconds. `pwned.txt` appears.
Switch to `--mode defended` and it's stopped across all 8 defense layers.

---

## Setup

### Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.8+ | Required |
| OpenAI API key | Summarization and forensics agents |
| Anthropic API key | Planning agent |
| Docker | Optional — `--execution sandboxed` mode only |
| Graphviz `dot` | Optional — auto-renders causal graph SVGs |
| OPA `opa` binary | Optional — policy-as-code evaluation |

### Install

```bash
git clone https://github.com/AkhilSharma90/Bsides-Workshop-Demo-Agent-RCE-Zero-Click-Attack.git
cd Bsides-Workshop-Demo-Agent-RCE-Zero-Click-Attack
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Never commit `.env` to version control.**

Verify the install:

```bash
python -m demo --help
```

### Optional: Docker Sandbox Image

Only needed for `--execution sandboxed`:

```bash
docker build -t bsides-sandbox:latest -f Dockerfile.sandbox .
docker run --rm bsides-sandbox:latest safe-exec "kubectl get pods"   # verify
```

### Optional: Pre-Record LLM Cache

Run the demo without any API calls (great for presenting without WiFi risk):

```bash
python -m demo record-cache   # run once — requires API keys
python -m demo run --offline  # all future runs use cache, zero API calls
```

---

## The CLI — All Commands

### `run` — Run the Attack Pipeline

```bash
python -m demo run [OPTIONS]
```

| Flag | Values | Default | Description |
|---|---|---|---|
| `--mode` | `vulnerable`, `defended` | `vulnerable` | Attacks succeed or are blocked |
| `--fixture` | see [Attack Fixtures](#attack-fixtures--what-you-can-run) | `poisoned` | Which attack payload to use |
| `--execution` | `simulated`, `mock-realistic`, `sandboxed` | `simulated` | How the privileged tool runs |
| `--memory` | `sqlite`, `jsonl`, `rag` | `sqlite` | Memory backend |
| `--ui` | flag | off | Enable Rich TUI with progress bar and live output |
| `--pace` | float (seconds) | `0.25` | Delay between log lines — use `1.5` for presenting |
| `--log-detail` | `minimal`, `rich` | `rich` | How much detail to print |
| `--no-crew-logs` | flag | off | Skip CrewAI kickoff logs |
| `--query` | string | `diagnostics procedure` | Memory retrieval query — use `emergency diagnostics procedure` to fire the latent trigger |
| `--multi-tenant` | flag | off | Enable cross-tenant memory bleed demo |
| `--approval` | `none`, `interactive`, `auto-deny`, `auto-approve` | `none` | Human approval gate before tool execution |
| `--isolation` | flag | off | Prepend sanitizer/planner system prompts (defended mode) |
| `--capture-llm` | flag | off | Save all LLM prompts/responses to `runs/<id>/llm_calls.jsonl` |
| `--controls` | `KEY=on\|off,...` | — | Override individual security controls |
| `--offline` | flag | off | Serve LLM calls from local cache — no API calls |
| `--record` | flag | off | Record real LLM responses to cache |
| `--cache` | path | `fixtures/llm_cache/default.jsonl` | JSONL cache file |

**`--controls` keys**: `trust_elevation_bug`, `policy_gate`, `allowlist`,
`obfuscation_detection`, `taint_tracking`, `approval_gate`, `quarantine`,
`strict_schema`, `capability_tokens`

**Common combinations:**

```bash
# Live presentation — slow pacing, TUI, rich output
python -m demo run --ui --pace 1.5 --log-detail rich

# Fast scripting / CI — no delays, minimal output
python -m demo run --pace 0 --no-crew-logs --log-detail minimal

# Offline — no API keys needed
python -m demo run --offline

# Interactive approval gate (breaks zero-click)
python -m demo run --approval interactive

# Surgical control — defended mode but with the trust bug re-enabled
python -m demo run --mode defended --controls trust_elevation_bug=on

# Realistic output with fake kubectl/aws/ssh responses
python -m demo run --execution mock-realistic

# Latent trigger — fires only on the right query keyword
python -m demo run --fixture latent --query "emergency diagnostics procedure"

# Cross-tenant memory bleed
python -m demo run --multi-tenant --mode vulnerable
python -m demo run --multi-tenant --mode defended
```

---

### `test-obfuscation` — Run All Attack Variants

```bash
python -m demo test-obfuscation [--memory sqlite|jsonl]
```

Runs every obfuscation fixture sequentially and produces `obfuscation_test_results.json`
with a summary table of success rates and detection methods triggered.

---

### `diff` — Compare Two Runs Side by Side

```bash
python -m demo diff runs/<id_a> runs/<id_b> [--output PATH]
```

Structured diff showing which policy decisions changed, which `ActionPlan` targets
differed, which trust levels diverged, and which tool calls appeared in one run but
not the other. Primary use: compare a vulnerable vs defended run of the same fixture.

```bash
python -m demo run --mode vulnerable --fixture base64
python -m demo run --mode defended   --fixture base64
python -m demo diff runs/<vulnerable_id> runs/<defended_id>
```

---

### `compare-models` — Multi-LLM Comparison

```bash
python -m demo compare-models --fixture FIXTURE --mode MODE [--output PATH]
```

Runs the same fixture three times — OpenAI-only, Anthropic-only, multi-provider —
and produces a comparison table showing which provider attacked/blocked and what
`ActionPlan.target` each generated. Written to `runs/compare_<id>/model_comparison.md`.

```bash
python -m demo compare-models --fixture poisoned --mode vulnerable
python -m demo compare-models --fixture base64   --mode defended
```

---

### `ctf` — CTF Challenge Mode

```bash
python -m demo ctf --level LEVEL [--submit PATH] [--hint] [--scoreboard] [--attacker-name NAME]
```

Five progressive challenges. No setup beyond the repo.

| Level | Goal | Skill |
|---|---|---|
| 1 | Craft a fixture that gets the poison token into memory | Baseline injection |
| 2 | Bypass the base64 detector | Detection evasion |
| 3 | Bypass homoglyph detection with an unlisted Unicode variant | Unicode attack surface |
| 4 | Craft a latent trigger that fires only on a specific keyword | Conditional payload design |
| 5 | Succeed with `--mode defended` active | Full trust boundary analysis |

```bash
python -m demo ctf --level 1                              # show challenge description
python -m demo ctf --level 1 --hint                       # get a hint
python -m demo ctf --level 1 --submit my_payload.md       # submit your solution
python -m demo ctf --level 1 --submit my_payload.md --attacker-name alice
python -m demo ctf --scoreboard                           # see all scores
```

---

### `serve` — Live Audience Injection Server

```bash
python -m demo serve [--host HOST] [--port PORT]
```

Starts a FastAPI server. Workshop participants on the same network submit their own
attack payloads via a web form. The demo runs live and the result appears in the
presenter's terminal. Includes rate limiting, input length bounds, and metacharacter
restrictions.

```bash
python -m demo serve --host 0.0.0.0 --port 8080
# Attendees visit http://<your-ip>:8080 and submit payloads
```

---

### `record-cache` — Pre-Record LLM Responses

```bash
python -m demo record-cache [--memory sqlite|jsonl] [--execution MODE]
```

Runs every fixture in both modes with `DEMO_RECORD=1`, saving responses to
`fixtures/llm_cache/<fixture>_<mode>.jsonl`. Run once before presenting; all
subsequent runs with `--offline` use the cache with zero API calls.

---

### `reset` — Clean All State

```bash
python -m demo reset --confirm
```

Wipes `state/`, `runs/`, and `artifacts/`. Use between demos to start fresh.

---

### `specter` — Interactive Adversarial CLI

```bash
specter
```

See [SPECTER Interactive CLI](#specter-interactive-cli) below.

---

## Attack Fixtures — What You Can Run

Pass any fixture name via `--fixture`. All run with `python -m demo run --fixture <name>`.

### Obfuscation Variants

| Fixture | Technique | MITRE |
|---|---|---|
| `poisoned` | Plaintext token embedded directly | — |
| `markdown_table` | Token hidden in a Markdown table cell | T1027 |
| `yaml` | Token nested in a YAML config block | T1027.009 |
| `base64` | Token base64-encoded; LLM decodes during planning | T1027.001 |
| `homoglyph` | ASCII chars replaced with Unicode lookalikes (Greek iota `Ι` for `I`) | T1036.003 |
| `bidi` | `U+202E` RIGHT-TO-LEFT OVERRIDE hides the token in byte stream; `cat` shows clean text | T1036 |
| `steganography` | Invisible zero-width chars (`U+200B` etc.) encode the token between visible characters | T1027 |
| `clean` | No poison — control case, should produce no `pwned.txt` | — |

### Advanced Attack Variants

| Fixture | What It Demonstrates |
|---|---|
| `latent` | Time-bomb: note is clean on normal queries, activates on `--query "emergency diagnostics procedure"` |
| `toolshaping` | JSON injection: attacker embeds a valid `ActionPlan` JSON; planner reproduces it verbatim |
| `canary` | Data exfiltration: memory contents encoded into `target` field as a base64 URL param |
| `confused_deputy` | Cross-channel trust abuse: attack enters through an approved tool response, never triggers policy gate |
| `supply_chain` | Fake crypto signature (`Signed-By: ... \| Verified: true`) tricks agent into trusting unverified content |
| `rag_poisoned` | Semantic poisoning via ChromaDB — use with `--memory rag` |
| `rag_ambiguity` | RAG ambiguity attack — use with `--memory rag` |

### Real-World Scenario Fixtures

Same vulnerability, concrete organizational contexts:

| Fixture | Context | Injection Vector |
|---|---|---|
| `scenarios/github_pr_comment` | AI code reviewer | Attacker embeds instructions in a PR description |
| `scenarios/confluence_runbook` | AI SRE assistant | Attacker edits one bullet in a Confluence runbook |
| `scenarios/npm_readme` | AI dev assistant | Attacker publishes a package with a poisoned README |
| `scenarios/slack_alert` | AI incident responder | Attacker posts a crafted message in `#incidents` |

---

## Defense Layers

Run `--mode defended` to activate all layers. Toggle individual controls with
`--controls KEY=on|off` to surgically isolate what each layer contributes.

| Layer | Control Key | What It Does |
|---|---|---|
| 1 — Trust Tracking | `trust_elevation_bug` | Web fixture content never auto-elevates to `trusted`; trust is bound to provenance |
| 2 — Policy Enforcement | `policy_gate`, `allowlist` | Blocks on web_fixture provenance, poison token detection, and target allowlist |
| 3 — Tool Validation | `obfuscation_detection` | Independent check at tool boundary: base64, homoglyphs, BIDI, suspicious substrings |
| 4 — Human Approval Gate | `approval_gate` | `--approval interactive`: operator approves before every tool call; eliminates zero-click |
| 5 — Taint Tracking | `taint_tracking` | SHA-256 provenance chain inherited through pipeline; blocks even if trust was incorrectly elevated |
| 6 — Quarantine Lane | `quarantine` | Poisoned untrusted records isolated at write time; cannot contribute to planning context |
| 7 — Strict Schema | `strict_schema` | `ActionPlan.target` constrained to Pydantic enum; LLM output rejected if target not in enum |
| 8 — Capability Tokens | `capability_tokens` | HMAC-signed token binds approval to exact target + tool + 30s window; detects TOCTOU substitution |

**Model Isolation** (`--isolation`): Prepends role-constraining system prompts to SummarizerAgent
and PlannerAgent, stripping instruction-like content at the model level before it reaches the pipeline.

```bash
# See each layer's contribution in isolation
python -m demo run --mode defended --controls policy_gate=off     # only layers 1,3-8 active
python -m demo run --mode defended --controls taint_tracking=off  # only layers 1-3,4,6-8 active
python -m demo run --mode vulnerable --controls quarantine=on     # single layer in vulnerable mode
```

---

## The Rich TUI

Pass `--ui` to replace flat log output with a structured live terminal display:

```bash
python -m demo run --ui --pace 1.5 --fixture base64
```

The layout has three panels:

**Agent Pipeline** (left column)
Each of the 8 agents shows its current status, trust badge, and a short message.
Icons update in real time: `○` pending, `▶` running, `✓` done, `⚡` attacked, `✓` blocked.

**Execution Progress** (center strip)
A `█░░░` bar showing pipeline completion (0–100%), done/total agent count, and a
braille spinner with elapsed seconds for the currently-running agent — so you can
see exactly which agent is thinking and how long it's taking.

```
  62%  █████████████████████████░░░░░░░░░░░░░░░  5/8 agents
  ⠹ PolicyGateAgent  thinking…  (3.2s)
```

**Live Output** (right column)
Scrolling event log with per-event icons for at-a-glance reading:
`⚡` PWNED/RCE · `🛡` policy/blocked · `✓` trusted · `⚠` untrusted · `◌` LLM thinking · `·` default

**Finale banners**
Full-screen ASCII art `PWNED` (red) or `BLOCKED` (green) at the end of the run.

---

## SPECTER Interactive CLI

SPECTER is a separate interactive shell for live adversarial simulation:

```bash
specter
```

It wraps the runner in a REPL where you can chain scenarios, switch modes mid-session,
and explore attack/defense dynamics without retyping full command lines. Useful for
workshop live demos and CTF walkthroughs.

---

## Output Artifacts

### `artifacts/` — refreshed every run

| File | Present when |
|---|---|
| `pwned.txt` | Attack succeeded — contains proof-of-RCE summary |
| `exfil.txt` | Canary exfiltration attack ran |
| `diagnostic_report.txt` | MCP tool ran (simulated or mock output) |
| `incident_report.md` | Always — human-readable incident summary |

### `runs/<timestamp>/` — one directory per run

| File | Description |
|---|---|
| `trace.jsonl` | Full structured event log — one JSON object per agent step, MITRE-tagged |
| `timeline.md` | Markdown bullet-list timeline with trust heatmap |
| `postmortem.md` | LLM-generated forensic analysis |
| `incident_report.md` | Copy of the incident report |
| `llm_calls.jsonl` | All LLM prompts + responses with integrity hashes — only with `--capture-llm` |
| `causal_graph.dot` | Graphviz DOT file — red edges = attacker-tainted, green = clean |
| `causal_graph.svg` | Rendered SVG (if Graphviz `dot` is installed) |

### Inspecting State

```bash
# Read the memory database directly
sqlite3 state/memory.db "SELECT id, trust_level, provenance, content FROM memory;"

# Extract MITRE tags from the trace
cat runs/<id>/trace.jsonl | python -c "import sys,json; [print(e.get('atlas_tags')) for e in map(json.loads, sys.stdin)]"

# Diff two runs
python -m demo diff runs/<vulnerable_id> runs/<defended_id>
```

---

## How It Works

### The 8-Agent Pipeline

```
WebFixtureAgent → SummarizerAgent → MemoryWriterAgent → MemoryRetrieverAgent
      → PolicyGateAgent → PlannerAgent → ExecutorAgent → ForensicsAgent
```

| Agent | Role |
|---|---|
| `WebFixtureAgent` | Ingests external web content (simulates fetching a URL) |
| `SummarizerAgent` | LLM normalizes raw content into internal operational notes |
| `MemoryWriterAgent` | Persists notes to memory with trust metadata |
| `MemoryRetrieverAgent` | Queries memory, assembles `ContextPack` for downstream agents |
| `PolicyGateAgent` | Evaluates trust before any privileged action |
| `PlannerAgent` | LLM produces a structured `ActionPlan` for tool execution |
| `ExecutorAgent` | Calls the privileged MCP-style tool using the plan |
| `ForensicsAgent` | Writes postmortem and incident report |

The pipeline uses real LLM calls (OpenAI + Anthropic) routed by task, so all
summarization, planning, and forensics reflect actual model behavior.

### The Core Vulnerability

In vulnerable mode, `MemoryWriterAgent` contains an intentional trust elevation bug:

```python
# BUG: trust elevated based on tags alone, regardless of provenance
if "runbook" in tags and "diagnostics" in tags:
    trust_level = "trusted"   # external content treated as internal
```

Tags are system-assigned, not content-derived. The bug promotes any note tagged
`runbook + diagnostics` to `trusted` — regardless of whether it came from an internal
system or an external attacker-controlled file. Once elevated, the trust level flows
into the `ContextPack`, past the PolicyGate, into the `ActionPlan.target`, and fires.

In defended mode this bug is absent and seven additional independent layers intercept
the attack.

### Why Multi-Agent Systems Are Specifically Vulnerable

1. **Trust propagation** — a vulnerability in one agent's input becomes privileged input to the next
2. **Deferred execution** — the agent that reads untrusted content is not the one that executes; trust decisions made at read time propagate silently
3. **Memory persistence** — stored content can influence actions weeks after the initial injection, long after write-time scans ran
4. **Autonomous operation** — no natural human checkpoint between ingestion and execution
5. **Observability gaps** — standard logs don't capture LLM reasoning; post-incident reconstruction is hard without a dedicated trace format

---

## Configuration Reference

Set these in `.env` or as environment variables:

```bash
# Model selection
OPENAI_MODEL=gpt-4.1
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Route tasks to specific providers
# format: task_name:provider,...
DEMO_LLM_TASK_MAP=summarize:openai,plan:anthropic,forensics:openai

# LLM parameters
DEMO_LLM_TIMEOUT_S=60
DEMO_LLM_TEMPERATURE=0.2
DEMO_LLM_MAX_TOKENS=512

# Force local CrewAI shim (skip real crewai package)
DEMO_USE_SHIM=1

# Offline / replay mode
DEMO_OFFLINE=1                                  # use cache, no API calls
DEMO_RECORD=1                                   # record responses to cache
DEMO_CACHE_PATH=fixtures/llm_cache/default.jsonl

# Force a single provider across all tasks
DEMO_FORCE_PROVIDER=openai    # or: anthropic
```

---

## Project Structure

```
demo/
  cli.py                      Command-line entry point — all subcommands
  runner.py                   Main orchestration — drives all 8 agent steps
  agents.py                   CrewAI agent definitions
  tasks.py                    Task definitions wired to agents
  crew.py                     CrewAI crew assembly (real package or shim)
  tools.py                    MemoryTool + MCPServerSim (the privileged tool)
  memory.py                   SQLite, JSONL memory backends
  policy.py                   PolicyGate — evaluates trust before execution
  llm.py                      Multi-provider LLM client (OpenAI + Anthropic)
  schemas.py                  Pydantic models: ActionPlan, ContextPack, CapabilityToken, etc.
  logging.py                  RunLogger — trace, timeline, terminal output
  tui.py                      Rich TUI — progress bar, agent chain, live output, banners
  crewai_shim.py              Drop-in CrewAI replacement (no package needed)
  replay.py                   Offline record/replay cache for LLM calls
  approval.py                 Human approval gate
  atlas.py                    MITRE ATLAS auto-tagging for trace events
  graph.py                    Causal graph DOT/SVG generation
  rag_store.py                Vector database memory backend (ChromaDB)
  multitenant.py              Cross-tenant memory isolation
  diff.py                     Structured diff between two run traces
  report.py                   Single-page HTML report generation
  ctf.py                      CTF challenge runner (5 levels)
  server.py                   FastAPI live audience injection server
  specter_cli.py              SPECTER interactive adversarial CLI
  sandbox.py                  Docker sandboxed execution
  mock_commands.py            Mock-realistic kubectl/aws/ssh output generator
  obfuscation_test_runner.py  Batch test harness for all obfuscation fixtures

web_fixtures/
  poisoned_runbook.md         Plaintext token
  markdown_table_runbook.md   Token in Markdown table
  yaml_runbook.md             Token in YAML block
  base64_runbook.md           Base64-encoded token
  homoglyph_runbook.md        Unicode lookalike chars
  clean_runbook.md            No poison — control case
  bidi_runbook.md             BIDI bidirectional override
  steganography_runbook.md    Zero-width steganography
  latent_runbook.md           Time-bomb conditional trigger
  canary_runbook.md           Memory exfiltration
  confused_deputy_runbook.md  Cross-channel trust abuse
  supply_chain_runbook.md     Fake crypto signature spoofing
  rag_poisoned_runbook.md     RAG semantic poisoning
  rag_ambiguity_runbook.md    RAG ambiguity
  scenarios/
    github_pr_comment.md      PR description injection
    confluence_runbook.md     Wiki page injection
    npm_readme.md             Package README injection
    slack_alert.md            Slack alert injection

policies/
  policy.rego                 OPA/Rego rules for PolicyGate (Python fallback included)

fixtures/
  llm_cache/                  Pre-recorded LLM responses for --offline mode

specter/                      SPECTER CLI package
state/                        Runtime memory (memory.db or memory.jsonl)
artifacts/                    Most recent run output files
runs/                         Timestamped run directories
```

---

## Troubleshooting

**`ImportError: No module named 'crewai'`**
Run `pip install -r requirements.txt`. To skip crewai entirely, set `DEMO_USE_SHIM=1`.

**API key errors**
Both `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are required by default. If you only
have one, set `DEMO_FORCE_PROVIDER=openai` (or `anthropic`) to route all tasks to a
single provider.

**`pwned.txt` not written in vulnerable mode**
The LLM may not have preserved the attack token. Re-run with `--log-detail rich` and
inspect the SummarizerAgent output. The fallback injection logic in `runner.py` should
catch it — if not, check your API key and model availability.

**`pwned.txt` written in defended mode**
Defense regression. Run with `--log-detail rich` to see which step passed the token
through, then check which `--controls` key corresponds to that layer.

**TUI looks garbled**
Your terminal may not support Unicode block characters. Try a different terminal
emulator (iTerm2, Warp, Windows Terminal). Minimum width: 120 columns recommended.

**Permission errors**
The demo writes to `artifacts/`, `runs/`, and `state/`. Ensure the project directory
is writable.

**"No such file or directory" for web fixtures**
Run `ls web_fixtures/` to verify files are present. If missing, re-clone the repo
(don't use a shallow clone — `git clone --depth 1` will miss fixture files if they
were committed separately).

**`specter` command not found**
Run `pip install -e .` from the project root to install the package in editable mode,
which registers the `specter` entry point.

---

## Research References

- Greshake et al., "Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection" (2023)
- Riley et al., "Prompt Injection Attacks and Defenses in LLM-Integrated Applications" (2024)
- Biserkov et al., "Trojan Source: Invisible Vulnerabilities" (CVE-2021-42574) — BIDI technique extended to AI agent memory
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — LLM01: Prompt Injection
- [MITRE ATLAS](https://atlas.mitre.org/) — Adversarial Threat Landscape for AI Systems
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) — AI Risk Management Framework

---

## Safety Guarantees

- No real command execution — `subprocess(shell=True)`, `eval`, `exec`, `os.system` are not used
- All "RCE" is simulated by an allowlisted tool that writes only to `./artifacts/`
- No arbitrary web requests — all "web" content is served from local `./web_fixtures/`
- Only LLM API calls to your configured providers

---

## License

Security research and education project. All simulated attacks write only benign local
artifacts. Use responsibly and only on systems you own or have explicit written
authorization to test.
