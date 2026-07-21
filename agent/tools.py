"""agent.tools - rich tool definitions (JSON schemas + execution handlers).

A Tool bundles: a name, a human/agent-readable description, an input JSON
Schema, an output JSON Schema, and a Python handler. The ToolRegistry resolves
tools by name, validates inputs/outputs against the schemas, invokes the
handler inside a retry wrapper, and emits ``tool.invoked`` / ``tool.failed``
events on the bus.

``build_default_tools()`` registers the real engine-backed tools used by the
harness (ratio solver, Little's Law, balancer, verdict classifier, knowledge
search, etc.) so agents can invoke them dynamically.
"""
from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .errors import ToolNotFound, SchemaError
from .events import EventBus
from .schemas import validate_instance

# Ensure the sibling automation_grid package is importable when this module
# is loaded directly (e.g. via ``python -m agent.tools``).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from automation_grid import (  # noqa: E402
    DEFAULT_REGISTRY,
    balancer_design,
    belts_required,
    bottleneck_analysis,
    classify_verdict,
    little_law,
    machine_config,
    power_pollution_summary,
    search_brain,
    solve_grid,
    solve_ratios,
    valid_verdicts,
)
from automation_grid.engine import RecipeRegistry  # noqa: E402
from automation_grid.knowledge import append_entry, load_existing_hashes  # noqa: E402


