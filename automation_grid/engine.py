"""automation_grid.engine - automation-game grid logistics & throughput engine.

Production-grade computational core for factory/automation games (Factorio,
Satisfactory, Dyson Sphere Program). Implements:

  * recipe-graph ratio solving (reverse demand propagation)
  * throughput / bottleneck analysis via Little's Law
  * belt / logistics balancing (splitter-balancer trees, lane balancing)
  * power / pollution / space tradeoff accounting
  * best/base/worst scaling scenarios
  * verdict classification (Optimized / Conditional / Infeasible / Inconclusive)

The engine is intentionally pure-Python (no third-party deps) so it can run in
any production environment and be unit-tested deterministically.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from .config import BELT_THROUGHPUT, MACHINE_SPECS, MODULE_EFFECTS, VERDICTS


class Verdict(str, Enum):
    OPTIMIZED = "Optimized Layout"
    CONDITIONAL = "Conditional (bottleneck)"
    INFEASIBLE = "Infeasible Target"
    INCONCLUSIVE = "Inconclusive"


@dataclass(frozen=True)
class Recipe:
    """A single recipe.

    inputs/outputs map item name -> quantity per single craft.
    craft_time is seconds for one craft at base machine craft_speed == 1.0.
    ``machine`` is the canonical machine used to craft this recipe.
    """
    name: str
    game: str
    inputs: Dict[str, float]
    outputs: Dict[str, float]
    craft_time: float
    machine: str
    category: str = "crafting"

    def base_rate(self, output_item: str) -> float:
        """Items per second of ``output_item`` produced by one base machine."""
        out_qty = self.outputs.get(output_item, 0.0)
        if self.craft_time <= 0:
            raise ValueError(f"recipe {self.name!r} has non-positive craft_time")
        return out_qty / self.craft_time

    def demand_per_output(self, output_item: str) -> Dict[str, float]:
        """Inputs consumed per unit of output_item produced (at base speed)."""
        rate = self.base_rate(output_item)
        if rate <= 0:
            return {}
        return {item: qty / self.craft_time / rate for item, qty in self.inputs.items()}


@dataclass
class MachineConfig:
    """Runtime configuration for a machine in a stage."""
    machine: str
    game: str
    craft_speed: float = 1.0
    speed_bonus: float = 0.0
    productivity_bonus: float = 0.0
    module_slots: int = 0
    power_kw: float = 0.0
    pollution_per_min: float = 0.0
    module_effects: Dict[str, float] = field(default_factory=dict)

    def effective_craft_speed(self) -> float:
        return max(self.craft_speed * (1.0 + self.speed_bonus), 1e-9)

    def effective_output_multiplier(self) -> float:
        return 1.0 + self.productivity_bonus


@dataclass
class StageResult:
    stage: str
    recipe: Recipe
    machine: MachineConfig
    count: float                  # exact machine count required
    count_rounded: int            # ceil to whole machines
    output_item: str
    target_rate: float            # items/sec produced by this stage
    input_rates: Dict[str, float] = field(default_factory=dict)
    utilization: float = 1.0      # fraction of installed capacity actually used
    power_kw: float = 0.0
    pollution_per_min: float = 0.0
    belts_in: Dict[str, int] = field(default_factory=dict)
    belts_out: Dict[str, int] = field(default_factory=dict)


@dataclass
class BottleneckReport:
    bottleneck_stage: Optional[str]
    bottleneck_utilization: float
    stages: List[Tuple[str, float]]   # (stage, utilization)
    throughput_cap: float            # items/sec at bottleneck stage
    buffer_size_seconds: float       # Little's Law W = L * (W time) suggestion
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GridSolution:
    target_item: str
    target_rate: float
    stages: List[StageResult]
    bottleneck: BottleneckReport
    power_kw_total: float
    pollution_per_min_total: float
    belts_total: int
    verdict: Verdict
    notes: List[str] = field(default_factory=list)


def machine_config(machine: str, game: str, modules: Optional[Iterable[str]] = None) -> MachineConfig:
    """Build a MachineConfig from the seeded specs, applying module effects."""
    specs = MACHINE_SPECS.get(game, {}).get(machine)
    if specs is None:
        raise KeyError(f"unknown machine {machine!r} for game {game!r}")
    cfg = MachineConfig(
        machine=machine,
        game=game,
        craft_speed=specs["craft_speed"],
        power_kw=specs["power_kw"],
        module_slots=int(specs.get("module_slots", 0)),
    )
    if modules:
        per_module: Dict[str, float] = {}
        for m in modules:
            eff = MODULE_EFFECTS.get(game, {}).get(m)
            if eff is None:
                raise KeyError(f"unknown module {m!r} for game {game!r}")
            for k, v in eff.items():
                per_module[k] = per_module.get(k, 0.0) + v
        cfg.speed_bonus += per_module.get("speed", 0.0)
        cfg.productivity_bonus += per_module.get("productivity", 0.0)
        cfg.module_effects = per_module
    return cfg


# ---------------------------------------------------------------------------
# Recipe registry
# ---------------------------------------------------------------------------
class RecipeRegistry:
    """In-memory recipe graph keyed by output item."""

    def __init__(self) -> None:
        self._by_output: Dict[Tuple[str, str], Recipe] = {}

    def add(self, recipe: Recipe) -> None:
        for out in recipe.outputs:
            self._by_output[(recipe.game, out)] = recipe

    def get(self, game: str, item: str) -> Optional[Recipe]:
        return self._by_output.get((game, item))

    def has(self, game: str, item: str) -> bool:
        return (game, item) in self._by_output

    def items(self) -> Iterable[Recipe]:
        seen = set()
        for r in self._by_output.values():
            if id(r) not in seen:
                seen.add(id(r))
                yield r


# ---------------------------------------------------------------------------
# Ratio solver: reverse demand propagation
# ---------------------------------------------------------------------------
def solve_ratios(
    target_item: str,
    target_rate: float,
    registry: RecipeRegistry,
    game: str,
    machine_map: Optional[Dict[str, MachineConfig]] = None,
    max_depth: int = 32,
) -> List[StageResult]:
    """Compute the full multi-stage ratio tree needed to produce ``target_rate``
    items/sec of ``target_item``.

    Returns a list of StageResult objects (post-order: deepest inputs first).
    Raises ``KeyError`` if a required recipe is missing and ``RecursionError``
    if a recipe cycle is detected (e.g. catalyst loops handled by max_depth).
    """
    if target_rate <= 0:
        raise ValueError("target_rate must be positive")

    machine_map = machine_map or {}
    stages: List[StageResult] = []
    visited: Dict[Tuple[str, str], float] = {}

    def demand(item: str, rate: float, depth: int) -> None:
        if depth > max_depth:
            raise RecursionError(f"recipe depth exceeded {max_depth} (possible cycle)")
        recipe = registry.get(game, item)
        if recipe is None:
            # Raw/external input: record as an input requirement on caller
            visited[("_RAW", item)] = visited.get(("_RAW", item), 0.0) + rate
            return
        cfg = machine_map.get(recipe.machine) or machine_config(recipe.machine, game)
        eff_speed = cfg.effective_craft_speed()
        prod_mult = cfg.effective_output_multiplier()
        per_machine_rate = recipe.base_rate(item) * eff_speed * prod_mult
        if per_machine_rate <= 0:
            raise ValueError(f"zero output rate for recipe {recipe.name!r}")
        count = rate / per_machine_rate
        count_rounded = max(1, math.ceil(count - 1e-9))
        utilization = count / count_rounded

        # power: scaled by count_rounded (machines draw power when running)
        specs = MACHINE_SPECS[game][recipe.machine]
        power_kw = specs["power_kw"] * count_rounded
        pollution = specs["pollution_per_min"] * count_rounded

        # input rates (per second) consumed by this stage
        input_rates: Dict[str, float] = {}
        for in_item, qty in recipe.inputs.items():
            consumed = (qty / recipe.craft_time) * count_rounded * eff_speed
            input_rates[in_item] = consumed

        # belts in/out
        belts_in = {it: belts_required(r, game) for it, r in input_rates.items()}
        belts_out = {item: belts_required(rate, game)}

        stage = StageResult(
            stage=recipe.name,
            recipe=recipe,
            machine=cfg,
            count=count,
            count_rounded=count_rounded,
            output_item=item,
            target_rate=rate,
            input_rates=input_rates,
            utilization=utilization,
            power_kw=power_kw,
            pollution_per_min=pollution,
            belts_in=belts_in,
            belts_out=belts_out,
        )
        stages.append(stage)

        # propagate demand upstream
        for in_item, qty in recipe.inputs.items():
            child_rate = (qty / recipe.craft_time) * count_rounded * eff_speed
            demand(in_item, child_rate, depth + 1)

    demand(target_item, target_rate, 0)
    return stages


def belts_required(rate_items_per_sec: float, game: str, belt: Optional[str] = None) -> int:
    """Number of belts needed to carry ``rate_items_per_sec``.

    If ``belt`` is None, picks the highest-tier belt available for the game.
    """
    tiers = BELT_THROUGHPUT.get(game)
    if not tiers:
        raise KeyError(f"no belt throughput table for game {game!r}")
    if belt is None:
        belt = max(tiers, key=lambda k: tiers[k])
    capacity = tiers[belt]
    if capacity <= 0:
        raise ValueError(f"zero capacity belt {belt!r}")
    return max(1, math.ceil(rate_items_per_sec / capacity - 1e-9))


# ---------------------------------------------------------------------------
# Bottleneck analysis via Little's Law
# ---------------------------------------------------------------------------
def little_law(throughput_lambda: float, waiting_time_s: float) -> float:
    """L = lambda * W  (expected items in system)."""
    return throughput_lambda * waiting_time_s


def bottleneck_analysis(stages: List[StageResult], buffer_time_s: float = 2.0) -> BottleneckReport:
    """Identify the bottleneck stage (lowest throughput utilization headroom).

    The bottleneck is the stage whose output capacity most tightly bounds the
    requested throughput, i.e. the stage with the highest installed utilization.
    Little's Law is applied to recommend a buffer that smooths stage jitter.
    """
    if not stages:
        return BottleneckReport(
            bottleneck_stage=None,
            bottleneck_utilization=0.0,
            stages=[],
            throughput_cap=0.0,
            buffer_size_seconds=0.0,
            recommendations=["No stages provided; cannot analyze bottlenecks."],
        )
    ordered = sorted(stages, key=lambda s: s.utilization, reverse=True)
    b = ordered[0]
    throughput_cap = b.target_rate / b.utilization if b.utilization > 0 else 0.0
    buffer = little_law(b.target_rate, buffer_time_s)

    recs: List[str] = []
    if b.utilization >= 0.98:
        recs.append(
            f"Stage '{b.stage}' is at {b.utilization*100:.1f}% utilization (capacity-bound). "
            f"Add 1+ {b.machine.machine} or upgrade craft speed (modules/beacons) to relieve the bottleneck."
        )
    elif b.utilization >= 0.85:
        recs.append(
            f"Stage '{b.stage}' is near capacity ({b.utilization*100:.1f}%). "
            f"Prefer a small buffer (>= {buffer:.1f} items) to absorb stage jitter."
        )
    else:
        recs.append(
            f"No binding bottleneck. Stage '{b.stage}' has the tightest utilization "
            f"({b.utilization*100:.1f}%); remaining headroom supports {((1/b.utilization)-1)*100:.0f}% scale-up."
        )
    recs.append(
        f"Little's Law buffer (W={buffer_time_s}s, L=lambda*W): "
        f"hold ~{buffer:.1f} items at stage '{b.stage}'."
    )
    return BottleneckReport(
        bottleneck_stage=b.stage,
        bottleneck_utilization=b.utilization,
        stages=[(s.stage, s.utilization) for s in ordered],
        throughput_cap=throughput_cap,
        buffer_size_seconds=buffer_time_s,
        recommendations=recs,
    )


# ---------------------------------------------------------------------------
# Splitter / balancer design (Factorio-style n:m balancers)
# ---------------------------------------------------------------------------
def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def balancer_design(input_belts: int, output_belts: int) -> Dict[str, object]:
    """Design a belt balancer tree.

    A throughput-ideal n:m balancer can be built as an n:n balancer followed by
    a merge/split fan-out. For Factorio, throughput-balanced n:n balancers exist
    for power-of-two n (1:1, 2:2, 4:4, 8:8); other sizes use a closest PoT
    balancer plus lane balancing. This function returns the recommended
    balancer topology and splitter count.
    """
    if input_belts <= 0 or output_belts <= 0:
        raise ValueError("belt counts must be positive")
    if input_belts == 1 and output_belts == 1:
        return {"topology": "passthrough", "splitters": 0, "balanced": True,
                "notes": "1:1 needs no splitter."}

    n = input_belts
    m = output_belts
    # Nearest power of two >= max(n,m)
    pot = 1
    while pot < max(n, m):
        pot *= 2
    # An n:n PoT balancer uses (n - 1) splitters in a standard splitter tree,
    # then we need a 1:m split from the balanced lanes.
    if n == m and is_power_of_two(n):
        splitters = n - 1
        topology = f"{n}:{m} throughput balancer (splitter tree)"
        balanced = True
        notes = f"Standard {n}:{m} balancer; all lanes throughput-balanced."
    else:
        # Combine an n:n PoT balancer (scaled) with lane merging to m outputs.
        balancer_splitters = pot - 1
        # extra splitters to redistribute pot balanced lanes down to m outputs
        extra = max(0, pot - m)
        splitters = balancer_splitters + extra
        topology = f"{n}:{m} via {pot}:{pot} balancer + lane merge/split"
        balanced = (n % m == 0) or (m % n == 0)
        notes = (
            f"Use a {pot}:{pot} throughput balancer, then merge/split to {m} output lanes. "
            + ("Output lanes are throughput-balanced." if balanced else
               "Output lanes are lane-balanced but not fully throughput-balanced; "
               "add lane balancers if exact throughput is required.")
        )
    return {
        "topology": topology,
        "splitters": splitters,
        "balanced": balanced,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Power / pollution / space tradeoff accounting
# ---------------------------------------------------------------------------
def power_pollution_summary(stages: List[StageResult]) -> Dict[str, float]:
    power = sum(s.power_kw for s in stages)
    pollution = sum(s.pollution_per_min for s in stages)
    machines = sum(s.count_rounded for s in stages)
    return {
        "power_kw_total": power,
        "pollution_per_min_total": pollution,
        "machine_count_total": machines,
        "power_per_machine_kw": power / machines if machines else 0.0,
        "pollution_per_machine_per_min": pollution / machines if machines else 0.0,
    }


# ---------------------------------------------------------------------------
# Verdict classification
# ---------------------------------------------------------------------------
def classify_verdict(
    bottleneck: BottleneckReport,
    feasible: bool,
    data_available: bool = True,
) -> Verdict:
    if not data_available:
        return Verdict.INCONCLUSIVE
    if not feasible:
        return Verdict.INFEASIBLE
    if bottleneck.bottleneck_utilization >= 0.98:
        return Verdict.CONDITIONAL
    return Verdict.OPTIMIZED


# ---------------------------------------------------------------------------
# Full grid solve
# ---------------------------------------------------------------------------
def solve_grid(
    target_item: str,
    target_rate: float,
    registry: RecipeRegistry,
    game: str,
    machine_map: Optional[Dict[str, MachineConfig]] = None,
    buffer_time_s: float = 2.0,
    data_available: bool = True,
) -> GridSolution:
    """End-to-end solve: ratios -> throughput -> tradeoffs -> verdict."""
    if not data_available:
        return GridSolution(
            target_item=target_item,
            target_rate=target_rate,
            stages=[],
            bottleneck=BottleneckReport(None, 0.0, [], 0.0, 0.0,
                                        ["DATA UNAVAILABLE: degraded-mode output."]),
            power_kw_total=0.0,
            pollution_per_min_total=0.0,
            belts_total=0,
            verdict=Verdict.INCONCLUSIVE,
            notes=["Degraded mode: primary sources unavailable; no fabrication attempted."],
        )
    stages = solve_ratios(target_item, target_rate, registry, game, machine_map)
    bottleneck = bottleneck_analysis(stages, buffer_time_s)
    summary = power_pollution_summary(stages)
    belts_total = sum(sum(s.belts_in.values()) + sum(s.belts_out.values()) for s in stages)
    # If no recipe exists for the target item (stages empty) we cannot produce
    # a layout verdict honestly -> Inconclusive rather than a misleading
    # "Optimized Layout" with zero stages.
    verdict = classify_verdict(bottleneck, feasible=True,
                               data_available=data_available and bool(stages))
    notes: List[str] = []
    if data_available and not stages:
        notes.append(
            "DATA UNAVAILABLE: no seeded recipe for target item "
            f"{target_item!r}; treated as raw input. Verdict -> Inconclusive."
        )
    if bottleneck.bottleneck_utilization >= 0.98:
        notes.append("Capacity-bound: scale the bottleneck stage before adding downstream load.")
    if summary["pollution_per_min_total"] > 0:
        notes.append("Pollution > 0: consider efficiency modules or green power.")
    return GridSolution(
        target_item=target_item,
        target_rate=target_rate,
        stages=stages,
        bottleneck=bottleneck,
        power_kw_total=summary["power_kw_total"],
        pollution_per_min_total=summary["pollution_per_min_total"],
        belts_total=belts_total,
        verdict=verdict,
        notes=notes,
    )


def verdict_label(v: Verdict) -> str:
    return v.value


def valid_verdicts() -> List[str]:
    return list(VERDICTS)
