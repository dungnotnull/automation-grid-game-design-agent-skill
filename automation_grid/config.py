import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent

# ---------------------------------------------------------------------------
# Knowledge crawl configuration (Semantic Scholar / ArXiv / RSS)
# ---------------------------------------------------------------------------
KNOWLEDGE_CONFIG = {
    "domain": "Automation-Game Grid Logistics & Throughput Optimization",
    "keywords": [
        "factory automation game",
        "production chain ratio optimization",
        "throughput bottleneck Little law",
        "belt balancer splitter",
        "factory game layout optimization",
        "recipe graph scheduling",
        "factorio satisfactory throughput",
    ],
    "arxiv_categories": ["cs.AI", "cs.CE", "cs.RO"],
    "arxiv_base": "https://export.arxiv.org/api/query",
    "semantic_scholar_base": "https://api.semanticscholar.org/graph/v1/paper/search",
    "semantic_scholar_fields": "title,authors,year,venue,externalIds,abstract,citationCount",
    "rss_feeds": [
        "https://forums.factorio.com/forum/feed.php",
        "https://www.reddit.com/r/factorio/.rss",
        "https://www.reddit.com/r/SatisfactoryGame/.rss",
        "https://www.reddit.com/r/DysonSphereProgram/.rss",
    ],
    "authoritative_docs": [
        "Proceedings of CHI PLAY (ACM)",
        "IEEE Transactions on Games",
        "Entertainment Computing - Elsevier",
        "Computers & Operations Research (flow/scheduling)",
        "Simulation & Gaming - SAGE",
        "Journal of Simulation",
        "Factorio Wiki (wiki.factorio.com)",
        "Satisfactory Wiki (satisfactory.wiki.gg)",
        "FactorioLab calculator (factoriolab.github.io)",
    ],
    "scoring_weights": {
        "recency": 0.4,
        "keyword_relevance": 0.4,
        "citation_count": 0.2,
    },
    "max_results_per_source": 10,
    "max_new_entries_per_run": 20,
    "request_timeout_seconds": 30,
    "max_retries": 3,
    "base_retry_delay_seconds": 2.0,
}

# ---------------------------------------------------------------------------
# Belt throughput tables (items per second, per game)
# ---------------------------------------------------------------------------
# All values in ITEMS PER SECOND for unit consistency with the engine's
# items/sec rate model.
#   Factorio:   yellow 15/s, red 30/s, blue 45/s (900/1800/2700 per min).
#   Satisfactory: Mk1..Mk6 = 60/120/270/480/780/1200 per min -> /60 per sec.
BELT_THROUGHPUT = {
    "factorio": {
        "transport-belt": 15.0,
        "fast-transport-belt": 30.0,
        "express-transport-belt": 45.0,
    },
    "satisfactory": {
        "mk1-conveyor": 1.0,
        "mk2-conveyor": 2.0,
        "mk3-conveyor": 4.5,
        "mk4-conveyor": 8.0,
        "mk5-conveyor": 13.0,
        "mk6-conveyor": 20.0,
    },
}

# Inserter / sorter approximations (items/sec at nominal stack size 1)
INSERTER_THROUGHPUT = {
    "factorio": {
        "burner-inserter": 0.83,
        "inserter": 0.83,
        "long-handed-inserter": 1.19,
        "fast-inserter": 2.31,
        "filter-inserter": 2.31,
        "stack-inserter": 4.62,  # with stack-size tech
    },
}

