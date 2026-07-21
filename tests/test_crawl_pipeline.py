"""test_knowledge_updater.py - pytest suite for the crawl pipeline (mirror of tools/test_knowledge_updater.py)."""
from __future__ import annotations

import datetime
from pathlib import Path

from automation_grid import KNOWLEDGE_CONFIG
from automation_grid.knowledge import compute_hash, load_existing_hashes, append_entry
from tools import knowledge_updater as ku


def test_hash_dedup():
    a = compute_hash("https://x.com/1")
    assert a == compute_hash("https://x.com/1")
    assert compute_hash("https://x.com/2") != a
    assert compute_hash("  HTTPS://X.COM/1  ") == a


def test_score_range_and_ordering():
    e = ku.CrawlEntry(
        title="factory automation game throughput bottleneck belt balancer splitter",
        abstract="production chain ratio optimization and recipe graph scheduling",
        published_date=datetime.datetime(2024, 6, 1), citation_count=10)
    now = datetime.datetime(2024, 6, 1)
    s = ku.score_entry(e, KNOWLEDGE_CONFIG["keywords"], now)
    assert 0 <= s <= 10
    generic = ku.CrawlEntry(title="zzz", abstract="zzz",
                            published_date=datetime.datetime(2024, 1, 1), citation_count=0)
    assert s >= ku.score_entry(generic, KNOWLEDGE_CONFIG["keywords"], now)


def test_config_validation_passes():
    ku.validate_config()


def test_dry_run_no_network_returns_zero():
    assert ku.run(dry_run=True, news_only=True, keywords=["zzznonexistent"], offline=True) == 0


def test_append_entry_dedup(tmp_path: Path):
    brain = tmp_path / "brain.md"
    brain.write_text("# brain\n\n## 7. Knowledge Update Log\n", encoding="utf-8")
    from automation_grid import knowledge as k
    entry = {"title": "T", "authors": "A", "year": "2025", "venue": "V",
             "doi_or_url": "https://example.com/unique-1",
             "abstract": "ab", "tier": "Tier 2", "score": "5.0"}
    assert k.append_entry(entry, brain) is True
    assert k.append_entry(entry, brain) is False


def test_load_existing_hashes_is_set():
    assert isinstance(load_existing_hashes(), set)


def test_crawl_entry_to_dict():
    e = ku.CrawlEntry(title="T", authors=["A", "B"], year=2025, venue="V",
                      doi_or_url="https://x", abstract="ab")
    d = e.to_dict()
    assert d["authors"] == "A, B"
    assert d["doi_or_url"] == "https://x"
