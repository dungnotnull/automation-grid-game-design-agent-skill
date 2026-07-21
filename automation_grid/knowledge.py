"""automation_grid.knowledge - SECOND-KNOWLEDGE-BRAIN.md read/append helpers."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import ROOT

BRAIN_PATH = ROOT / "SECOND-KNOWLEDGE-BRAIN.md"
UPDATE_LOG_HEADER = "## 7. Knowledge Update Log"


def compute_hash(identifier: str) -> str:
    return hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()


def load_existing_hashes(path: Path = BRAIN_PATH) -> set[str]:
    if not path.exists():
        return set()
    hashes: set[str] = set()
    text = path.read_text(encoding="utf-8")
    # Match markdown links or DOI/URL entries
    for m in re.finditer(r"(?:10\.\d{4,9}/[^\s|)]+|https?://\S+)", text):
        hashes.add(compute_hash(m.group(0)))
    return hashes


def parse_papers_table(path: Path = BRAIN_PATH) -> List[Dict[str, str]]:
    """Parse the seeded papers table in Section 2 into structured records."""
    if not path.exists():
        return []
    rows: List[Dict[str, str]] = []
    capture = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("| Title"):
            capture = True
            continue
        if capture and not line.strip().startswith("|"):
            break
        if capture and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6 or cells[0].lower() in ("title", "---"):
                continue
            rows.append({
                "title": cells[0],
                "authors": cells[1],
                "year": cells[2],
                "venue": cells[3],
                "doi_or_url": cells[4],
                "tier": cells[5],
            })
    return rows


def _normalize(text: str) -> str:
    """Lowercase, strip apostrophes and non-alphanumeric runs for fuzzy matching."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def search_brain(keywords: List[str], path: Path = BRAIN_PATH,
                 max_results: int = 5) -> List[Dict[str, str]]:
    """Return the most relevant seeded entries whose title/venue/authors match keywords.

    Matching is token-based and apostrophe-insensitive: a paper scores +1 for
    each query keyword (or keyword token) that appears in its normalized text.
    Papers with no matches are excluded unless the caller passes ``max_results``
    large enough to surface the full table via ``search_brain_all``.
    """
    papers = parse_papers_table(path)
    if not papers:
        return []
    norm_papers = [
        (p, _normalize(p["title"] + " " + p["venue"] + " " + p["authors"])) for p in papers
    ]
    kw_tokens: List[str] = []
    for k in keywords:
        k_norm = _normalize(k)
        kw_tokens.append(k_norm)
        kw_tokens.extend(t for t in k_norm.split() if t)

    scored: List[tuple[int, Dict[str, str]]] = []
    for p, hay in norm_papers:
        score = 0
        for tok in kw_tokens:
            if not tok:
                continue
            if tok in hay:
                score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in scored[:max_results]]


def search_brain_all(path: Path = BRAIN_PATH, max_results: int = 10) -> List[Dict[str, str]]:
    """Return all seeded papers (regardless of keyword match) - coverage fallback."""
    return parse_papers_table(path)[:max_results]


def append_entry(entry: Dict[str, str], path: Path = BRAIN_PATH) -> bool:
    """Append a crawled entry under the update-log section. Returns True if appended."""
    doi = entry.get("doi_or_url", "").strip()
    if not doi:
        return False
    existing = load_existing_hashes(path)
    h = compute_hash(doi)
    if h in existing:
        return False
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    block = (
        f"\n### {date} - {entry.get('title', 'Untitled')}\n"
        f"- **Authors:** {entry.get('authors', 'Unknown')}\n"
        f"- **Year:** {entry.get('year', '')}\n"
        f"- **Venue:** {entry.get('venue', 'Unknown')}\n"
        f"- **DOI/URL:** {doi}\n"
        f"- **Tier:** {entry.get('tier', 'Tier 4')}\n"
        f"- **Relevance Score:** {entry.get('score', 'n/a')}/10\n"
        f"- **Key Finding:** {entry.get('abstract', 'No abstract available.')}\n"
    )
    content = path.read_text(encoding="utf-8")
    if UPDATE_LOG_HEADER not in content:
        content = content.rstrip() + "\n\n" + UPDATE_LOG_HEADER + "\n" + block
    else:
        content = content.rstrip() + block
    path.write_text(content, encoding="utf-8")
    return True