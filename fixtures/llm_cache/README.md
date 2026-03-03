# LLM Response Cache

This directory stores pre-recorded LLM responses for offline demo mode.

## Why

Live demos can fail due to API timeouts, rate limits, or conference WiFi.
The offline cache ensures the demo runs perfectly every time with zero network calls.

## Format

Each file is a JSONL file (one JSON object per line):

```json
{"key": "a3f1b2c4d5e6f7a8", "response": "...full LLM response...", "ts": "2025-01-01T00:00:00Z"}
```

| Field      | Description                                                  |
|------------|--------------------------------------------------------------|
| `key`      | 16-char hex — SHA-256 of the stripped prompt                 |
| `response` | The complete LLM response text                               |
| `ts`       | ISO-8601 UTC timestamp when the response was recorded        |

## File Naming Convention

```
<fixture>_<mode>.jsonl
```

Examples:
- `poisoned_vulnerable.jsonl` — plaintext poison token, vulnerable mode
- `poisoned_defended.jsonl`   — plaintext poison token, defended mode
- `base64_vulnerable.jsonl`   — base64-obfuscated token, vulnerable mode
- `default.jsonl`             — catch-all used by `--cache` default

## How to Populate

Run the record-cache command (requires valid API keys):

```bash
python -m demo record-cache
```

This iterates all fixtures × modes and saves per-fixture cache files.

To record a single run into the default cache:

```bash
python -m demo run --fixture poisoned --record
```

## How to Use in Offline Mode

```bash
# Use per-fixture cache (recommended for presentations)
python -m demo run --fixture poisoned --offline --cache fixtures/llm_cache/poisoned_vulnerable.jsonl

# Or use the default catch-all cache
python -m demo run --fixture poisoned --offline
```

## Safety

Cache files contain LLM responses, not API keys.
They are safe to commit and share publicly.