# ---------------------------------------------------------------------------
# Machine specifications (craft_speed multiplier at base game, power kW, pollution/min)
# ---------------------------------------------------------------------------
MACHINE_SPECS = {
    "factorio": {
        "assembling-machine-1": {"craft_speed": 0.75, "power_kw": 75.0, "pollution_per_min": 4.0},
        "assembling-machine-2": {"craft_speed": 1.00, "power_kw": 150.0, "pollution_per_min": 8.0},
        "assembling-machine-3": {"craft_speed": 1.25, "power_kw": 225.0, "pollution_per_min": 12.0},
        "chemical-plant": {"craft_speed": 1.00, "power_kw": 150.0, "pollution_per_min": 8.0},
        "oil-refinery": {"craft_speed": 1.00, "power_kw": 420.0, "pollution_per_min": 24.0},
        "electric-furnace": {"craft_speed": 2.00, "power_kw": 180.0, "pollution_per_min": 1.0},
        "stone-furnace": {"craft_speed": 1.00, "power_kw": 0.0, "pollution_per_min": 2.0},
        "steel-furnace": {"craft_speed": 2.00, "power_kw": 0.0, "pollution_per_min": 4.0},
        "centrifuge": {"craft_speed": 1.00, "power_kw": 350.0, "pollution_per_min": 12.0},
    },
    "satisfactory": {
        "constructor": {"craft_speed": 1.00, "power_kw": 4.0, "pollution_per_min": 0.0},
        "assembler": {"craft_speed": 1.00, "power_kw": 15.0, "pollution_per_min": 0.0},
        "manufacturer": {"craft_speed": 1.00, "power_kw": 55.0, "pollution_per_min": 0.0},
        "refinery": {"craft_speed": 1.00, "power_kw": 30.0, "pollution_per_min": 0.0},
        "smelter": {"craft_speed": 1.00, "power_kw": 4.0, "pollution_per_min": 0.0},
        "foundry": {"craft_speed": 1.00, "power_kw": 100.0, "pollution_per_min": 0.0},
        "blender": {"craft_speed": 1.00, "power_kw": 150.0, "pollution_per_min": 0.0},
        "particle-accelerator": {"craft_speed": 1.00, "power_kw": 250.0, "pollution_per_min": 0.0},
        "converter": {"craft_speed": 1.00, "power_kw": 55.0, "pollution_per_min": 0.0},
        "quantum-encoder": {"craft_speed": 1.00, "power_kw": 1500.0, "pollution_per_min": 0.0},
    },
}

# Module effects (Factorio): speed/productivity/efficiency by tier
MODULE_EFFECTS = {
    "factorio": {
        "speed-module-1": {"speed": 0.20, "productivity": 0.0, "energy": 0.50, "pollution": 0.0},
        "speed-module-2": {"speed": 0.30, "productivity": 0.0, "energy": 0.60, "pollution": 0.0},
        "speed-module-3": {"speed": 0.50, "productivity": 0.0, "energy": 0.70, "pollution": 0.0},
        "productivity-module-1": {"speed": -0.05, "productivity": 0.04, "energy": 0.40, "pollution": 0.05},
        "productivity-module-2": {"speed": -0.10, "productivity": 0.06, "energy": 0.60, "pollution": 0.07},
        "productivity-module-3": {"speed": -0.15, "productivity": 0.10, "energy": 0.80, "pollution": 0.10},
        "efficiency-module-1": {"speed": 0.0, "productivity": 0.0, "energy": -0.30, "pollution": 0.0},
        "efficiency-module-2": {"speed": 0.0, "productivity": 0.0, "energy": -0.40, "pollution": 0.0},
        "efficiency-module-3": {"speed": 0.0, "productivity": 0.0, "energy": -0.50, "pollution": 0.0},
    },
}

# Evidence hierarchy tiers (this domain)
EVIDENCE_TIERS = {
    "Tier 1": "Systematic review / meta-analysis / official standard",
    "Tier 2": "Peer-reviewed academic paper / RCT",
    "Tier 3": "Industry report / professional association guideline",
    "Tier 4": "News / blog / vendor material",
}

# Verdict categories for the advisor sub-skill
VERDICTS = [
    "Optimized Layout",
    "Conditional (bottleneck)",
    "Infeasible Target",
    "Inconclusive",
]

# Universal quality gates U1..U6 plus domain gates G1..G4
QUALITY_GATES = [
    {"id": "U1", "check": ">=3 sources cited, >=1 academic/authoritative"},
    {"id": "U2", "check": "Disclosure/limitations before recommendation"},
    {"id": "U3", "check": "Evidence hierarchy stated per source (Tier 1-4)"},
    {"id": "U4", "check": "Language matches user preference"},
    {"id": "U5", "check": "Output uses declared template (all sections)"},
    {"id": "U6", "check": "Every claim traceable to >=1 source or flagged"},
    {"id": "G1", "check": "Ratios computed from recipe graphs"},
    {"id": "G2", "check": "Bottlenecks identified via throughput analysis (Little's Law)"},
    {"id": "G3", "check": "Belt/logistics balancing specified (splitters/balancers)"},
    {"id": "G4", "check": "Power/pollution/space tradeoffs addressed"},
]

# Default log directory
LOG_DIR = ROOT / "logs"
LOG_LEVEL = os.environ.get("AUTOMATION_GRID_LOG_LEVEL", "INFO")
