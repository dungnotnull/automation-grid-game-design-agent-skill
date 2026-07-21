"""agent.runner - end-to-end harness orchestrator.

The HarnessRunner wires together the skill registry, tool registry, hooks,
context window, LLM provider and router, then executes the routed skill
sequence with production-grade error handling and graceful degradation. It
renders the final markdown report (matching the ``skills/main.md`` output
template) and returns a structured RunResult.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import ContextWindow, TokenCounter
from .errors import AgentError, DegradedMode
from .events import EventBus
from .hooks import HookManager, Hooks
from .llm import DeterministicProvider, LLMProvider, build_provider
from .registry import SkillRegistry, load_skill_definitions
from .router import ChainOfThoughtRouter, RoutingDecision
from .state import SessionState
from .tools import ToolRegistry, build_default_tools

_ROOT = Path(__file__).resolve().parent.parent
_DEFINITIONS = _ROOT / "skills" / "definitions"


@dataclass
class RunResult:
    state: SessionState
    decision: RoutingDecision
    report: str
    ok: bool
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "run_id": self.state.run_id,
            "intent": self.decision.intent,
            "verdict": self.state.verdict.get("verdict", ""),
            "tokens_used": self.state.tokens_used,
            "degradation_level": self.state.degradation_level,
            "gates_passed": sum(1 for g in self.state.gate_results if g.get("passed")),
            "gates_total": len(self.state.gate_results),
            "failures": self.failures,
        }


class HarnessRunner:
    """Production-grade orchestrator for the automation-grid-game-design skill."""

    def __init__(
        self,
        *,
        bus: Optional[EventBus] = None,
        tools: Optional[ToolRegistry] = None,
        skills: Optional[SkillRegistry] = None,
        llm: Optional[LLMProvider] = None,
        router: Optional[ChainOfThoughtRouter] = None,
        hooks: Optional[HookManager] = None,
        context: Optional[ContextWindow] = None,
        definitions_dir: Optional[Path] = None,
        token_budget: int = 8192,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        logger: Any = None,
    ) -> None:
        self.bus = bus or EventBus()
        self.tools = tools or build_default_tools(self.bus)
        self.skills = skills or load_skill_definitions(definitions_dir or _DEFINITIONS, self.bus)
        self.llm = llm or build_provider(api_key=api_key, base_url=base_url, model=model, bus=self.bus)
        self.router = router or ChainOfThoughtRouter(self.bus)
        self.hooks = hooks or HookManager(self.bus)
        self.context = context or ContextWindow(budget=token_budget, bus=self.bus)
        self.token_counter = TokenCounter()
        self.logger = logger
        self._install_default_hooks()

    def _install_default_hooks(self) -> None:
        if self.logger is not None:
            self.hooks.register("pre_skill", Hooks.structured_log(self.logger))
            self.hooks.register("post_skill", Hooks.structured_log(self.logger))
        self.hooks.register("post_skill", Hooks.token_budget_guard())

    # ------------------------------------------------------------------
    def run(self, query: str, run_id: Optional[str] = None) -> RunResult:
        state = SessionState(
            run_id=run_id or uuid.uuid4().hex[:12],
            user_query=query,
            tokens_budget=self.context.budget,
        )
        failures: List[Dict[str, Any]] = []

        self.context.add_system(
            "You are automation-grid-game-design, a senior automation-game grid "
            "logistics & throughput optimization specialist. Produce evidence-backed, "
            "risk-disclosed outputs. Units are items/sec."
        )
        self.context.add("user", query)
        state.spend_tokens(self.token_counter.count(query))

        self.hooks.trigger("pre_run", state, {"point": "pre_run"})
        self.bus.emit("run.started", run_id=state.run_id, query=query)

        decision = self.router.route(query, state, self.skills)
        state.metadata["intent"] = decision.intent
        state.metadata["reasoning"] = list(decision.reasoning)

        for step_idx, skill_name in enumerate(decision.skill_sequence, start=1):
            self.hooks.trigger("pre_skill", state, {"point": "pre_skill", "skill": skill_name, "step": step_idx})
            try:
                result = self.skills.execute(skill_name, state, self.tools, self.llm,
                                             {"point": "pre_skill", "skill": skill_name, "step": step_idx})
                state.spend_tokens(self.token_counter.count(json.dumps(result, default=str)))
                self.context.add("tool", f"{skill_name}: {json.dumps(result, default=str)[:400]}")
            except AgentError as ex:
                failures.append({"skill": skill_name, "error": ex.message, "code": ex.code})
                state.degradation_level = min(4, state.degradation_level + 1)
                self.bus.emit("run.degraded", skill=skill_name, level=state.degradation_level, error=ex.message)
                if state.degradation_level >= 4:
                    # cannot continue meaningfully; break to degraded output
                    break
            except Exception as ex:  # noqa: BLE001 - last-resort isolation
                failures.append({"skill": skill_name, "error": str(ex), "code": "unexpected"})
                state.add_error("unexpected", f"{skill_name}: {ex}")
                state.degradation_level = min(4, state.degradation_level + 1)
            finally:
                self.hooks.trigger("post_skill", state, {"point": "post_skill", "skill": skill_name, "step": step_idx})

        report = self.render_report(state, decision)
        state.report = report
        state.mark_finished()

        self.hooks.trigger("post_run", state, {"point": "post_run"})
        self.bus.emit("run.completed", run_id=state.run_id,
                     verdict=state.verdict.get("verdict", ""), tokens=state.tokens_used)

        ok = state.degradation_level < 4 and not failures
        return RunResult(state=state, decision=decision, report=report, ok=ok, failures=failures)

    # ------------------------------------------------------------------
    def render_report(self, state: SessionState, decision: RoutingDecision) -> str:
        req = state.requirements or {}
        ev = state.evidence or {}
        an = state.analysis or {}
        kn = state.knowledge or {}
        vd = state.verdict or {}
        gates = state.gate_results or []
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lang = state.language

        lines: List[str] = []
        lines.append("# Automation Grid System Design & Optimization in Factory/Automation Games - Report")
        lines.append(f"**Date:** {date} | **Analyst:** automation-grid-game-design v2.0 | "
                     f"**Language:** {lang} | **Intent:** {decision.intent}")
        lines.append("")
        lines.append("## Executive Summary")
        verdict = vd.get("verdict", "Inconclusive")
        lines.append(f"Verdict: **{verdict}**. " + (vd.get("disclosure", "")[:200] if verdict == "Inconclusive" else
                     f"Target: {req.get('target_rate')} items/sec of {req.get('target_item')} ({req.get('game')})."))
        lines.append("")
        lines.append("## Inputs & Scope")
        lines.append(f"- Game: {req.get('game', 'n/a')}")
        lines.append(f"- Object / target item: {req.get('object', req.get('target_item', 'n/a'))}")
        lines.append(f"- Target rate: {req.get('target_rate', 'n/a')} {req.get('target_rate_unit', 'items/sec')}")
        lines.append(f"- Scope: {req.get('scope', 'n/a')} | Timeframe: {req.get('timeframe', 'n/a')}")
        lines.append(f"- Audience: {req.get('target_audience', 'n/a')} | Analysis type: {req.get('analysis_type', 'combined')}")
        if req.get("assumptions"):
            lines.append("- Assumptions: " + "; ".join(req["assumptions"]))
        lines.append("")
        lines.append("## Evidence Collected")
        lines.append(f"- Belts: {json.dumps(ev.get('current_data', {}).get('belts', {}))}")
        lines.append(f"- Machines: {json.dumps(ev.get('current_data', {}).get('machines', {}))}")
        lines.append(f"- Recipes loaded: {len(ev.get('current_data', {}).get('recipes', []))}")
        for d in ev.get("authoritative_docs", []):
            lines.append(f"- {d.get('title')} ({d.get('venue')}) DOI:{d.get('doi')} [{d.get('tier')}]")
        if ev.get("limitations"):
            lines.append("- Limitations: " + "; ".join(ev["limitations"]))
        lines.append("")
        lines.append("## Analysis / Scorecard")
        lines.append(f"- Stages: {len(an.get('stages', []))}")
        for s in an.get("stages", []):
            lines.append(f"  - {s['stage']} ({s['machine']}): {s['count_rounded']} machine(s), "
                         f"util={s['utilization']:.2f}, {s['target_rate']} items/s, "
                         f"power={s['power_kw']}kW, pollution={s['pollution_per_min']}/min")
        b = an.get("bottleneck", {})
        lines.append(f"- Bottleneck: {b.get('stage')} (util={b.get('utilization')}) "
                     f"cap={b.get('throughput_cap')} items/s")
        lines.append(f"- Tradeoffs: {json.dumps(an.get('tradeoffs', {}))}")
        lines.append(f"- Engine verdict: {an.get('engine_verdict', 'n/a')}")
        if an.get("scenarios"):
            lines.append("- Scenarios (best/base/worst):")
            for name, sc in an["scenarios"].items():
                lines.append(f"  - {name}: {json.dumps(sc)}")
        lines.append("")
        lines.append("## Action / Control Plan")
        for r in vd.get("remediation", []) or ["No action required."]:
            lines.append(f"- {r}")
        lines.append("")
        lines.append("## Academic & Research Evidence")
        for c in kn.get("citations", []):
            lines.append(f"- {c.get('title', '')} ({c.get('year', '')}) {c.get('venue', '')} "
                         f"DOI/URL:{c.get('doi_or_url', '')} [{c.get('tier', '')}]")
        if kn.get("gaps"):
            lines.append("- Knowledge gaps:")
            for g in kn["gaps"]:
                lines.append(f"  - {g.get('topic')}: {g.get('query')}")
        lines.append(f"- Coverage: {kn.get('coverage', 'n/a')}")
        lines.append("")
        lines.append("## Disclosure / Limitations")
        lines.append(f"> {vd.get('disclosure', 'No disclosure generated.')}")
        if state.degradation_level >= 1:
            lines.append(f"> LIMITATION NOTICE: degradation level {state.degradation_level}.")
        lines.append("")
        lines.append("## Recommendation / Conclusion")
        lines.append(f"**Verdict: {verdict}**")
        if vd.get("key_risks"):
            lines.append("Key risks:")
            for r in vd["key_risks"]:
                lines.append(f"- {r.get('risk')} (prob={r.get('probability')}, impact={r.get('impact')})")
        if vd.get("evidence_chain"):
            lines.append("Evidence chain:")
            for e in vd["evidence_chain"]:
                lines.append(f"- {e.get('claim')} <- {e.get('source')} [{e.get('tier')}]")
        lines.append("")
        lines.append("## Post-Execution Gate Checklist")
        gate_summary = " ".join(
            f"{g['gate']}-{'ok' if g.get('passed') else 'FAIL'}" for g in gates
        ) or "no gates run"
        lines.append(gate_summary + f" | Limitations: {state.degradation_level}")
        lines.append("")
        lines.append("## Routing Reasoning (chain-of-thought)")
        for r in decision.reasoning:
            lines.append(f"- {r}")
        return "\n".join(lines)
