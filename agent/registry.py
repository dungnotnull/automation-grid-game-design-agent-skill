"""agent.registry - skill registry: register, resolve, validate, execute.

A Skill is a data-driven unit of agent work: a name, description, ordered
step, input/output JSON Schemas, a prompt-template reference, the tools it may
invoke, the quality gates it must satisfy, and a Python handler. The
SkillRegistry resolves skills by name, validates them, and executes them with
schema-checked inputs/outputs, emitting lifecycle events on the bus.

Skill definitions are loaded from ``skills/definitions/*.json`` (one per skill)
and bound to the handlers in ``agent.skill_handlers.HANDLERS``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .errors import SkillNotFound, SchemaError
from .events import EventBus
from .schemas import validate_instance
from .skill_handlers import HANDLERS
from .state import SessionState
from .tools import ToolRegistry
from .llm import LLMProvider

Handler = Callable[[SessionState, ToolRegistry, LLMProvider, Dict[str, Any]], Dict[str, Any]]


@dataclass
class Skill:
    name: str
    description: str
    step: int
    inputs_schema: Dict[str, Any]
    outputs_schema: Dict[str, Any]
    prompt_template: str
    tools: List[str] = field(default_factory=list)
    gates: List[str] = field(default_factory=list)
    handler: Optional[Handler] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("skill name must be non-empty")
        if not isinstance(self.inputs_schema, dict) or not isinstance(self.outputs_schema, dict):
            raise SchemaError("skill input/output schemas must be objects")
        if self.handler is None:
            if self.name in HANDLERS:
                self.handler = HANDLERS[self.name]
            else:
                raise SkillNotFound(f"no handler registered for skill {self.name!r}")

    def descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "step": self.step,
            "prompt_template": self.prompt_template,
            "tools": list(self.tools),
            "gates": list(self.gates),
            "inputs_schema": self.inputs_schema,
            "outputs_schema": self.outputs_schema,
        }


class SkillRegistry:
    """Resolves + executes skills with schema validation + lifecycle events."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if skill.name in self._skills:
            raise ValueError(f"skill {skill.name!r} already registered")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        skill = self._skills.get(name)
        if skill is None:
            raise SkillNotFound(f"skill {name!r} not registered")
        return skill

    def has(self, name: str) -> bool:
        return name in self._skills

    def names(self) -> List[str]:
        return sorted(self._skills)

    def ordered(self) -> List[Skill]:
        """Skills ordered by their ``step`` field (the harness execution order)."""
        return sorted(self._skills.values(), key=lambda s: s.step)

    def descriptors(self) -> List[Dict[str, Any]]:
        return [s.descriptor() for s in self.ordered()]

    def validate_definitions(self) -> List[str]:
        """Static validation: every skill has schemas, handler, gates. Returns issues."""
        issues: List[str] = []
        for s in self._skills.values():
            if s.handler is None:
                issues.append(f"{s.name}: missing handler")
            if "type" not in s.inputs_schema or "type" not in s.outputs_schema:
                issues.append(f"{s.name}: schemas must declare top-level 'type'")
            for t in s.tools:
                # tool existence is checked at execution time against a ToolRegistry
                if not isinstance(t, str) or not t:
                    issues.append(f"{s.name}: invalid tool ref {t!r}")
        return issues

    def execute(self, name: str, state: SessionState, tools: ToolRegistry,
                llm: LLMProvider, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        skill = self.get(name)
        context = dict(ctx or {})
        context.setdefault("point", "pre_skill")
        context["skill"] = name
        self.bus.emit("skill.started", skill=name, step=skill.step)
        assert skill.handler is not None
        try:
            result = skill.handler(state, tools, llm, context)
        except Exception as ex:  # noqa: BLE001 - emit + re-raise as agent error
            self.bus.emit("skill.failed", skill=name, error=str(ex))
            state.add_error("skill_failed", f"{name}: {ex}")
            raise
        try:
            validate_instance(result, skill.outputs_schema)
        except SchemaError as ex:
            self.bus.emit("skill.output_invalid", skill=name, error=str(ex))
            state.add_error("schema_error", f"{name}: {ex}")
            raise
        self.bus.emit("skill.completed", skill=name, step=skill.step)
        return result


# ---------------------------------------------------------------------------
# Loader for skills/definitions/*.json
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ("name", "description", "step", "inputs_schema", "outputs_schema",
                   "prompt_template")


def _skill_from_dict(data: Dict[str, Any]) -> Skill:
    for f in REQUIRED_FIELDS:
        if f not in data:
            raise SchemaError(f"skill definition missing field {f!r}", path=f)
    return Skill(
        name=data["name"],
        description=data["description"],
        step=int(data["step"]),
        inputs_schema=data["inputs_schema"],
        outputs_schema=data["outputs_schema"],
        prompt_template=data["prompt_template"],
        tools=list(data.get("tools", [])),
        gates=list(data.get("gates", [])),
        metadata=dict(data.get("metadata", {})),
    )


def load_skill_definitions(definitions_dir: Path, bus: Optional[EventBus] = None) -> SkillRegistry:
    """Load every ``skills/definitions/*.json`` into a SkillRegistry."""
    registry = SkillRegistry(bus=bus)
    if not definitions_dir.exists():
        raise SkillNotFound(f"skill definitions directory not found: {definitions_dir}")
    files = sorted(definitions_dir.glob("*.json"))
    if not files:
        raise SkillNotFound(f"no skill definition files in {definitions_dir}")
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        registry.register(_skill_from_dict(data))
    issues = registry.validate_definitions()
    if issues:
        raise SchemaError(f"invalid skill definitions: {issues}", path="definitions")
    return registry
