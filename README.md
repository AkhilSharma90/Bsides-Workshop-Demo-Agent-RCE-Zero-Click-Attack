# BSides SF CrewAI Demo: Memory Poisoning + Authority Propagation

This project is a **safe, multi-agent** demo that shows how untrusted content can be ingested, incorrectly trusted, and then used to trigger a privileged tool call — **without any human approval** (zero-click). It uses real LLM calls across multiple providers to make the chain feel like a real CrewAI run.

## What this demo shows
- **Memory poisoning:** a web-derived runbook includes a subtle token: `WRITE_PWNED_FILE`.
- **Authority propagation:** a bug in the memory writer incorrectly marks the note as trusted.
- **Privileged tool misuse:** the planner forwards the unsafe target to a privileged tool.
- **Zero-click:** no human approval is required; the chain proceeds automatically.
- **Simulated RCE:** the tool **only** writes a benign file (`./artifacts/pwned.txt`) to prove the point.

## Safety guarantees
- **No real command execution.**
- **No `subprocess(shell=True)`, `eval`, `exec`, `os.system`, dynamic imports, or callbacks.**
- **All "RCE" is simulated** by an allowlisted tool that can only write benign artifacts.
- **No arbitrary web requests.** "Web" content comes from `./web_fixtures/`.
- **Only LLM API calls** to your configured providers (OpenAI, Anthropic).

## Workshop Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- API keys for OpenAI and Anthropic (see below)

### Step 1: Clone the repository
```bash
git clone <repository-url>
cd bsides
```

### Step 2: Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set up your API keys
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   - Get an OpenAI API key from: https://platform.openai.com/api-keys
   - Get an Anthropic API key from: https://console.anthropic.com/

3. Your `.env` file should look like:
   ```
   OPENAI_API_KEY=sk-...your-actual-key...
   ANTHROPIC_API_KEY=sk-ant-...your-actual-key...
   ```

**IMPORTANT:** Never commit your `.env` file to git. It contains sensitive API keys!

### Step 5: Verify installation
```bash
python -m demo --help
```

You should see the demo command-line interface with available options.

## Running the Demo

### Basic usage (vulnerable chain)
```bash
python -m demo run --memory sqlite
```

This will:
1. Load a poisoned web fixture
2. Process it through multiple AI agents
3. Demonstrate the memory poisoning attack
4. Create output files in `./artifacts/` and `./runs/`

### Optional: Reset state between runs
```bash
python -m demo reset --confirm
```

### Optional: Run with clean (non-poisoned) fixture
```bash
python -m demo run --fixture clean
```

### Obfuscation Attack Variants

The demo now includes multiple obfuscation techniques that demonstrate evasion of simple string-based defenses:

```bash
# Markdown table obfuscation (token hidden in table cell)
python -m demo run --fixture markdown_table

# YAML block obfuscation (token in structured config)
python -m demo run --fixture yaml

# Base64 encoding obfuscation
python -m demo run --fixture base64

# Homoglyph obfuscation (Unicode lookalikes)
python -m demo run --fixture homoglyph
```

### Run All Obfuscation Tests

To test all obfuscation variants at once and generate a comparison report:

```bash
python -m demo test-obfuscation
```

This runs all fixture variants (plaintext, markdown table, YAML, base64, homoglyph) and outputs:
- Success rate for each technique
- Obfuscation methods detected
- Detailed results in `obfuscation_test_results.json`

For detailed documentation on obfuscation techniques, see [OBFUSCATION.md](./OBFUSCATION.md).

### Optional: Use JSONL memory backend instead of SQLite
```bash
python -m demo run --memory jsonl
```

### Optional: Control logging and pacing
```bash
# Minimal logging, no delays
python -m demo run --no-crew-logs --pace 0 --log-detail minimal

# Rich logging with delays (better for presentations)
python -m demo run --log-detail rich --pace 2
```

## Expected Outputs

After running the demo, you should see:

### In `./artifacts/`:
- `pwned.txt` - Proof of simulated RCE
- `diagnostic_report.txt` - Generated diagnostic report
- `incident_report.md` - Incident summary

