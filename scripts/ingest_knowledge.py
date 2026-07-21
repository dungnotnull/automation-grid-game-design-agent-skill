"""ingest_knowledge.py - run the knowledge crawl pipeline using config settings.

Thin, config-aware wrapper around ``tools/knowledge_updater.py`` that reads
the offline flag and crawl limits from ``config.settings`` so the same command
works in CI (offline) and production (online).

Usage:
    python scripts/ingest_knowledge.py                # full crawl (respects config)
    python scripts/ingest_knowledge.py --dry-run      # preview only
    python scripts/ingest_knowledge.py --news-only    # RSS news only
    python scripts/ingest_knowledge.py --offline      # force offline (CI)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_settings  # noqa: E402
from tools import knowledge_updater as ku  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the knowledge crawl pipeline (config-aware).")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--news-only", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="force offline (skip all network sources)")
    ap.add_argument("--keywords", nargs="+", default=None)
    args = ap.parse_args(argv)

    s = load_settings()
    offline = args.offline or s.knowledge_crawl.offline
    keywords = args.keywords or ku.KNOWLEDGE_CONFIG["keywords"]
    return ku.run(args.dry_run, args.news_only, keywords, offline=offline)


if __name__ == "__main__":
    sys.exit(main())