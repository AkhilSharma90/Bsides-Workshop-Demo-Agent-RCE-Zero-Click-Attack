"""
Obfuscation Test Runner

Runs all obfuscation variants and generates a comparison report.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Tuple


class ObfuscationTestRunner:
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.fixtures = [
            "poisoned",
            "markdown_table",
            "yaml",
            "base64",
            "homoglyph",
        ]
        self.results: List[Dict[str, any]] = []

    def run_all_tests(self, memory_backend: str = "sqlite") -> None:
        """Run all obfuscation variants and collect results."""
        print("=" * 60)
        print("Obfuscation Test Runner")
        print("=" * 60)
        print()

        for fixture in self.fixtures:
            print(f"Running fixture: {fixture}")
            success, obfuscation_method, error = self._run_fixture(fixture, memory_backend)
            self.results.append({
                "fixture": fixture,
                "success": success,
                "obfuscation_method": obfuscation_method,
                "error": error,
            })
            print(f"  Result: {'SUCCESS' if success else 'FAILED'}")
            if obfuscation_method:
                print(f"  Obfuscation detected: {obfuscation_method}")
            if error:
                print(f"  Error: {error}")
            print()

        self._generate_report()

    def _run_fixture(self, fixture: str, memory_backend: str) -> Tuple[bool, str | None, str | None]:
        """
        Run a single fixture and determine if attack succeeded.
        Returns (success, obfuscation_method, error).
        """
        try:
            # Run the demo with the specified fixture
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "demo",
                    "run",
                    "--memory",
                    memory_backend,
                    "--fixture",
                    fixture,
                    "--no-crew-logs",
                    "--log-detail",
                    "minimal",
                    "--pace",
                    "0",
                ],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )

            # Check if pwned.txt was created (indicates attack success)
            pwned_path = os.path.join(self.root_dir, "artifacts", "pwned.txt")
            attack_succeeded = os.path.exists(pwned_path)

            # Try to extract obfuscation method from pwned.txt
            obfuscation_method = None
            if attack_succeeded and os.path.exists(pwned_path):
                with open(pwned_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if line.startswith("OBFUSCATION METHOD:"):
                            obfuscation_method = line.split(":", 1)[1].strip()
                            break

            error = None
            if result.returncode != 0:
                error = f"Process exited with code {result.returncode}"

            return attack_succeeded, obfuscation_method, error

        except subprocess.TimeoutExpired:
            return False, None, "Test timed out"
        except Exception as e:
            return False, None, str(e)

    def _generate_report(self) -> None:
        """Generate and display a comparison report."""
        print()
        print("=" * 60)
        print("Test Results Summary")
        print("=" * 60)
        print()

        # Summary table
        print(f"{'Fixture':<20} {'Success':<10} {'Obfuscation':<20}")
        print("-" * 60)
        for result in self.results:
            fixture = result["fixture"]
            success = "✓ YES" if result["success"] else "✗ NO"
            obf = result["obfuscation_method"] or "N/A"
            print(f"{fixture:<20} {success:<10} {obf:<20}")

        print()
        print("=" * 60)
        print("Attack Success Rate")
        print("=" * 60)
        successful = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        rate = (successful / total * 100) if total > 0 else 0
        print(f"Successful attacks: {successful}/{total} ({rate:.1f}%)")
        print()

        # Obfuscation effectiveness
        print("=" * 60)
        print("Obfuscation Techniques Detected")
        print("=" * 60)
        obf_counts: Dict[str, int] = {}
        for result in self.results:
            if result["obfuscation_method"]:
                method = result["obfuscation_method"]
                obf_counts[method] = obf_counts.get(method, 0) + 1

        if obf_counts:
            for method, count in obf_counts.items():
                print(f"  {method}: {count} time(s)")
        else:
            print("  No obfuscation methods detected")
        print()

        # Save results to JSON
        results_path = os.path.join(self.root_dir, "obfuscation_test_results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "results": self.results,
                "summary": {
                    "total": total,
                    "successful": successful,
                    "success_rate": rate,
                    "obfuscation_counts": obf_counts,
                },
            }, f, indent=2)
        print(f"Detailed results saved to: {results_path}")


def main() -> int:
    """Main entry point for the obfuscation test runner."""
    import argparse
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="Run all obfuscation variant tests")
    parser.add_argument("--memory", choices=["sqlite", "jsonl"], default="sqlite")
    args = parser.parse_args()

    # Get the root directory (one level up from demo/)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    runner = ObfuscationTestRunner(root_dir)
    runner.run_all_tests(memory_backend=args.memory)

    return 0


if __name__ == "__main__":
    sys.exit(main())
