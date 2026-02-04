from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .runner import Runner
from .obfuscation_test_runner import ObfuscationTestRunner


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
        choices=[
            "poisoned",
            "clean",
            "markdown_table",
            "yaml",
            "base64",
            "homoglyph",
        ],
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

    reset_cmd = sub.add_parser("reset", help="Reset demo state")
    reset_cmd.add_argument("--confirm", action="store_true", help="Confirm destructive reset")

    test_cmd = sub.add_parser("test-obfuscation", help="Run all obfuscation variant tests")
    test_cmd.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        runner = Runner(
            mode=args.mode,
            execution_mode=args.execution,
            memory_backend=args.memory,
            fixture=args.fixture,
            crew_logs=not args.no_crew_logs,
            pace_seconds=args.pace,
            log_detail=args.log_detail,
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
        import os
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        test_runner = ObfuscationTestRunner(root_dir)
        test_runner.run_all_tests(memory_backend=args.memory)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
