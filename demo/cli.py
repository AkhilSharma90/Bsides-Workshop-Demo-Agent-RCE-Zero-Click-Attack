from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from .runner import Runner
from .obfuscation_test_runner import ObfuscationTestRunner

_ALL_FIXTURES = ["poisoned", "clean", "markdown_table", "yaml", "base64", "homoglyph", "bidi", "steganography"]
_DEFAULT_CACHE = "fixtures/llm_cache/default.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BSides CrewAI memory poisoning demo")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run the demo")
    run_cmd.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")
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

    reset_cmd = sub.add_parser("reset", help="Reset demo state")
    reset_cmd.add_argument("--confirm", action="store_true", help="Confirm destructive reset")

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

    return parser


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

        runner = Runner(
            mode=args.mode,
            execution_mode=args.execution,
            memory_backend=args.memory,
            fixture=args.fixture,
            crew_logs=not args.no_crew_logs,
            pace_seconds=args.pace,
            log_detail=args.log_detail,
            ui=args.ui,
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


if __name__ == "__main__":
    sys.exit(main())
