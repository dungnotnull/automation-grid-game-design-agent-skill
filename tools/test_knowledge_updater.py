"""test_knowledge_updater.py - unit tests for the knowledge crawl pipeline.

Pytest-compatible; also runnable standalone (``python tools/test_knowledge_updater.py``).
"""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_grid import KNOWLEDGE_CONFIG
from automation_grid.knowledge import compute_hash, load_existing_hashes
from tools import knowledge_updater as ku


def test_hash_dedup() -> None:
    a = compute_hash("https://x.com/1")
    b = compute_hash("https://x.com/1")
    assert a == b
    assert compute_hash("https://x.com/2") != a
    # case/whitespace insensitive
    assert compute_hash("  HTTPS://X.COM/1  ") == a


def test_score_range() -> None:
    e = ku.CrawlEntry(
        title="factory automation game throughput bottleneck belt balancer splitter",
        abstract="production chain ratio optimization and recipe graph scheduling",
        published_date=datetime.datetime(2024, 6, 1),
        citation_count=10,
    )
    now = datetime.datetime(2024, 6, 1)
    s = ku.score_entry(e, KNOWLEDGE_CONFIG["keywords"], now)
    assert 0 <= s <= 10, s
    # a high-relevance recent entry should beat a generic older empty one
    generic = ku.CrawlEntry(title="zzz", abstract="zzz",
                            published_date=datetime.datetime(2024, 1, 1), citation_count=0)
    assert s >= ku.score_entry(generic, KNOWLEDGE_CONFIG["keywords"], now)


def test_config_validation() -> None:
    ku.validate_config()  # must not raise


def test_dry_run_no_network() -> None:
    # With no feeds reachable and no installed libs, dry-run returns 0 cleanly
    n = ku.run(dry_run=True, news_only=True, keywords=["zzznonexistent"], offline=True)
    assert n == 0


def test_append_dedup(tmp_path: Path) -> None:
    brain = tmp_path / "brain.md"
    brain.write_text("# brain\n\n## 7. Knowledge Update Log\n", encoding="utf-8")
    from automation_grid import knowledge as k
    entry = {"title": "T", "authors": "A", "year": "2025", "venue": "V",
             "doi_or_url": "https://example.com/unique-1",
             "abstract": "ab", "tier": "Tier 2", "score": "5.0"}
    assert k.append_entry(entry, brain) is True
    assert k.append_entry(entry, brain) is False  # deduped


def test_load_existing_hashes() -> None:
    h = load_existing_hashes()
    assert isinstance(h, set)


if __name__ == "__main__":
    test_hash_dedup()
    test_score_range()
    test_config_validation()
    test_dry_run_no_network()
    print("[OK] all knowledge_updater tests passed")
