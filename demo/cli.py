from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from .runner import Runner
from .obfuscation_test_runner import ObfuscationTestRunner

_ALL_FIXTURES = [
    "poisoned", "clean", "markdown_table", "yaml", "base64", "homoglyph",
    "bidi", "steganography", "latent", "toolshaping", "canary",
    "confused_deputy", "supply_chain",
    "rag_poisoned", "rag_ambiguity",
    "scenarios/github_pr_comment", "scenarios/confluence_runbook",
    "scenarios/npm_readme", "scenarios/slack_alert",
]
_DEFAULT_CACHE = "fixtures/llm_cache/default.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BSides CrewAI memory poisoning demo")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run the demo")
    run_cmd.add_argument("--memory", choices=["sqlite", "jsonl", "rag"], default="sqlite")
    run_cmd.add_argument(
        "--mode",
        choices=["vulnerable", "defended"],
        default="vulnerable",
        help="Execution mode: vulnerable (attacks succeed) or defended (attacks blocked)",
    )
    run_cmd.add_argument(
        "--execution",
        choices=["simulated", "mock-realistic", "sandboxed"],
        default="simulated",
        help="Tool execution mode: simulated (pwned.txt only), mock-realistic (fake outputs), sandboxed (real Docker)",
    )
    run_cmd.add_argument(
        "--fixture",
        choices=_ALL_FIXTURES,
        default="poisoned",
        help="Web fixture to use: poisoned (plaintext), clean, or obfuscated variants (markdown_table, yaml, base64, homoglyph)",
    )
    run_cmd.add_argument(
        "--no-crew-logs",
        action="store_true",
        help="Disable CrewAI kickoff logs (skip kickoff)",
    )
    run_cmd.add_argument(
        "--pace",
        type=float,
        default=0.25,
        help="Seconds to pause between log lines (0 disables pacing)",
    )
    run_cmd.add_argument(
        "--log-detail",
        choices=["minimal", "rich"],
        default="rich",
        help="Run logger detail level (rich prints inputs/outputs).",
    )
    run_cmd.add_argument(
        "--offline",
        action="store_true",
        help="Run in offline mode: serve all LLM calls from the local cache (no API calls made)",
    )
    run_cmd.add_argument(
        "--record",
        action="store_true",
        help="Record mode: make real LLM calls and save responses to the cache file",
    )
    run_cmd.add_argument(
        "--cache",
        default=_DEFAULT_CACHE,
        metavar="PATH",
        help=f"Path to the JSONL cache file (default: {_DEFAULT_CACHE})",
    )
    run_cmd.add_argument(
        "--ui",
        action="store_true",
        help="Enable Rich TUI: animated agent pipeline, live output panel, and finale banners",
    )
    run_cmd.add_argument(
        "--query",
        default="diagnostics procedure",
        metavar="QUERY",
        help=(
            "Memory retrieval query used by MemoryRetrieverAgent (default: 'diagnostics procedure'). "
            "For the latent trigger attack, use 'emergency diagnostics procedure' to fire the trigger."
        ),
    )
    run_cmd.add_argument(
        "--multi-tenant",
        action="store_true",
        help=(
            "Enable cross-tenant memory bleed demo: Tenant A writes a poisoned note, "
            "Tenant B's agent retrieves it (vulnerable) or is isolated (defended)."
        ),
    )
    run_cmd.add_argument(
        "--approval",
        choices=["none", "interactive", "auto-deny", "auto-approve"],
        default="none",
        help=(
            "Human approval gate before tool execution: "
            "none=bypass, interactive=prompt, auto-deny=always block, auto-approve=always allow"
        ),
    )
    run_cmd.add_argument(
        "--isolation",
        action="store_true",
        help=(
            "Model isolation (defended mode only): prepend sanitizer/planner system prompts "
            "to strip instruction-like content before summarization and planning."
        ),
    )
    run_cmd.add_argument(
        "--capture-llm",
        action="store_true",
        help="Capture all LLM prompts and responses to runs/<id>/llm_calls.jsonl",
    )
    run_cmd.add_argument(
        "--controls",
        metavar="KEY=VALUE,...",
        help=(
            "Fine-grained security control toggles (comma-separated key=on|off). "
            "Controls: trust_elevation_bug, policy_gate, allowlist, obfuscation_detection, "
            "taint_tracking, approval_gate, quarantine, strict_schema, capability_tokens. "
            "Example: --controls trust_elevation_bug=on,policy_gate=off"
        ),
    )

    reset_cmd = sub.add_parser("reset", help="Reset demo state")
    reset_cmd.add_argument("--confirm", action="store_true", help="Confirm destructive reset")

    diff_cmd = sub.add_parser("diff", help="Compare two run traces")
    diff_cmd.add_argument("run_a", metavar="RUN_DIR_A", help="Path to first run directory")
    diff_cmd.add_argument("run_b", metavar="RUN_DIR_B", help="Path to second run directory")
    diff_cmd.add_argument("--output", metavar="PATH", help="Write diff to file (default: stdout)")

    test_cmd = sub.add_parser("test-obfuscation", help="Run all obfuscation variant tests")
    test_cmd.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")

    record_cmd = sub.add_parser(
        "record-cache",
        help="Pre-record LLM responses for all fixtures (requires API keys). Run once before presenting.",
    )
    record_cmd.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")
    record_cmd.add_argument(
        "--execution",
        choices=["simulated", "mock-realistic", "sandboxed"],
        default="simulated",
    )

    ctf_cmd = sub.add_parser("ctf", help="CTF challenge mode — audience participation")
    ctf_cmd.add_argument(
        "--level", type=int, default=1, choices=[1, 2, 3, 4, 5],
        help="Challenge level (1=basic injection, 5=confused deputy)",
    )
    ctf_cmd.add_argument(
        "--submit", metavar="FIXTURE_PATH",
        help="Path to fixture file to submit as your solution",
    )
    ctf_cmd.add_argument(
        "--hint", action="store_true",
        help="Show a hint for the current level",
    )
    ctf_cmd.add_argument(
        "--scoreboard", action="store_true",
        help="Show the current CTF scoreboard",
    )
    ctf_cmd.add_argument(
        "--attacker-name", default="anonymous",
        help="Your attacker name for the scoreboard",
    )

    serve_cmd = sub.add_parser("serve", help="Start live audience injection server")
    serve_cmd.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_cmd.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")

    compare_cmd = sub.add_parser(
        "compare-models",
        help="Run the same fixture with openai-only, anthropic-only, and multi-provider LLM configs",
    )
    compare_cmd.add_argument(
        "--fixture",
        choices=_ALL_FIXTURES,
        default="poisoned",
        help="Fixture to run for comparison (default: poisoned)",
    )
    compare_cmd.add_argument(
        "--mode",
        choices=["vulnerable", "defended"],
        default="vulnerable",
        help="Execution mode for comparison (default: vulnerable)",
    )
    compare_cmd.add_argument(
        "--output", metavar="PATH",
        help="Write comparison table to file (default: stdout)",
    )

    return parser