Handler = Callable[..., Any]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    handler: Handler
    idempotent: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("tool name must be non-empty")
        if not callable(self.handler):
            raise TypeError("tool handler must be callable")
        if "type" not in self.input_schema or "type" not in self.output_schema:
            raise SchemaError("tool schemas must declare a top-level 'type'")

    def signature(self) -> Dict[str, Any]:
        """Agent-facing tool descriptor (name + description + input schema)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "idempotent": self.idempotent,
        }


class ToolRegistry:
    """Resolves + executes tools by name with schema validation."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFound(f"tool {name!r} not registered")
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> List[str]:
        return sorted(self._tools)

    def signatures(self) -> List[Dict[str, Any]]:
        return [self._tools[n].signature() for n in self.names()]

    def invoke(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool = self.get(name)
        try:
            validate_instance(arguments, tool.input_schema)
        except SchemaError as ex:
            self.bus.emit("tool.failed", tool=name, reason="invalid_input", error=str(ex))
            raise
        self.bus.emit("tool.invoked", tool=name, args=arguments)
        try:
            result = tool.handler(**arguments)
        except Exception as ex:  # noqa: BLE001 - re-raised after event
            self.bus.emit("tool.failed", tool=name, reason="handler_error", error=str(ex))
            raise
        try:
            validate_instance(result, tool.output_schema)
        except SchemaError as ex:
            self.bus.emit("tool.failed", tool=name, reason="invalid_output", error=str(ex))
            raise
        self.bus.emit("tool.completed", tool=name)
        return result


# ---------------------------------------------------------------------------
# Tool handlers (thin, real wrappers around the engine + knowledge layer)
# ---------------------------------------------------------------------------

def _grid_to_dict(sol: Any) -> Dict[str, Any]:
    """Serialise a GridSolution dataclass into a JSON-safe dict."""
    return {
        "target_item": sol.target_item,
        "target_rate": sol.target_rate,
        "verdict": sol.verdict.value,
        "power_kw_total": sol.power_kw_total,
        "pollution_per_min_total": sol.pollution_per_min_total,
        "belts_total": sol.belts_total,
        "bottleneck": {
            "stage": sol.bottleneck.bottleneck_stage,
            "utilization": sol.bottleneck.bottleneck_utilization,
            "throughput_cap": sol.bottleneck.throughput_cap,
            "buffer_size_seconds": sol.bottleneck.buffer_size_seconds,
            "recommendations": list(sol.bottleneck.recommendations),
            "stages": [list(s) for s in sol.bottleneck.stages],
        },
        "stages": [
            {
                "stage": s.stage,
                "machine": s.machine.machine,
                "count": s.count,
                "count_rounded": s.count_rounded,
                "output_item": s.output_item,
                "target_rate": s.target_rate,
                "utilization": s.utilization,
                "power_kw": s.power_kw,
                "pollution_per_min": s.pollution_per_min,
                "input_rates": dict(s.input_rates),
                "belts_in": dict(s.belts_in),
                "belts_out": dict(s.belts_out),
            }
            for s in sol.stages
        ],
        "notes": list(sol.notes),
    }


def _stages_to_list(stages: Iterable[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in stages:
        out.append({
            "stage": s.stage,
            "machine": s.machine.machine,
            "count": s.count,
            "count_rounded": s.count_rounded,
            "output_item": s.output_item,
            "target_rate": s.target_rate,
            "utilization": s.utilization,
            "power_kw": s.power_kw,
            "pollution_per_min": s.pollution_per_min,
            "input_rates": dict(s.input_rates),
            "belts_in": dict(s.belts_in),
            "belts_out": dict(s.belts_out),
        })
    return out


def _make_solve_grid_handler() -> Handler:
    def _h(target_item: str, target_rate: float, game: str,
           buffer_time_s: float = 2.0, data_available: bool = True) -> Dict[str, Any]:
        sol = solve_grid(target_item, float(target_rate), DEFAULT_REGISTRY, game,
                         buffer_time_s=float(buffer_time_s),
                         data_available=bool(data_available))
        return _grid_to_dict(sol)
    return _h


def _make_solve_ratios_handler() -> Handler:
    def _h(target_item: str, target_rate: float, game: str) -> List[Dict[str, Any]]:
        stages = solve_ratios(target_item, float(target_rate), DEFAULT_REGISTRY, game)
        return _stages_to_list(stages)
    return _h


def _balancer_handler(input_belts: int, output_belts: int) -> Dict[str, Any]:
    return balancer_design(int(input_belts), int(output_belts))


def _little_law_handler(throughput_lambda: float, waiting_time_s: float) -> Dict[str, Any]:
    return {
        "lambda": float(throughput_lambda),
        "W": float(waiting_time_s),
        "L": little_law(float(throughput_lambda), float(waiting_time_s)),
    }


def _belts_handler(rate_items_per_sec: float, game: str, belt: Optional[str] = None) -> Dict[str, Any]:
    n = belts_required(float(rate_items_per_sec), game, belt)
    return {"belts": n, "game": game, "rate_items_per_sec": float(rate_items_per_sec), "belt": belt}


def _classify_verdict_handler(bottleneck_utilization: float, feasible: bool,
                              data_available: bool = True) -> Dict[str, Any]:
    class _B:
        pass
    b = _B()
    b.bottleneck_utilization = float(bottleneck_utilization)
    v = classify_verdict(b, feasible=bool(feasible), data_available=bool(data_available))
    return {"verdict": v.value, "feasible": bool(feasible), "data_available": bool(data_available)}


def _power_pollution_handler(target_item: str, target_rate: float, game: str) -> Dict[str, Any]:
    stages = solve_ratios(target_item, float(target_rate), DEFAULT_REGISTRY, game)
    return power_pollution_summary(stages)


def _bottleneck_handler(target_item: str, target_rate: float, game: str,
                        buffer_time_s: float = 2.0) -> Dict[str, Any]:
    stages = solve_ratios(target_item, float(target_rate), DEFAULT_REGISTRY, game)
    rep = bottleneck_analysis(stages, buffer_time_s=float(buffer_time_s))
    return {
        "bottleneck_stage": rep.bottleneck_stage,
        "bottleneck_utilization": rep.bottleneck_utilization,
        "throughput_cap": rep.throughput_cap,
        "buffer_size_seconds": rep.buffer_size_seconds,
        "recommendations": list(rep.recommendations),
        "stages": [list(s) for s in rep.stages],
    }


def _machine_config_handler(machine: str, game: str, modules: Optional[List[str]] = None) -> Dict[str, Any]:
    mc = machine_config(machine, game, modules=modules or [])
    return {
        "machine": mc.machine,
        "game": mc.game,
        "craft_speed": mc.craft_speed,
        "speed_bonus": mc.speed_bonus,
        "productivity_bonus": mc.productivity_bonus,
        "effective_craft_speed": mc.effective_craft_speed(),
        "effective_output_multiplier": mc.effective_output_multiplier(),
        "power_kw": mc.power_kw,
        "pollution_per_min": mc.pollution_per_min,
        "module_effects": dict(mc.module_effects),
    }


def _search_brain_handler(keywords: List[str], max_results: int = 5) -> Dict[str, Any]:
    rows = search_brain(list(keywords), max_results=int(max_results))
    return {"count": len(rows), "results": rows}


def _list_recipes_handler(game: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, List[str]] = {}
    for r in DEFAULT_REGISTRY.items():
        out.setdefault(r.game, []).extend(r.outputs.keys())
    if game:
        return {"game": game, "items": sorted(set(out.get(game, [])))}
    return {g: sorted(set(items)) for g, items in out.items()}


def _verdicts_handler() -> Dict[str, Any]:
    return {"verdicts": valid_verdicts()}


def _append_knowledge_handler(entry: Dict[str, str]) -> Dict[str, Any]:
    appended = append_entry(dict(entry))
    return {"appended": bool(appended), "dedup_hash_count": len(load_existing_hashes())}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

_STRING = {"type": "string", "minLength": 1}
_NUMBER = {"type": "number", "minimum": 0}
_GAME_ENUM = {"type": "string", "enum": ["factorio", "satisfactory", "dsp"]}

_SOLVE_GRID_IN = {
    "type": "object",
    "properties": {
        "target_item": _STRING,
        "target_rate": _NUMBER,
        "game": _GAME_ENUM,
        "buffer_time_s": {"type": "number", "minimum": 0},
        "data_available": {"type": "boolean"},
    },
    "required": ["target_item", "target_rate", "game"],
    "additionalProperties": False,
}

_OBJECT_OUT = {"type": "object"}
_ARRAY_OUT = {"type": "array"}


def build_default_tools(bus: Optional[EventBus] = None) -> ToolRegistry:
    """Register the production tool set backed by the automation_grid engine."""
    reg = ToolRegistry(bus=bus)

    reg.register(Tool(
        name="solve_grid",
        description="End-to-end solve: ratios -> throughput -> tradeoffs -> verdict for a target item/rate.",
        input_schema=_SOLVE_GRID_IN,
        output_schema=_OBJECT_OUT,
        handler=_make_solve_grid_handler(),
    ))
    reg.register(Tool(
        name="solve_ratios",
        description="Compute the multi-stage ratio tree (reverse demand propagation) for a target item/rate.",
        input_schema={
            "type": "object",
            "properties": {"target_item": _STRING, "target_rate": _NUMBER, "game": _GAME_ENUM},
            "required": ["target_item", "target_rate", "game"],
            "additionalProperties": False,
        },
        output_schema=_ARRAY_OUT,
        handler=_make_solve_ratios_handler(),
    ))
    reg.register(Tool(
        name="balancer_design",
        description="Design an n:m belt balancer topology (splitter count + balance guarantee).",
        input_schema={
            "type": "object",
            "properties": {
                "input_belts": {"type": "integer", "minimum": 1},
                "output_belts": {"type": "integer", "minimum": 1},
            },
            "required": ["input_belts", "output_belts"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_balancer_handler,
    ))
    reg.register(Tool(
        name="little_law",
        description="Apply Little's Law L = lambda * W to size buffers / expected items in system.",
        input_schema={
            "type": "object",
            "properties": {
                "throughput_lambda": {"type": "number", "minimum": 0},
                "waiting_time_s": {"type": "number", "minimum": 0},
            },
            "required": ["throughput_lambda", "waiting_time_s"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_little_law_handler,
    ))
    reg.register(Tool(
        name="belts_required",
        description="Number of belts needed to carry a given items/sec rate for a game (optional belt tier).",
        input_schema={
            "type": "object",
            "properties": {
                "rate_items_per_sec": _NUMBER,
                "game": _GAME_ENUM,
                "belt": {"type": ["string", "null"]},
            },
            "required": ["rate_items_per_sec", "game"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_belts_handler,
    ))
    reg.register(Tool(
        name="classify_verdict",
        description="Classify the final verdict from bottleneck utilization / feasibility / data availability.",
        input_schema={
            "type": "object",
            "properties": {
                "bottleneck_utilization": {"type": "number", "minimum": 0},
                "feasible": {"type": "boolean"},
                "data_available": {"type": "boolean"},
            },
            "required": ["bottleneck_utilization", "feasible"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_classify_verdict_handler,
    ))
    reg.register(Tool(
        name="power_pollution_summary",
        description="Aggregate power/pollution/machine-count tradeoffs for a target item/rate.",
        input_schema={
            "type": "object",
            "properties": {"target_item": _STRING, "target_rate": _NUMBER, "game": _GAME_ENUM},
            "required": ["target_item", "target_rate", "game"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_power_pollution_handler,
    ))
    reg.register(Tool(
        name="bottleneck_analysis",
        description="Identify the bottleneck stage (highest utilization) + Little's Law buffer for a target.",
        input_schema={
            "type": "object",
            "properties": {
                "target_item": _STRING, "target_rate": _NUMBER, "game": _GAME_ENUM,
                "buffer_time_s": {"type": "number", "minimum": 0},
            },
            "required": ["target_item", "target_rate", "game"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_bottleneck_handler,
    ))
    reg.register(Tool(
        name="machine_config",
        description="Build a machine configuration (craft speed, power, pollution, module effects).",
        input_schema={
            "type": "object",
            "properties": {
                "machine": _STRING, "game": _GAME_ENUM,
                "modules": {"type": ["array", "null"], "items": _STRING},
            },
            "required": ["machine", "game"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_machine_config_handler,
    ))
    reg.register(Tool(
        name="search_brain",
        description="Query SECOND-KNOWLEDGE-BRAIN.md for tier-labeled academic citations matching keywords.",
        input_schema={
            "type": "object",
            "properties": {
                "keywords": {"type": "array", "items": _STRING, "minItems": 1},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["keywords"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_search_brain_handler,
    ))
    reg.register(Tool(
        name="list_recipes",
        description="List seeded recipe output items, optionally filtered by game.",
        input_schema={
            "type": "object",
            "properties": {"game": {"type": ["string", "null"]}},
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_list_recipes_handler,
    ))
    reg.register(Tool(
        name="valid_verdicts",
        description="Return the declared set of verdict categories.",
        input_schema={"type": "object", "additionalProperties": False},
        output_schema=_OBJECT_OUT,
        handler=_verdicts_handler,
    ))
    reg.register(Tool(
        name="append_knowledge",
        description="Append a crawled knowledge entry to SECOND-KNOWLEDGE-BRAIN.md (dedup by DOI/URL).",
        input_schema={
            "type": "object",
            "properties": {
                "entry": {
                    "type": "object",
                    "properties": {
                        "title": _STRING,
                        "authors": _STRING,
                        "year": _STRING,
                        "venue": _STRING,
                        "doi_or_url": _STRING,
                        "abstract": _STRING,
                        "tier": _STRING,
                        "score": _STRING,
                    },
                    "required": ["title", "doi_or_url"],
                    "additionalProperties": False,
                },
            },
            "required": ["entry"],
            "additionalProperties": False,
        },
        output_schema=_OBJECT_OUT,
        handler=_append_knowledge_handler,
        idempotent=False,
    ))
    return reg
