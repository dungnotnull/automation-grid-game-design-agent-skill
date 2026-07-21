"""automation_grid - production-grade automation-game grid logistics & throughput engine.

Public API:
    Recipe, RecipeRegistry          -> recipe graph
    solve_ratios, solve_grid        -> ratio / grid solver
    bottleneck_analysis             -> Little's Law bottleneck report
    balancer_design                 -> splitter-balancer topology
    power_pollution_summary         -> tradeoff accounting
    classify_verdict, Verdict       -> verdict categories
    build_registry, DEFAULT_REGISTRY -> seeded recipe database
"""
from .config import (
    KNOWLEDGE_CONFIG,
    BELT_THROUGHPUT,
    MACHINE_SPECS,
    MODULE_EFFECTS,
    EVIDENCE_TIERS,
    VERDICTS,
    QUALITY_GATES,
)
from .engine import (
    Recipe,
    RecipeRegistry,
    MachineConfig,
    StageResult,
    BottleneckReport,
    GridSolution,
    Verdict,
    machine_config,
    solve_ratios,
    solve_grid,
    belts_required,
    little_law,
    bottleneck_analysis,
    balancer_design,
    power_pollution_summary,
    classify_verdict,
    verdict_label,
    valid_verdicts,
)
from .recipes import build_registry, DEFAULT_REGISTRY
from .knowledge import (
    compute_hash,
    load_existing_hashes,
    parse_papers_table,
    search_brain,
    append_entry,
)

__version__ = "1.1.0"
__all__ = [
    "KNOWLEDGE_CONFIG",
    "BELT_THROUGHPUT",
    "MACHINE_SPECS",
    "MODULE_EFFECTS",
    "EVIDENCE_TIERS",
    "VERDICTS",
    "QUALITY_GATES",
    "Recipe",
    "RecipeRegistry",
    "MachineConfig",
    "StageResult",
    "BottleneckReport",
    "GridSolution",
    "Verdict",
    "machine_config",
    "solve_ratios",
    "solve_grid",
    "belts_required",
    "little_law",
    "bottleneck_analysis",
    "balancer_design",
    "power_pollution_summary",
    "classify_verdict",
    "verdict_label",
    "valid_verdicts",
    "build_registry",
    "DEFAULT_REGISTRY",
    "compute_hash",
    "load_existing_hashes",
    "parse_papers_table",
    "search_brain",
    "append_entry",
]