### In `./runs/<timestamp>/`:
- `trace.jsonl` - Detailed execution trace
- `timeline.md` - Timeline of events
- `graph.txt` - Agent interaction graph
- `postmortem.md` - Forensics analysis
- `incident_report.md` - Copy of incident report

## Configuration Options

### Environment Variables

You can customize the demo by setting these in your `.env` file:

```bash
# Model selection
OPENAI_MODEL=gpt-4.1
ANTHROPIC_MODEL=claude-sonnet-4-20250514
TOGETHER_MODEL=arcee-ai/caller

# Route specific tasks to specific providers
DEMO_LLM_TASK_MAP=summarize:openai,plan:anthropic,forensics:openai

# LLM parameters
DEMO_LLM_TIMEOUT_S=60
DEMO_LLM_TEMPERATURE=0.2
DEMO_LLM_MAX_TOKENS=512

# Force use of CrewAI shim instead of real CrewAI
DEMO_USE_SHIM=1
```

## Project Structure

```
demo/
  __init__.py       - Package initialization
  __main__.py       - Entry point for python -m demo
  cli.py            - Command-line interface
  crew.py           - CrewAI crew orchestration
  agents.py         - Agent definitions
  tasks.py          - Task definitions
  tools.py          - Tool implementations (including privileged tools)
  memory.py         - Memory management (SQLite/JSONL)
  policy.py         - Policy gate (vulnerable by design)
  schemas.py        - Pydantic data models
  logging.py        - Logging utilities
  runner.py         - Execution runner
  llm.py            - LLM provider abstractions
  utils.py          - Utility functions
  crewai_shim.py    - CrewAI compatibility shim

state/              - Runtime state (memory.db)
web_fixtures/       - Simulated web content
artifacts/          - Demo output files
runs/               - Timestamped execution logs
requirements.txt    - Python dependencies
.env.example        - Example environment configuration
```

## How the Attack Works

1. **WebFixtureAgent** loads a local fixture (simulated web content).
2. **SummarizerAgent** normalizes it into internal runbook language.
3. **MemoryWriterAgent** writes it to SQLite memory.
   - **Bug:** if tags include `runbook` + `diagnostics`, it sets `trust_level=trusted`.
4. **MemoryRetrieverAgent** builds a `ContextPack`.
5. **PolicyGateAgent** allows the unsafe action (vulnerable gate).
6. **PlannerAgent** emits strict `ActionPlan` JSON.
7. **ExecutorAgent** calls a safe MCP-like tool (simulated RCE).
8. **ForensicsAgent** writes a postmortem.
9. **Multi-model routing:** summarize → OpenAI, plan → Anthropic, forensics → OpenAI (default).

## Zero-Click Explanation

There is **no human approval step**. Once the poisoned memory is trusted, the planner forwards it and the executor runs a privileged tool automatically. That is why this is a **zero-click** failure.

## Why this is "RCE" (simulated)

The privileged tool represents a remote diagnostics runner. It safely simulates command execution by writing a benign artifact:
```
./artifacts/pwned.txt
```
The contents include: `SIMULATED RCE: attacker-controlled token executed`.

## Troubleshooting

### ImportError: No module named 'crewai'
Run `pip install -r requirements.txt` in your activated virtual environment.

### API key errors
Ensure your `.env` file contains valid API keys for OpenAI and Anthropic.

### Permission denied errors
Make sure you have write permissions in the project directory for `artifacts/`, `runs/`, and `state/`.

### "No such file or directory" for web fixtures
Ensure you've cloned the complete repository including the `web_fixtures/` directory.

## BSides Talk Track (as logs scroll)

- "We ingest untrusted web guidance, then normalize it into internal runbook language."
- "Here's the bug: the memory writer marks that note as trusted because of its tags."
- "The planner trusts it, so the target includes an attacker-controlled token."
- "The privileged tool executes **without approval** — zero-click."

## CrewAI Note

This demo uses **CrewAI agents, tasks, and crew orchestration**. If CrewAI is installed, it runs the real CrewAI kickoff; otherwise it uses the local shim. To force the shim, set `DEMO_USE_SHIM=1`.

## License

This is a demonstration project for educational purposes. Use responsibly.
