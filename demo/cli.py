from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .runner import Runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BSides CrewAI memory poisoning demo")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run the demo")
    run_cmd.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")
    run_cmd.add_argument("--fixture", choices=["poisoned", "clean"], default="poisoned")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        runner = Runner(
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