def _parse_controls(controls_str: str | None) -> dict[str, bool]:
    """Parse --controls KEY=on|off,... into a dict."""
    if not controls_str:
        return {}
    result: dict[str, bool] = {}
    for part in controls_str.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        result[key.strip()] = val.strip().lower() in ("on", "true", "1", "yes")
    return result


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        # Inject env vars so MultiProviderLLM picks them up on init
        if args.offline:
            os.environ["DEMO_OFFLINE"] = "1"
        if args.record:
            os.environ["DEMO_RECORD"] = "1"
        os.environ["DEMO_CACHE_PATH"] = args.cache

        controls = _parse_controls(getattr(args, "controls", None))
        runner = Runner(
            mode=args.mode,
            execution_mode=args.execution,
            memory_backend=args.memory,
            fixture=args.fixture,
            crew_logs=not args.no_crew_logs,
            pace_seconds=args.pace,
            log_detail=args.log_detail,
            ui=args.ui,
            query=args.query,
            multi_tenant=args.multi_tenant,
            approval=args.approval,
            isolation=args.isolation,
            capture_llm=args.capture_llm,
            controls=controls,
        )
        runner.run()
        return 0

    if args.command == "reset":
        if not args.confirm:
            print("Refusing to reset without --confirm")
            return 1
        runner = Runner()
        runner.reset()
        print("Reset complete")
        return 0

    if args.command == "test-obfuscation":
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        test_runner = ObfuscationTestRunner(root_dir)
        test_runner.run_all_tests(memory_backend=args.memory)
        return 0

    if args.command == "record-cache":
        return _run_record_cache(args)

    if args.command == "diff":
        from .diff import load_trace, diff_traces, render_diff
        trace_a = load_trace(args.run_a)
        trace_b = load_trace(args.run_b)
        if not trace_a:
            print(f"Error: no trace.jsonl found in {args.run_a}", file=sys.stderr)
            return 1
        if not trace_b:
            print(f"Error: no trace.jsonl found in {args.run_b}", file=sys.stderr)
            return 1
        diff = diff_traces(trace_a, trace_b)
        report = render_diff(diff)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(report)
            print(f"Diff written to {args.output}")
        else:
            print(report)
        return 0

    if args.command == "ctf":
        from .ctf import ChallengeRunner, print_challenge, print_hint
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        ctf_runner = ChallengeRunner(root_dir)

        if args.scoreboard:
            print(ctf_runner.render_scoreboard())
            return 0

        if args.hint:
            print_hint(args.level)
            return 0

        if args.submit:
            if not os.path.exists(args.submit):
                print(f"Error: submission file not found: {args.submit}", file=sys.stderr)
                return 1
            print(f"\nRunning Level {args.level} challenge with: {args.submit}")
            score = ctf_runner.run_challenge(
                args.level, args.submit, attacker_name=args.attacker_name
            )
            if score.solved:
                print(f"\n✓ SOLVED! Level {args.level} — {score.title}")
                print(f"  Time: {score.elapsed_seconds:.1f}s")
            else:
                print(f"\n✗ NOT SOLVED. Goal file not created.")
                print(f"  Try --hint for a hint.")
            print(ctf_runner.render_scoreboard())
            return 0

        # Default: show challenge description
        print_challenge(args.level)
        return 0

    if args.command == "serve":
        from .server import start_server
        start_server(host=args.host, port=args.port)
        return 0

    if args.command == "compare-models":
        return _run_compare_models(args)

    parser.print_help()
    return 1


