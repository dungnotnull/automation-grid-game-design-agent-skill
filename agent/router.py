"""agent.router - chain-of-thought intent router.

The router inspects the user query, classifies the intent, emits an explicit
chain-of-thought reasoning trace, and selects the ordered skill sequence the
runner should execute. It is deterministic and unit-testable; a real LLM can
be plugged in by overriding ``classify_intent``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .events import EventBus
from .registry import SkillRegistry
from .state import SessionState


@dataclass
class RoutingDecision:
    intent: str
    reasoning: List[str] = field(default_factory=list)
    skill_sequence: List[str] = field(default_factory=list)
    entry_skill: str = ""
    degradation_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.skill_sequence:
            raise ValueError("skill_sequence must be non-empty")
        self.entry_skill = self.entry_skill or self.skill_sequence[0]


_INTENT_PATTERNS = [
    ("compare", re.compile(r"\b(compare|comparison|vs\.?|versus|so sánh|khác biệt)\b", re.IGNORECASE)),
    ("explain", re.compile(r"\b(explain|what is|how does|giải thích|là gì|nguyên lý)\b", re.IGNORECASE)),
    ("assess", re.compile(r"\b(assess|feasib|can i|is it possible|đánh giá|khả thi|có thể)\b", re.IGNORECASE)),
    ("optimize", re.compile(r"\b(optimize|optimise|ratio|throughput|tối ưu|tỉ lệ|công suất)\b", re.IGNORECASE)),
]

_FULL_SEQUENCE = [
    "gather_requirements", "evidence_collector", "core_analysis",
    "knowledge_updater", "advisor", "quality_gate",
]
_EXPLAIN_SEQUENCE = [
    "gather_requirements", "knowledge_updater", "advisor", "quality_gate",
]


class ChainOfThoughtRouter:
    """Deterministic chain-of-thought router over the skill registry."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()

    def classify_intent(self, query: str) -> str:
        for intent, pattern in _INTENT_PATTERNS:
            if pattern.search(query):
                return intent
        return "optimize"

    def route(self, query: str, state: SessionState, registry: SkillRegistry) -> RoutingDecision:
        intent = self.classify_intent(query)
        reasoning: List[str] = []

        if intent == "explain":
            sequence = [s for s in _EXPLAIN_SEQUENCE if registry.has(s)]
            reasoning.append("Intent=explain: user asks for a concept/method explanation.")
            reasoning.append("Skipping recipe/evidence fetch; routing to knowledge + advisor for an evidence-grounded explanation.")
        elif intent == "compare":
            sequence = [s for s in _FULL_SEQUENCE if registry.has(s)]
            reasoning.append("Intent=compare: user wants a comparison; full analysis pipeline produces comparable scenarios.")
            state.metadata["comparison"] = True
        elif intent == "assess":
            sequence = [s for s in _FULL_SEQUENCE if registry.has(s)]
            reasoning.append("Intent=assess: feasibility assessment; full pipeline + verdict + risks required.")
        else:
            sequence = [s for s in _FULL_SEQUENCE if registry.has(s)]
            reasoning.append("Intent=optimize (default): full ratio/throughput/logistics pipeline with engine cross-check.")

        reasoning.append(f"Selected skill sequence: {' -> '.join(sequence)}.")
        if not sequence:
            raise ValueError("router produced an empty skill sequence; registry misconfigured")

        decision = RoutingDecision(
            intent=intent,
            reasoning=reasoning,
            skill_sequence=sequence,
            degradation_level=state.degradation_level,
        )
        self.bus.emit("router.decision", intent=intent, sequence=sequence)
        return decision
