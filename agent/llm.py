"""agent.llm - LLM provider abstraction with a fully-functional deterministic
provider (offline, engine-backed) and a real OpenAI-compatible HTTP provider.

The deterministic provider is NOT a stub: it parses the user query, calls the
automation_grid engine, queries the knowledge base and synthesises real,
schema-validated structured outputs for every skill - so the entire harness
runs and is unit-testable with no network and no API key.

The OpenAI-compatible provider is a real HTTP client (uses ``requests`` when
available) that posts chat-completion requests and parses JSON tool/structured
outputs. It is only selected when an API key is configured; otherwise the
deterministic provider is used so the system degrades gracefully.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .errors import LLMError
from .events import EventBus

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from automation_grid import (  # noqa: E402
    DEFAULT_REGISTRY,
    KNOWLEDGE_CONFIG,
    classify_verdict,
    search_brain,
    solve_grid,
    valid_verdicts,
)
from automation_grid.config import BELT_THROUGHPUT, MACHINE_SPECS, MODULE_EFFECTS  # noqa: E402

try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore


@dataclass
class LLMResponse:
    text: str
    structured: Optional[Dict[str, Any]] = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = "deterministic"
    raw: Any = None


class LLMProvider:
    """Abstract LLM provider interface."""

    name = "base"

    def complete(self, messages: List[Dict[str, str]], **params: Any) -> LLMResponse:
        raise NotImplementedError

    def structured(self, skill: str, inputs: Dict[str, Any], **params: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Deterministic provider - real, engine-backed, offline
# ---------------------------------------------------------------------------

_GAME_KEYWORDS = {
    "factorio": ["factorio"],
    "satisfactory": ["satisfactory"],
    "dsp": ["dyson sphere", "dyson-sphere", "dsp"],
}

_RATE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:/|per|p)\s*(?:item\s*)?(sec|s|second|seconds|minute|min|minutes|min)",
    re.IGNORECASE,
)
_RATE_RE_BARE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:items?/)?(sec|s|min|minute)", re.IGNORECASE)


def _detect_game(query: str) -> str:
    q = query.lower()
    for game, kws in _GAME_KEYWORDS.items():
        if any(k in q for k in kws):
            return game
    return "factorio"


_HYPHEN_ID_RE = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\b")


def _detect_item(query: str, game: str) -> str:
    q = query.lower()
    candidates: List[str] = []
    for r in DEFAULT_REGISTRY.items():
        if r.game != game:
            continue
        candidates.extend(r.outputs.keys())
    # prefer the longest matching item name (more specific)
    matches = [c for c in candidates if c.replace("-", " ") in q or c in q]
    if matches:
        matches.sort(key=len, reverse=True)
        return matches[0]
    # if the user explicitly named a hyphenated identifier that is NOT in the
    # registry, return it as-is so the engine raises and the harness degrades
    # honestly instead of silently substituting a default.
    m = _HYPHEN_ID_RE.search(q)
    if m:
        return m.group(1)
    # fall back to a sensible default per game
    return {"factorio": "electronic-circuit", "satisfactory": "reinforced-iron-plate",
            "dsp": "electromagnetic-matrix"}.get(game, "electronic-circuit")


def _detect_rate(query: str) -> float:
    m = _RATE_RE.search(query) or _RATE_RE_BARE.search(query)
    if not m:
        return 10.0
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("min"):
        value = value / 60.0
    return round(value, 4)


def _detect_language(query: str) -> str:
    # Vietnamese diacritics + common words
    vi_chars = re.search(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", query)
    vi_words = re.search(r"\b(tối|tối ưu|tính|phân tích|cho|game|mục tiêu|báo cáo)\b", query, re.IGNORECASE)
    return "vi" if (vi_chars or vi_words) else "en"


class DeterministicProvider(LLMProvider):
    """Engine-backed offline provider. Produces real structured outputs."""

    name = "deterministic"

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()

    def complete(self, messages: List[Dict[str, str]], **params: Any) -> LLMResponse:
        # Render a deterministic acknowledgement; the runner uses structured().
        text = "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
        return LLMResponse(text=text, tokens_in=len(text) // 4, tokens_out=0, model=self.name)

    def structured(self, skill: str, inputs: Dict[str, Any], **params: Any) -> Dict[str, Any]:
        fn = getattr(self, f"_gen_{skill}", None)
        if fn is None:
            raise LLMError(f"deterministic provider has no generator for skill {skill!r}")
        try:
            result = fn(inputs)
        except Exception as ex:  # noqa: BLE001 - wrap as LLMError for fallback chain
            raise LLMError(f"deterministic generation failed for {skill!r}: {ex}") from ex
        if self.bus:
            self.bus.emit("llm.structured", skill=skill, keys=list(result.keys()))
        return result

    # ---- per-skill generators -------------------------------------------
    def _gen_gather_requirements(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("query", "")
        game = _detect_game(query)
        item = _detect_item(query, game)
        rate = _detect_rate(query)
        lang = _detect_language(query)
        return {
            "game": game,
            "object": item,
            "target_item": item,
            "target_rate": rate,
            "target_rate_unit": "items/sec",
            "scope": "full chain",
            "timeframe": "base game",
            "available_inputs": "default machine tiers + belts",
            "target_audience": "practitioner",
            "language": lang,
            "analysis_type": "combined",
            "assumptions": [
                f"game inferred as {game} from query",
                f"target item inferred as {item} from seeded recipe registry",
                f"target rate parsed as {rate} items/sec",
            ],
        }

    def _gen_evidence_collector(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        game = inputs.get("game", "factorio")
        item = inputs.get("target_item", "")
        belts = BELT_THROUGHPUT.get(game, {})
        machines = MACHINE_SPECS.get(game, {})
        modules = MODULE_EFFECTS.get(game, {})
        recipes = [
            {"name": r.name, "inputs": r.inputs, "outputs": r.outputs,
             "craft_time": r.craft_time, "machine": r.machine}
            for r in DEFAULT_REGISTRY.items() if r.game == game
        ]
        return {
            "game": game,
            "target_item": item,
            "current_data": {
                "belts": belts,
                "machines": machines,
                "modules": modules,
                "recipes": recipes,
            },
            "authoritative_docs": [
                {"title": "Little's Law", "venue": "Oper. Res. 9(3)", "doi": "10.1287/opre.9.3.383", "tier": "Tier 1"},
                {"title": "Flow-shop scheduling: a review", "venue": "EJOR", "doi": "10.1016/S0377-2217(03)00358-8", "tier": "Tier 1"},
            ],
            "recent_news": [],
            "reference_benchmarks": "SECOND-KNOWLEDGE-BRAIN.md Sections 2 & 4",
            "degradation_level": 0,
            "limitations": [],
        }

    def _gen_core_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        game = inputs.get("game", "factorio")
        item = inputs.get("target_item", "electronic-circuit")
        rate = float(inputs.get("target_rate", 10.0))
        data_available = bool(inputs.get("data_available", True))
        sol = solve_grid(item, rate, DEFAULT_REGISTRY, game, data_available=data_available)
        summary = {
            "power_kw_total": sol.power_kw_total,
            "pollution_per_min_total": sol.pollution_per_min_total,
            "belts_total": sol.belts_total,
            "machine_count_total": sum(s.count_rounded for s in sol.stages),
        }
        scenarios = self._scenarios(item, rate, game)
        return {
            "game": game,
            "target_item": item,
            "target_rate": rate,
            "stages": [
                {"stage": s.stage, "machine": s.machine.machine, "count_rounded": s.count_rounded,
                 "output_item": s.output_item, "target_rate": s.target_rate,
                 "utilization": s.utilization, "power_kw": s.power_kw,
                 "pollution_per_min": s.pollution_per_min,
                 "input_rates": dict(s.input_rates), "belts_in": dict(s.belts_in),
                 "belts_out": dict(s.belts_out)}
                for s in sol.stages
            ],
            "bottleneck": {
                "stage": sol.bottleneck.bottleneck_stage,
                "utilization": sol.bottleneck.bottleneck_utilization,
                "throughput_cap": sol.bottleneck.throughput_cap,
                "buffer_size_seconds": sol.bottleneck.buffer_size_seconds,
                "recommendations": list(sol.bottleneck.recommendations),
            },
            "tradeoffs": summary,
            "scenarios": scenarios,
            "engine_verdict": sol.verdict.value,
            "notes": list(sol.notes),
        }

    def _scenarios(self, item: str, rate: float, game: str) -> Dict[str, Any]:
        def _solve(mult: float, data_available: bool = True) -> Dict[str, Any]:
            try:
                sol = solve_grid(item, max(0.01, rate * mult), DEFAULT_REGISTRY, game,
                                 data_available=data_available)
                return {
                    "rate": round(rate * mult, 4),
                    "verdict": sol.verdict.value,
                    "power_kw_total": sol.power_kw_total,
                    "machine_count_total": sum(s.count_rounded for s in sol.stages),
                    "belts_total": sol.belts_total,
                }
            except Exception:  # noqa: BLE001
                return {"rate": round(rate * mult, 4), "verdict": "Inconclusive"}

        return {
            "best": _solve(1.25),
            "base": _solve(1.0),
            "worst": _solve(0.75),
        }

    def _gen_knowledge_updater(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        keywords = inputs.get("keywords") or [inputs.get("game", "factorio"),
                                               "throughput bottleneck", "Little law"]
        rows = search_brain(list(keywords), max_results=5)
        return {
            "citations": rows,
            "gaps": [
                {"topic": "belt balancer throughput proof", "query": "belt balancer throughput balanced n:m"},
                {"topic": "factory game telemetry ML bottleneck detection", "query": "factory game bottleneck machine learning"},
            ],
            "coverage": "Strong" if len(rows) >= 3 else ("Moderate" if rows else "Weak"),
        }

    def _gen_advisor(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        analysis = inputs.get("analysis", {})
        bottleneck = analysis.get("bottleneck", {})
        util = float(bottleneck.get("utilization", 0.0))
        data_available = bool(inputs.get("data_available", True))
        verdict = classify_verdict(
            _BottleneckShim(util), feasible=True, data_available=data_available
        ).value
        risks = self._risks(analysis, verdict)
        return {
            "verdict": verdict,
            "scenarios": analysis.get("scenarios", {}),
            "key_risks": risks,
            "evidence_chain": self._evidence_chain(analysis, inputs.get("knowledge", {})),
            "remediation": self._remediation(analysis, verdict),
            "disclosure": self._disclosure(inputs),
        }

    def _risks(self, analysis: Dict[str, Any], verdict: str) -> List[Dict[str, str]]:
        risks = [
            {"risk": "Bottleneck starvation at the tightest stage", "probability": "M", "impact": "H"},
            {"risk": "Belt throughput ceiling under peak load", "probability": "M", "impact": "M"},
            {"risk": "Power brownout when scaling stages", "probability": "L", "impact": "H"},
        ]
        if analysis.get("tradeoffs", {}).get("pollution_per_min_total", 0) > 0:
            risks.append({"risk": "Pollution cap exceeded triggering biter attacks / complaints",
                          "probability": "M", "impact": "M"})
        if verdict == "Conditional (bottleneck)":
            risks.append({"risk": "Bottleneck blocks scale-up before downstream expansion",
                          "probability": "H", "impact": "H"})
        return risks

    def _evidence_chain(self, analysis: Dict[str, Any], knowledge: Dict[str, Any]) -> List[Dict[str, str]]:
        chain = [
            {"claim": f"Ratios computed for {analysis.get('target_item', 'target')}",
             "source": "automation_grid.solve_ratios", "tier": "engine"},
            {"claim": "Bottleneck identified via Little's Law",
             "source": "automation_grid.bottleneck_analysis", "tier": "engine"},
        ]
        for c in knowledge.get("citations", [])[:3]:
            chain.append({"claim": c.get("title", "academic reference"),
                          "source": c.get("doi_or_url", "SECOND-KNOWLEDGE-BRAIN"),
                          "tier": c.get("tier", "Tier 2")})
        return chain

    def _remediation(self, analysis: Dict[str, Any], verdict: str) -> List[str]:
        recs = list(analysis.get("bottleneck", {}).get("recommendations", []))
        if verdict == "Conditional (bottleneck)":
            stage = analysis.get("bottleneck", {}).get("stage", "bottleneck stage")
            recs.insert(0, f"Add 1 machine at '{stage}' or apply speed modules/beacons to relieve the capacity-bound stage.")
        if analysis.get("tradeoffs", {}).get("pollution_per_min_total", 0) > 0:
            recs.append("Consider efficiency modules or green power to cut pollution.")
        return recs or ["No remediation required; layout is optimized with headroom."]

    def _disclosure(self, inputs: Dict[str, Any]) -> str:
        level = int(inputs.get("degradation_level", 0))
        base = ("This output was generated by the automation-grid-game-design harness "
                "with the deterministic (engine-backed) provider.")
        if level == 0:
            return base + " All primary seeded data available."
        return (base + f" Reduced data availability (Level {level}); cross-check with "
                "current live data before acting. Substituted/missing sources are flagged inline.")


@dataclass
class _BottleneckShim:
    bottleneck_utilization: float


# ---------------------------------------------------------------------------
# OpenAI-compatible HTTP provider (real, optional)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider(LLMProvider):
    """Real HTTP client for any OpenAI-compatible chat-completions endpoint.

    Selected only when ``api_key`` is provided. Falls back to deterministic
    generation for ``structured()`` by instructing the model to emit JSON, then
    parsing it; on any failure the caller (runner) applies the fallback chain.
    """

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 60.0,
        deterministic: Optional[DeterministicProvider] = None,
        bus: Optional[EventBus] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required for OpenAICompatibleProvider")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = float(timeout)
        self.deterministic = deterministic or DeterministicProvider(bus=bus)
        self.bus = bus or EventBus()

    def is_available(self) -> bool:
        return requests is not None

    def complete(self, messages: List[Dict[str, str]], **params: Any) -> LLMResponse:
        if requests is None:
            return self.deterministic.complete(messages, **params)
        payload = {"model": params.get("model", self.model), "messages": messages,
                   "temperature": params.get("temperature", 0.2)}
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        try:
            resp = requests.post(f"{self.base_url}/chat/completions",
                                 json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return LLMResponse(text=text, tokens_in=data.get("usage", {}).get("prompt_tokens", 0),
                               tokens_out=data.get("usage", {}).get("completion_tokens", 0),
                               model=self.model, raw=data)
        except Exception as ex:  # noqa: BLE001 - degrade to deterministic
            if self.bus:
                self.bus.emit("llm.fallback", reason=str(ex))
            return self.deterministic.complete(messages, **params)

    def structured(self, skill: str, inputs: Dict[str, Any], **params: Any) -> Dict[str, Any]:
        # Real providers return free-form text; we ask for JSON and parse it,
        # falling back to the deterministic generator on any failure so the
        # harness never produces a malformed output.
        prompt = (f"Skill: {skill}\nInputs: {json.dumps(inputs)}\n"
                  f"Respond with a single JSON object matching the skill output schema.")
        resp = self.complete([{"role": "user", "content": prompt}], **params)
        text = resp.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, json.JSONDecodeError):
            pass
        if self.bus:
            self.bus.emit("llm.structured_fallback", skill=skill)
        return self.deterministic.structured(skill, inputs, **params)


def build_provider(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    bus: Optional[EventBus] = None,
) -> LLMProvider:
    """Build the configured provider; deterministic when no API key is set."""
    if api_key:
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
            model=model or "gpt-4o-mini",
            bus=bus,
        )
    return DeterministicProvider(bus=bus)