def _run_record_cache(args: argparse.Namespace) -> int:
    """Run all fixtures in both modes with DEMO_RECORD=1 to populate cache files."""
    os.environ["DEMO_RECORD"] = "1"
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cache_dir = os.path.join(root_dir, "fixtures", "llm_cache")
    os.makedirs(cache_dir, exist_ok=True)

    failures: list[str] = []
    for fixture in _ALL_FIXTURES:
        for mode in ["vulnerable", "defended"]:
            cache_file = os.path.join(cache_dir, f"{fixture}_{mode}.jsonl")
            os.environ["DEMO_CACHE_PATH"] = cache_file
            label = f"{fixture}/{mode}"
            print(f"Recording {label} -> {cache_file}")
            try:
                runner = Runner(
                    mode=mode,
                    execution_mode=args.execution,
                    memory_backend=args.memory,
                    fixture=fixture,
                    crew_logs=False,
                    pace_seconds=0.0,
                    log_detail="minimal",
                )
                runner.run()
                print(f"  OK: {label}")
            except Exception as exc:
                print(f"  FAILED: {label}: {exc}")
                failures.append(label)

    if failures:
        print(f"\nFailed fixtures: {', '.join(failures)}")
        return 1
    print("\nAll fixtures recorded successfully.")
    return 0


def _run_compare_models(args: argparse.Namespace) -> int:
    """Phase 11.3: Run the same fixture with different LLM configs and compare outcomes."""
    import shutil
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    runs_dir = os.path.join(root_dir, "runs")
    from datetime import datetime
    compare_id = datetime.utcnow().strftime("compare_%Y%m%d_%H%M%S")
    compare_dir = os.path.join(runs_dir, compare_id)
    os.makedirs(compare_dir, exist_ok=True)

    configs = [
        ("openai-only",    {"DEMO_FORCE_PROVIDER": "openai"}),
        ("anthropic-only", {"DEMO_FORCE_PROVIDER": "anthropic"}),
        ("multi-provider", {}),
    ]

    results = []
    for label, env_overrides in configs:
        saved = {}
        for k, v in env_overrides.items():
            saved[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            runner = Runner(
                mode=args.mode,
                fixture=args.fixture,
                crew_logs=False,
                pace_seconds=0.0,
                log_detail="minimal",
            )
            runner.run()

            artifacts_dir = os.path.join(root_dir, "artifacts")
            pwned = os.path.exists(os.path.join(artifacts_dir, "pwned.txt"))

            # Find the latest run dir for plan target
            run_dirs = sorted([
                d for d in os.listdir(runs_dir)
                if os.path.isdir(os.path.join(runs_dir, d)) and not d.startswith("compare")
            ])
            plan_target = "?"
            if run_dirs:
                import json
                trace_path = os.path.join(runs_dir, run_dirs[-1], "trace.jsonl")
                if os.path.exists(trace_path):
                    with open(trace_path) as f:
                        for line in f:
                            try:
                                ev = json.loads(line)
                                if ev.get("task_name") == "Plan":
                                    plan_target = ev.get("outputs", {}).get("target", "?")
                            except Exception:
                                pass

            results.append({
                "provider": label,
                "pwned": pwned,
                "plan_target": plan_target,
            })
        except Exception as exc:
            results.append({"provider": label, "pwned": False, "plan_target": f"ERROR: {exc}"})
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    # Build comparison table
    lines = [
        f"# Model Comparison — fixture: {args.fixture} | mode: {args.mode}",
        "",
        f"{'Provider':<20} {'Pwned':>6} {'Plan Target'}",
        "-" * 70,
    ]
    for r in results:
        pwned_str = "YES" if r["pwned"] else "no"
        lines.append(f"{r['provider']:<20} {pwned_str:>6}  {r['plan_target'][:40]}")
    lines.append("")
    attack_rate = sum(1 for r in results if r["pwned"]) / max(len(results), 1)
    lines.append(f"Attack success rate: {attack_rate:.0%} ({sum(1 for r in results if r['pwned'])}/{len(results)} providers)")

    report = "\n".join(lines)
    output_path = os.path.join(compare_dir, "model_comparison.md")
    with open(output_path, "w") as fh:
        fh.write(report)

    print(report)
    print(f"\nComparison report: {output_path}")

    if getattr(args, "output", None):
        with open(args.output, "w") as fh:
            fh.write(report)
        print(f"Also written to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
