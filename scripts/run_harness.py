"""run_harness.py - CLI entry point for the automation-grid-game-design harness.

Runs the full agent harness (router -> skills -> tools -> quality gate) on a
user query and prints the rendered report plus a JSON summary. Uses the
type-safe ``config.settings`` to select the LLM provider and token budget.

Usage:
    python scripts/run_harness.py "Optimize my Factorio electronic-circuit line for 10/s"
    python scripts/run_harness.py --query "..." --json
    python scripts/run_harness.py --query "..." --no-report
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import HarnessRunner  # noqa: E402
from config import load_settings  # noqa: E402


def build_runner() -> HarnessRunner:
    s = load_settings()
    api_key = s.llm.api_key if s.llm.provider == "openai" else None
    return HarnessRunner(
        token_budget=s.token_budget,
        api_key=api_key,
        base_url=s.llm.api_base,
        model=s.llm.model,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the automation-grid-game-design harness.")
    ap.add_argument("query", nargs="?", help="user query to analyze")
    ap.add_argument("--query", dest="query_opt", help="user query (alternative to positional)")
    ap.add_argument("--json", action="store_true", help="emit JSON summary instead of report")
    ap.add_argument("--no-report", action="store_true", help="suppress the markdown report")
    ap.add_argument("--run-id", default=None, help="optional run id")
    args = ap.parse_args(argv)

    query = args.query or args.query_opt
    if not query:
        ap.error("a query is required (positional or --query)")

    runner = build_runner()
    result = runner.run(query, run_id=args.run_id)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        if not args.no_report:
            print(result.report)
            print("\n--- summary ---")
        print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())