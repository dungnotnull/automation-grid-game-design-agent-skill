"""agent.errors - typed exception hierarchy + retry/fallback helpers.

Production-grade error handling for the agent framework. Every recoverable
failure is mapped to a specific exception so the runner can apply the graceful
degradation protocol without string-matching.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

T = TypeVar("T")


class AgentError(Exception):
    """Base class for all agent-framework errors."""

    code: str = "agent_error"

    def __init__(self, message: str, *, recoverable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable


class SkillNotFound(AgentError):
    code = "skill_not_found"


class ToolNotFound(AgentError):
    code = "tool_not_found"


class SchemaError(AgentError):
    code = "schema_error"

    def __init__(self, message: str, *, path: str = "", recoverable: bool = True) -> None:
        super().__init__(message, recoverable=recoverable)
        self.path = path


class ContextOverflow(AgentError):
    code = "context_overflow"

    def __init__(self, message: str = "context window budget exceeded") -> None:
        super().__init__(message, recoverable=True)


class LLMError(AgentError):
    code = "llm_error"


class GateFailed(AgentError):
    code = "gate_failed"

    def __init__(self, gate_id: str, message: str) -> None:
        super().__init__(f"gate {gate_id}: {message}", recoverable=True)
        self.gate_id = gate_id


class DegradedMode(AgentError):
    """Raised when the harness must fall back to a lower degradation level."""

    code = "degraded_mode"

    def __init__(self, level: int, message: str) -> None:
        super().__init__(f"degradation level {level}: {message}", recoverable=True)
        self.level = level


def retry(
    max_attempts: int = 3,
    base_delay: float = 0.2,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: retry a callable with exponential backoff.

    ``sleep`` is injectable so unit tests can run without real delays.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as ex:  # noqa: BLE001 - intentional
                    last_exc = ex
                    if attempt < max_attempts:
                        sleep(base_delay * (2 ** (attempt - 1)))
            assert last_exc is not None
            raise last_exc

        return wrapper

    return deco


def run_with_fallback(
    primary: Callable[..., T],
    fallbacks: List[Callable[..., T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run ``primary``; on any exception try each fallback in order.

    Raises the last exception if all fail. Used by the evidence/knowledge
    collectors to implement the documented degradation chain.
    """
    callables: List[Callable[..., T]] = [primary, *fallbacks]
    last_exc: Optional[BaseException] = None
    for fn in callables:
        try:
            return fn(*args, **kwargs)
        except Exception as ex:  # noqa: BLE001 - intentional fallback chain
            last_exc = ex
    assert last_exc is not None
    raise last_exc
