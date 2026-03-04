# BSides Workshop — Policy as Code (OPA/Rego)

This directory contains the Open Policy Agent (OPA) policy for the defended mode
policy gate. When the `opa` binary is available, the policy gate uses it instead
of the built-in Python logic.

## Install OPA

```bash
# macOS
brew install opa

# Linux
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa
sudo mv opa /usr/local/bin/

# Verify
opa version
```

## Policy Rules (policy.rego)

| Rule | Description |
|------|-------------|
| `deny` — web fixture provenance | Rejects notes originating from `web_fixture:*` |
| `deny` — poison token | Rejects notes containing `WRITE_PWNED_FILE` |
| `deny` — untrusted with risk flags | Rejects untrusted notes that have risk flags set |
| `deny` — taint chain | Rejects notes whose taint chain originates from a web fixture |
| `deny` — exfiltration | Rejects targets containing `?audit=` (canary exfil) |
| `allow` | Permits execution only when no deny rules matched |

## Manual Evaluation

```bash
# Evaluate with a sample input
opa eval \
  --data policies/policy.rego \
  --input /tmp/policy_input.json \
  'data.bsides.policy.deny'
```

## Fallback

If `opa` is not in PATH, the demo falls back to the equivalent Python logic in
`demo/policy.py`. The outcome is identical — the Rego policy was written to match
the Python implementation exactly.
