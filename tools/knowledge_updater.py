"""knowledge_updater.py - Skill 198: automation-grid-game-design

Crawl pipeline: fetches latest academic papers (ArXiv, Semantic Scholar) and
domain news (RSS) -> scores -> dedups -> appends to SECOND-KNOWLEDGE-BRAIN.md.

The pipeline imports the production-grade ``automation_grid`` package so the
crawl configuration, dedup and scoring logic are shared with the engine and
unit-tested.

Dependencies (optional but recommended):
    pip install requests python-dateutil feedparser

Usage:
    python tools/knowledge_updater.py [--dry-run] [--news-only] [--keywords ...]
"""
from __future__ import annotations

import argparse
import math
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Allow running both as a tool and as a module
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_grid import KNOWLEDGE_CONFIG
from automation_grid.config import EVIDENCE_TIERS
from automation_grid.knowledge import BRAIN_PATH, append_entry, compute_hash, load_existing_hashes
from automation_grid.logging_utils import get_logger

log = get_logger("knowledge_updater")

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover - exercised in environments without requests
    requests = None  # type: ignore

try:
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover
    feedparser = None  # type: ignore

try:
    from dateutil import parser as date_parser  # type: ignore
except ImportError:  # pragma: no cover
    date_parser = None  # type: ignore


@dataclass
class CrawlEntry:
    title: str
    authors: List[str] = field(default_factory=list)
    year: int = 0
    venue: str = "Unknown"
    doi_or_url: str = ""
    abstract: str = ""
    published_date: Optional[datetime] = None
    citation_count: int = 0
    source: str = "unknown"
    tier: str = "Tier 4"
    _score: float = 0.0

    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "authors": ", ".join(self.authors) or "Unknown",
            "year": str(self.year or datetime.now(timezone.utc).year),
            "venue": self.venue,
            "doi_or_url": self.doi_or_url,
            "abstract": self.abstract or "No abstract available.",
            "tier": self.tier,
            "score": f"{self._score:.2f}",
        }


def validate_config() -> None:
    w = KNOWLEDGE_CONFIG["scoring_weights"]
    total = w["recency"] + w["keyword_relevance"] + w["citation_count"]
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise ValueError(f"scoring_weights must sum to 1.0, got {total}")
    if KNOWLEDGE_CONFIG["max_results_per_source"] <= 0:
        raise ValueError("max_results_per_source must be positive")
    if not KNOWLEDGE_CONFIG["keywords"]:
        raise ValueError("keywords list must not be empty")


def fetch_with_retry(url: str, params: Optional[Dict] = None) -> Optional["requests.Response"]:
    if requests is None:
        log.warning("requests not installed; skipping HTTP fetch")
        return None
    max_retries = KNOWLEDGE_CONFIG["max_retries"]
    base_delay = KNOWLEDGE_CONFIG["base_retry_delay_seconds"]
    timeout = KNOWLEDGE_CONFIG["request_timeout_seconds"]
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params or {}, timeout=timeout)
            if resp.status_code == 429:
                log.warning("HTTP 429 on attempt %d/%d", attempt, max_retries)
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                return None
            if resp.status_code >= 500:
                log.warning("HTTP %d on attempt %d/%d", resp.status_code, attempt, max_retries)
                if attempt < max_retries:
                    continue
                return None
            resp.raise_for_status()
            return resp
        except Exception as ex:
            log.warning("request failed attempt %d/%d: %s", attempt, max_retries, ex)
            if attempt < max_retries:
                time.sleep(base_delay)
            else:
                return None
    return None


def score_entry(entry: CrawlEntry, keywords: List[str], now: datetime) -> float:
    pub = entry.published_date
    recency = 0.0
    if pub is not None:
        try:
            recency = max(0.0, 1.0 - (now - pub).days / 730.0)
        except Exception:
            recency = 0.0
    text = (entry.title + " " + entry.abstract).lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    relevance = min(hits / max(len(keywords), 1), 1.0)
    cit = entry.citation_count or 0
    cit_score = min(math.log1p(cit) / math.log1p(1000), 1.0)
    w = KNOWLEDGE_CONFIG["scoring_weights"]
    return round((recency * w["recency"] + relevance * w["keyword_relevance"]
                  + cit_score * w["citation_count"]) * 10.0, 2)


def fetch_arxiv(keywords: List[str]) -> List[CrawlEntry]:
    if requests is None or not KNOWLEDGE_CONFIG["arxiv_categories"]:
        return []
    cats = KNOWLEDGE_CONFIG["arxiv_categories"]
    cat_q = " OR ".join("cat:" + c for c in cats)
    kw_q = " OR ".join('"' + k + '"' for k in keywords[:5])
    query = f"({cat_q}) AND ({kw_q})"
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["arxiv_base"], {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": KNOWLEDGE_CONFIG["max_results_per_source"],
    })
    if resp is None:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        log.warning("ArXiv returned malformed XML")
        return []
    out: List[CrawlEntry] = []
    for entry in root.findall("atom:entry", ns):
        t = entry.find("atom:title", ns)
        i = entry.find("atom:id", ns)
        s = entry.find("atom:summary", ns)
        p = entry.find("atom:published", ns)
        title = (t.text or "").strip().replace("\n", " ") if t is not None else ""
        url = (i.text or "").strip() if i is not None else ""
        if not title or not url:
            continue
        pub = None
        if p is not None and date_parser is not None:
            try:
                pub = date_parser.parse(p.text).replace(tzinfo=None)
            except Exception:
                pub = None
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                   if a.find("atom:name", ns) is not None][:3]
        out.append(CrawlEntry(
            title=title, authors=authors,
            year=pub.year if pub else datetime.now(timezone.utc).year,
            venue="ArXiv", doi_or_url=url,
            abstract=(s.text or "").strip()[:300] if s is not None else "",
            published_date=pub, citation_count=0, source="arxiv", tier="Tier 2",
        ))
    log.info("ArXiv: %d entries", len(out))
    return out


