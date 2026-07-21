"""agent.state - mutable per-run session state shared across skills/hooks/tools.

SessionState is the single source of truth for one harness run. It is plain
data (serialisable to JSON) so the state-sync hook can persist snapshots and
the runner can resume across the 6 harness steps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionState:
    """Mutable state for a single harness execution."""

    run_id: str = ""
    user_query: str = ""
    language: str = "en"
    degradation_level: int = 0
    requirements: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    analysis: Dict[str, Any] = field(default_factory=dict)
    knowledge: Dict[str, Any] = field(default_factory=dict)
    verdict: Dict[str, Any] = field(default_factory=dict)
    report: str = ""
    gate_results: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    tokens_budget: int = 8192
    started_at: str = field(default_factory=_now)
    finished_at: Optional[str] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ---- typed accessors -------------------------------------------------
    def add_history(self, skill: str, event: str, **extra: Any) -> None:
        self.history.append({"skill": skill, "event": event, "ts": _now(), **extra})

    def add_error(self, code: str, message: str, **extra: Any) -> None:
        self.errors.append({"code": code, "message": message, "ts": _now(), **extra})

    def add_gate(self, gate_id: str, passed: bool, detail: str = "") -> None:
        self.gate_results.append({"gate": gate_id, "passed": passed, "detail": detail, "ts": _now()})

    def spend_tokens(self, n: int) -> None:
        if n < 0:
            raise ValueError("token spend must be non-negative")
        self.tokens_used += n

    def tokens_remaining(self) -> int:
        return max(0, self.tokens_budget - self.tokens_used)

    def mark_finished(self) -> None:
        self.finished_at = _now()

    # ---- serialisation ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_query": self.user_query,
            "language": self.language,
            "degradation_level": self.degradation_level,
            "requirements": self.requirements,
            "evidence": self.evidence,
            "analysis": self.analysis,
            "knowledge": self.knowledge,
            "verdict": self.verdict,
            "report": self.report,
            "gate_results": list(self.gate_results),
            "history": list(self.history),
            "tokens_used": self.tokens_used,
            "tokens_budget": self.tokens_budget,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        s = cls()
        s.run_id = data.get("run_id", "")
        s.user_query = data.get("user_query", "")
        s.language = data.get("language", "en")
        s.degradation_level = int(data.get("degradation_level", 0))
        s.requirements = dict(data.get("requirements", {}))
        s.evidence = dict(data.get("evidence", {}))
        s.analysis = dict(data.get("analysis", {}))
        s.knowledge = dict(data.get("knowledge", {}))
        s.verdict = dict(data.get("verdict", {}))
        s.report = data.get("report", "")
        s.gate_results = list(data.get("gate_results", []))
        s.history = list(data.get("history", []))
        s.tokens_used = int(data.get("tokens_used", 0))
        s.tokens_budget = int(data.get("tokens_budget", 8192))
        s.started_at = data.get("started_at", _now())
        s.finished_at = data.get("finished_at")
        s.errors = list(data.get("errors", []))
        s.metadata = dict(data.get("metadata", {}))
        return s

    def snapshot(self) -> Dict[str, Any]:
        """A deep-ish JSON snapshot suitable for state-sync hooks / persistence."""
        import json
        return json.loads(json.dumps(self.to_dict()))
