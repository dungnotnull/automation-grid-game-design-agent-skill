"""agent.skill_handlers - concrete per-skill execution handlers.

Each handler derives its inputs from the shared SessionState, calls the LLM
provider (deterministic by default) to produce a schema-validated structured
output, persists the result back into state, and returns it. Handlers are
plain functions so they are trivially unit-testable and free of side effects
beyond mutating the passed-in state.
"""
from __future__ import annotations

from typing import Any, Callable, Dict

from .errors import LLMError
from .events import EventBus
from .llm import LLMProvider
from .state import SessionState
from .tools import ToolRegistry


def _keywords_from(state: SessionState) -> list[str]:
    req = state.requirements or {}
    analysis = state.analysis or {}
    kws = [req.get("game", "factorio")]
    bottleneck = analysis.get("bottleneck", {})
    if bottleneck.get("stage"):
        kws.append(bottleneck["stage"])
    kws.extend(["throughput bottleneck", "Little law", "production chain"])
    return kws


def _completed_skills(state: SessionState) -> set[str]:
    return {h["skill"] for h in state.history if h.get("event") == "completed"}


def gather_requirements(state: SessionState, tools: ToolRegistry,
                        llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    inputs = {"query": state.user_query}
    out = llm.structured("gather_requirements", inputs)
    state.requirements = out
    state.language = out.get("language", state.language)
    state.add_history("gather_requirements", "completed", fields=list(out.keys()))
    return out


def evidence_collector(state: SessionState, tools: ToolRegistry,
                       llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    req = state.requirements or {}
    inputs = {"game": req.get("game", "factorio"),
              "target_item": req.get("target_item", "")}
    out = llm.structured("evidence_collector", inputs)
    state.evidence = out
    state.degradation_level = max(state.degradation_level, int(out.get("degradation_level", 0)))
    state.add_history("evidence_collector", "completed", fields=list(out.keys()))
    return out


def core_analysis(state: SessionState, tools: ToolRegistry,
                  llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    req = state.requirements or {}
    inputs = {
        "game": req.get("game", "factorio"),
        "target_item": req.get("target_item", "electronic-circuit"),
        "target_rate": float(req.get("target_rate", 10.0)),
        "data_available": state.degradation_level < 4,
    }
    out = llm.structured("core_analysis", inputs)
    if inputs["data_available"] and len(out.get("stages", [])) == 0:
        # no seeded recipe for the target item -> missing input (level 3)
        state.degradation_level = max(state.degradation_level, 3)
    state.analysis = out
    state.add_history("core_analysis", "completed", verdict=out.get("engine_verdict"))
    return out


def knowledge_updater(state: SessionState, tools: ToolRegistry,
                      llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    inputs = {"keywords": _keywords_from(state)}
    out = llm.structured("knowledge_updater", inputs)
    state.knowledge = out
    state.add_history("knowledge_updater", "completed", coverage=out.get("coverage"))
    return out


def advisor(state: SessionState, tools: ToolRegistry,
            llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    inputs = {
        "analysis": state.analysis or {},
        "knowledge": state.knowledge or {},
        "degradation_level": state.degradation_level,
        "data_available": state.degradation_level < 3,
    }
    out = llm.structured("advisor", inputs)
    state.verdict = out
    state.add_history("advisor", "completed", verdict=out.get("verdict"))
    return out


# Mapping of each gate to the skill that owns it. A gate is only "applicable"
# (and thus enforced) when its owning skill actually ran for this run.
GATE_OWNER = {
    "U1": "evidence_collector",
    "U2": "advisor",
    "U3": "evidence_collector",
    "U4": "gather_requirements",
    "U5": "quality_gate",
    "U6": "advisor",
    "G1": "core_analysis",
    "G2": "core_analysis",
    "G3": "core_analysis",
    "G4": "core_analysis",
}


def quality_gate(state: SessionState, tools: ToolRegistry,
                 llm: LLMProvider, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Run the U1-U6 + G1-G4 gates that are applicable to this run.

    A gate is applicable iff its owning skill completed. This keeps the
    domain gates (G1-G4) from failing explain-only runs that intentionally
    skip the production-line analysis.
    """
    results = []
    req = state.requirements or {}
    ev = state.evidence or {}
    an = state.analysis or {}
    kn = state.knowledge or {}
    vd = state.verdict or {}
    ran = _completed_skills(state)
    ran.add("quality_gate")  # this skill is running now

    def _gate(gid: str, ok: bool, detail: str = "", applicable: bool = True) -> None:
        if not applicable:
            state.add_gate(gid, True, "n/a (owning skill not run)")
            results.append({"gate": gid, "passed": True, "applicable": False, "detail": "n/a"})
            return
        state.add_gate(gid, ok, detail)
        results.append({"gate": gid, "passed": bool(ok), "applicable": True, "detail": detail})

    def _applicable(gid: str) -> bool:
        return GATE_OWNER.get(gid) in ran

    sources = list(ev.get("authoritative_docs", [])) + list(kn.get("citations", []))
    _gate("U1", len(sources) >= 3, f"{len(sources)} sources", _applicable("U1"))
    _gate("U2", bool(vd.get("disclosure")), "disclosure present" if vd.get("disclosure") else "missing", _applicable("U2"))
    tiers_ok = all("tier" in s for s in sources) if sources else False
    _gate("U3", tiers_ok, "all sources tier-tagged" if tiers_ok else "untagged sources", _applicable("U3"))
    _gate("U4", state.language == req.get("language", state.language), f"lang={state.language}", _applicable("U4"))

    # U5 (template completeness) is applicable only when core_analysis ran.
    u5_applicable = "core_analysis" in ran
    if u5_applicable:
        u5_ok = all(k in an for k in ("stages", "bottleneck", "tradeoffs", "scenarios")) and all(
            k in vd for k in ("verdict", "scenarios", "key_risks", "evidence_chain", "remediation"))
    else:
        u5_ok = True
    _gate("U5", u5_ok, "required sections present" if u5_ok else "missing sections", u5_applicable)

    _gate("U6", bool(vd.get("evidence_chain")), "evidence chain present", _applicable("U6"))
    _gate("G1", len(an.get("stages", [])) >= 1, f"{len(an.get('stages', []))} stages", _applicable("G1"))
    _gate("G2", an.get("bottleneck", {}).get("stage") is not None, "bottleneck identified", _applicable("G2"))
    belts_ok = any(bool(s.get("belts_in") or s.get("belts_out")) for s in an.get("stages", []))
    _gate("G3", belts_ok, "belt counts specified", _applicable("G3"))
    _gate("G4", bool(an.get("tradeoffs")), "tradeoffs present", _applicable("G4"))

    applicable_results = [r for r in results if r.get("applicable", True)]
    passed = sum(1 for r in applicable_results if r["passed"])
    total = len(applicable_results)
    state.add_history("quality_gate", "completed", passed=passed, total=total)
    return {"gates": results, "passed": passed, "total": total,
            "all_passed": passed == total}


HANDLERS: Dict[str, Callable[[SessionState, ToolRegistry, LLMProvider, Dict[str, Any]], Dict[str, Any]]] = {
    "gather_requirements": gather_requirements,
    "evidence_collector": evidence_collector,
    "core_analysis": core_analysis,
    "knowledge_updater": knowledge_updater,
    "advisor": advisor,
    "quality_gate": quality_gate,
}