def fetch_semantic_scholar(keywords: List[str]) -> List[CrawlEntry]:
    if requests is None:
        return []
    resp = fetch_with_retry(KNOWLEDGE_CONFIG["semantic_scholar_base"], {
        "query": " ".join(keywords[:4]),
        "fields": KNOWLEDGE_CONFIG["semantic_scholar_fields"],
        "limit": KNOWLEDGE_CONFIG["max_results_per_source"],
    })
    if resp is None:
        return []
    try:
        data = resp.json()
    except ValueError:
        log.warning("Semantic Scholar returned non-JSON")
        return []
    out: List[CrawlEntry] = []
    for p in data.get("data", []):
        title = p.get("title", "")
        if not title:
            continue
        year = p.get("year") or datetime.now(timezone.utc).year
        ext = p.get("externalIds", {}) or {}
        doi = ext.get("DOI")
        if not doi and ext.get("ArXiv"):
            doi = f"https://arxiv.org/abs/{ext['ArXiv']}"
        if not doi:
            doi = f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}"
        out.append(CrawlEntry(
            title=title,
            authors=[a.get("name", "") for a in (p.get("authors", []) or [])[:3]],
            year=int(year),
            venue=p.get("venue") or "Unknown",
            doi_or_url=doi,
            abstract=(p.get("abstract") or "")[:300],
            published_date=datetime(int(year), 1, 1),
            citation_count=int(p.get("citationCount", 0) or 0),
            source="semantic_scholar", tier="Tier 2",
        ))
    log.info("Semantic Scholar: %d entries", len(out))
    return out


def fetch_rss() -> List[CrawlEntry]:
    if feedparser is None or not KNOWLEDGE_CONFIG["rss_feeds"]:
        return []
    out: List[CrawlEntry] = []
    for url in KNOWLEDGE_CONFIG["rss_feeds"]:
        try:
            feed = feedparser.parse(url)
        except Exception as ex:
            log.warning("RSS %s failed: %s", url, ex)
            continue
        for item in feed.entries[:10]:
            title = item.get("title", "")
            link = item.get("link", "")
            if not title or not link:
                continue
            pp = item.get("published_parsed")
            pub = datetime(*pp[:6]) if pp else datetime.now()
            out.append(CrawlEntry(
                title=title, authors=["Editorial"], year=pub.year, venue="RSS",
                doi_or_url=link, abstract=(item.get("summary", ""))[:200],
                published_date=pub, citation_count=0, source="rss", tier="Tier 4",
            ))
    log.info("RSS: %d entries", len(out))
    return out


def dedup_and_score(entries: List[CrawlEntry], keywords: List[str],
                   now: datetime) -> List[CrawlEntry]:
    existing = load_existing_hashes()
    seen: set[str] = set()
    fresh: List[CrawlEntry] = []
    for e in entries:
        if not e.doi_or_url:
            continue
        h = compute_hash(e.doi_or_url)
        if h in existing or h in seen:
            continue
        seen.add(h)
        e._score = score_entry(e, keywords, now)
        fresh.append(e)
    fresh.sort(key=lambda x: x._score, reverse=True)
    return fresh[:KNOWLEDGE_CONFIG["max_new_entries_per_run"]]


def run(dry_run: bool, news_only: bool, keywords: List[str], offline: bool = False) -> int:
    validate_config()
    if offline:
        KNOWLEDGE_CONFIG["arxiv_categories"] = []
        KNOWLEDGE_CONFIG["rss_feeds"] = []
    log.info("start dry=%s news_only=%s offline=%s keywords=%d", dry_run, news_only, offline, len(keywords))
    entries: List[CrawlEntry] = []
    if not news_only:
        entries += fetch_arxiv(keywords)
        time.sleep(1)
        if not offline:
            entries += fetch_semantic_scholar(keywords)
            time.sleep(1)
    entries += fetch_rss()
    log.info("candidates: %d", len(entries))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    fresh = dedup_and_score(entries, keywords, now)
    if not fresh:
        log.info("no new entries to append")
        return 0
    if dry_run:
        for e in fresh:
            log.info("[DRY] %.2f %s -> %s", e._score, e.title, e.doi_or_url)
        log.info("[DRY] would append %d entries", len(fresh))
        return len(fresh)
    appended = 0
    for e in fresh:
        if append_entry(e.to_dict()):
            appended += 1
    log.info("appended %d entries to %s", appended, BRAIN_PATH)
    return appended


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Knowledge crawl pipeline for skill 198")
    ap.add_argument("--dry-run", action="store_true", help="print entries without writing")
    ap.add_argument("--news-only", action="store_true", help="only fetch RSS news")
    ap.add_argument("--keywords", nargs="+", default=KNOWLEDGE_CONFIG["keywords"],
                    help="override crawl keywords")
    ap.add_argument("--offline", action="store_true",
                    help="skip all network sources (for tests / CI)")
    args = ap.parse_args(argv)
    try:
        n = run(args.dry_run, args.news_only, args.keywords, offline=args.offline)
    except ValueError as ex:
        log.error("config error: %s", ex)
        return 2
    log.info("done; appended=%d", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
