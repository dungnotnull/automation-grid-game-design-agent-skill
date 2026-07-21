"""agent.context - token counting + context-window budget management.

Token accounting uses a pluggable counter (default heuristic: ~4 chars/token,
matching OpenAI's published rough average for English prose). A real
tokenizer can be injected by setting ``TokenCounter.count_fn``. The
ContextWindow trims conversation history when the budget is approached and
emits a ``context.trimmed`` event when it does so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .errors import ContextOverflow
from .events import EventBus


def default_count(text: str) -> int:
    """Heuristic token count: ~4 characters per token, min 1 for non-empty."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class Message:
    role: str
    content: str
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tokens:
            self.tokens = default_count(self.content)


class TokenCounter:
    """Pluggable token counter. Swap ``count_fn`` for a real tokenizer."""

    def __init__(self, count_fn: Optional[Callable[[str], int]] = None) -> None:
        self.count_fn = count_fn or default_count

    def count(self, text: str) -> int:
        if not isinstance(text, str):
            text = str(text)
        n = self.count_fn(text)
        if n < 0:
            raise ValueError("token count must be non-negative")
        return n

    def count_messages(self, messages: List[Message]) -> int:
        return sum(self.count(m.content) for m in messages)


class ContextWindow:
    """Bounded conversation buffer with trim-to-budget semantics.

    Trim policy: keep the system message + most-recent messages until the
    running token total fits the budget, dropping oldest non-system messages
    first. A ``context.trimmed`` event is emitted on the bus (if provided)
    with the number of dropped messages and tokens freed.
    """

    def __init__(
        self,
        budget: int = 8192,
        counter: Optional[TokenCounter] = None,
        bus: Optional[EventBus] = None,
        reserve_output: int = 1024,
    ) -> None:
        if budget <= 0:
            raise ValueError("budget must be positive")
        if reserve_output < 0 or reserve_output >= budget:
            raise ValueError("reserve_output must be in [0, budget)")
        self.budget = budget
        self.reserve_output = reserve_output
        self.counter = counter or TokenCounter()
        self.bus = bus
        self._messages: List[Message] = []

    @property
    def input_budget(self) -> int:
        return self.budget - self.reserve_output

    @property
    def messages(self) -> List[Message]:
        return list(self._messages)

    def used(self) -> int:
        return sum(m.tokens for m in self._messages)

    def remaining(self) -> int:
        return max(0, self.input_budget - self.used())

    def add(self, role: str, content: str, **metadata: Any) -> Message:
        msg = Message(role=role, content=content, metadata=metadata)
        msg.tokens = self.counter.count(content)
        self._messages.append(msg)
        self._maybe_trim()
        return msg

    def add_system(self, content: str) -> Message:
        return self.add("system", content, protected=True)

    def reset(self) -> None:
        self._messages.clear()

    def _maybe_trim(self) -> None:
        if self.used() <= self.input_budget:
            return
        dropped = 0
        freed = 0
        # never drop protected (system) messages
        i = 0
        while i < len(self._messages) and self.used() > self.input_budget:
            msg = self._messages[i]
            if msg.metadata.get("protected"):
                i += 1
                continue
            freed += msg.tokens
            self._messages.pop(i)
            dropped += 1
        if self.used() > self.input_budget and dropped == 0:
            # nothing droppable left; the single largest non-protected message
            # still overflows -> raise so the runner can apply degradation
            raise ContextOverflow(
                f"context window budget ({self.input_budget}) exceeded and no "
                f"droppable messages remain; used={self.used()}"
            )
        if self.bus and dropped:
            self.bus.emit("context.trimmed", dropped=dropped, freed_tokens=freed, budget=self.budget)

    def render(self) -> str:
        return "\n\n".join(f"[{m.role}] {m.content}" for m in self._messages)
