"""agent.hooks - lifecycle, state-sync and event-emission hooks.

Hooks are simple callables registered against named lifecycle points. The
HookManager invokes them in registration order; a failing hook is isolated
(emits ``hook.failed``) so it cannot break the harness - matching the
production-grade "graceful fallback" requirement.

Built-in hooks:
  * StructuredLogHook      - emits every lifecycle event to a logger.
  * StateSyncHook          - snapshots SessionState after each skill step.
  * EventEmissionHook     - re-bus internal events (metrics tap).
  * TokenBudgetHook       - enforces the per-run token budget.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .events import EventBus, Event
from .state import SessionState


Hook = Callable[[SessionState, EventBus, Dict[str, Any]], None]

HOOK_POINTS = (
    "pre_run",
    "post_run",
    "pre_skill",
    "post_skill",
    "on_tool",
    "on_gate",
    "on_error",
    "on_event",
)


class HookManager:
    """Registry + dispatcher for lifecycle hooks."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self._hooks: Dict[str, List[Hook]] = {p: [] for p in HOOK_POINTS}

    def register(self, point: str, hook: Hook) -> Callable[[], None]:
        if point not in self._hooks:
            raise ValueError(f"unknown hook point {point!r}; valid: {HOOK_POINTS}")
        if not callable(hook):
            raise TypeError("hook must be callable")
        self._hooks[point].append(hook)

        def _unregister() -> None:
            if hook in self._hooks[point]:
                self._hooks[point].remove(hook)

        return _unregister

    def trigger(self, point: str, state: SessionState, ctx: Optional[Dict[str, Any]] = None) -> None:
        if point not in self._hooks:
            raise ValueError(f"unknown hook point {point!r}")
        context = ctx or {}
        for hook in list(self._hooks[point]):
            try:
                hook(state, self.bus, context)
            except Exception as ex:  # noqa: BLE001 - isolate faulty hooks
                self.bus.emit(
                    "hook.failed",
                    point=point,
                    hook=getattr(hook, "__name__", repr(hook)),
                    error=str(ex),
                )

    def count(self, point: str) -> int:
        return len(self._hooks.get(point, []))


class Hooks:
    """Namespace of built-in, reusable hook factories."""

    @staticmethod
    def structured_log(logger: Any) -> Hook:
        def _hook(state: SessionState, bus: EventBus, ctx: Dict[str, Any]) -> None:
            point = ctx.get("point", "lifecycle")
            skill = ctx.get("skill", "")
            logger.info("hook.%s skill=%s run=%s level=%d tokens=%d",
                        point, skill, state.run_id, state.degradation_level, state.tokens_used)
        _hook.__name__ = "structured_log_hook"
        return _hook

    @staticmethod
    def state_sync(snapshot_dir: Optional[Path] = None) -> Hook:
        """Persist a SessionState snapshot after each skill step."""
        def _hook(state: SessionState, bus: EventBus, ctx: Dict[str, Any]) -> None:
            snap = state.snapshot()
            if snapshot_dir is not None:
                try:
                    snapshot_dir.mkdir(parents=True, exist_ok=True)
                    step = ctx.get("step", len(state.history))
                    path = snapshot_dir / f"{state.run_id or 'run'}_step{step}.json"
                    path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
                except OSError:
                    # read-only / restricted filesystem: keep in-memory snapshot only
                    pass
            state.metadata.setdefault("snapshots", []).append(snap)
            bus.emit("state.synced", run_id=state.run_id, step=ctx.get("step"))
        _hook.__name__ = "state_sync_hook"
        return _hook

    @staticmethod
    def event_emission(tap: EventBus) -> Hook:
        """Re-emit lifecycle events onto a separate metrics tap bus."""
        def _hook(state: SessionState, bus: EventBus, ctx: Dict[str, Any]) -> None:
            tap.emit("lifecycle", run_id=state.run_id, **{k: v for k, v in ctx.items() if isinstance(v, (str, int, float, bool))})
        _hook.__name__ = "event_emission_hook"
        return _hook

    @staticmethod
    def token_budget_guard() -> Hook:
        """Raise a degradation event when the token budget is exhausted."""
        def _hook(state: SessionState, bus: EventBus, ctx: Dict[str, Any]) -> None:
            if state.tokens_used >= state.tokens_budget:
                bus.emit("tokens.exhausted", run_id=state.run_id, used=state.tokens_used, budget=state.tokens_budget)
                state.degradation_level = max(state.degradation_level, 2)
        _hook.__name__ = "token_budget_guard_hook"
        return _hook

    @staticmethod
    def metrics_collector(sink: Optional[List[Dict[str, Any]]] = None) -> Hook:
        """Collect a flat metrics record per skill step into ``sink``."""
        sink_list: List[Dict[str, Any]] = sink if sink is not None else []

        def _hook(state: SessionState, bus: EventBus, ctx: Dict[str, Any]) -> None:
            sink_list.append({
                "run_id": state.run_id,
                "point": ctx.get("point", ""),
                "skill": ctx.get("skill", ""),
                "tokens_used": state.tokens_used,
                "degradation_level": state.degradation_level,
                "gates_passed": sum(1 for g in state.gate_results if g.get("passed")),
                "gates_total": len(state.gate_results),
            })
        _hook.__name__ = "metrics_collector_hook"
        return _hook
