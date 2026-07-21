"""agent.events - lightweight in-process event bus for lifecycle emission.

The event bus lets hooks, tools and skills emit structured events (skill
started, tool invoked, gate failed, knowledge appended, ...) that any
registered subscriber can observe - enabling structured logging, metrics and
state synchronisation without tight coupling.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class Event:
    """An immutable event record."""

    type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("event type must be non-empty")


Subscriber = Callable[[Event], None]


class EventBus:
    """Thread-safe synchronous pub/sub event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._wildcard: List[Subscriber] = []
        self._lock = threading.RLock()
        self._history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: str, subscriber: Subscriber) -> Callable[[], None]:
        """Subscribe to ``event_type`` (or "*" for all). Returns an unsubscribe fn."""
        if not callable(subscriber):
            raise TypeError("subscriber must be callable")
        with self._lock:
            if event_type == "*":
                self._wildcard.append(subscriber)
            else:
                self._subscribers.setdefault(event_type, []).append(subscriber)

        def _unsubscribe() -> None:
            with self._lock:
                if event_type == "*":
                    if subscriber in self._wildcard:
                        self._wildcard.remove(subscriber)
                elif event_type in self._subscribers and subscriber in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(subscriber)

        return _unsubscribe

    def publish(self, event: Event) -> None:
        """Synchronously dispatch ``event`` to all matching subscribers."""
        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                del self._history[: max(1, len(self._history) - self._max_history)]
            subs = list(self._subscribers.get(event.type, [])) + list(self._wildcard)

        for sub in subs:
            try:
                sub(event)
            except Exception:  # noqa: BLE001 - subscribers must not break the bus
                continue

    def emit(self, event_type: str, **payload: Any) -> Event:
        """Build + publish an event in one call."""
        event = Event(type=event_type, payload=payload)
        self.publish(event)
        return event

    def history(self, event_type: Optional[str] = None) -> List[Event]:
        with self._lock:
            events = list(self._history)
        if event_type is None:
            return events
        return [e for e in events if e.type == event_type]

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
