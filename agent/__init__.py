"""automation_grid agent framework - production-grade skill registry, router,
hooks, tools, context management and orchestration for the
automation-grid-game-design skill.

The framework is pure-stdlib (no third-party dependencies beyond what the
engine already uses) and is fully runnable offline: a deterministic LLM
provider computes real, engine-backed structured outputs so the whole harness
can be executed and unit-tested without any network or API key.

Public API:
    Skill, SkillRegistry          -> skill registration / resolution / execution
    Tool, ToolRegistry            -> tool definitions (schema + handler) + invocation
    HookManager, Hooks            -> lifecycle / state-sync / event hooks
    EventBus, Event               -> in-process event emission
    ChainOfThoughtRouter          -> intent + reasoning router
    ContextWindow, TokenCounter   -> context-window + token-budget management
    SessionState                  -> mutable per-run agent state
    HarnessRunner                 -> end-to-end orchestrator
    LLMProvider, DeterministicProvider, OpenAICompatibleProvider
"""
from .errors import AgentError, SkillNotFound, ToolNotFound, SchemaError, ContextOverflow
from .events import EventBus, Event
from .schemas import validate, validate_instance
from .state import SessionState
from .context import TokenCounter, ContextWindow
from .hooks import HookManager, Hooks
from .tools import Tool, ToolRegistry, build_default_tools
from .registry import Skill, SkillRegistry, load_skill_definitions
from .router import ChainOfThoughtRouter, RoutingDecision
from .llm import (
    LLMProvider,
    LLMResponse,
    DeterministicProvider,
    OpenAICompatibleProvider,
    build_provider,
)
from .runner import HarnessRunner, RunResult

__all__ = [
    "AgentError", "SkillNotFound", "ToolNotFound", "SchemaError", "ContextOverflow",
    "EventBus", "Event",
    "validate", "validate_instance",
    "SessionState",
    "TokenCounter", "ContextWindow",
    "HookManager", "Hooks",
    "Tool", "ToolRegistry", "build_default_tools",
    "Skill", "SkillRegistry", "load_skill_definitions",
    "ChainOfThoughtRouter", "RoutingDecision",
    "LLMProvider", "LLMResponse", "DeterministicProvider",
    "OpenAICompatibleProvider", "build_provider",
    "HarnessRunner", "RunResult",
]

__version__ = "2.0.0"
