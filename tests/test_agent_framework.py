"""test_agent_framework.py - pytest suite for the agent framework."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agent import (
    ChainOfThoughtRouter,
    ContextWindow,
    DeterministicProvider,
    EventBus,
    HookManager,
    Hooks,
    HarnessRunner,
    LLMResponse,
    SkillRegistry,
    Skill,
    TokenCounter,
    Tool,
    ToolRegistry,
    build_default_tools,
    load_skill_definitions,
)
from agent.errors import (
    AgentError, ContextOverflow, SchemaError, SkillNotFound, ToolNotFound,
    retry, run_with_fallback,
)
from agent.schemas import validate, validate_instance, collect_errors
from agent.state import SessionState

ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS = ROOT / "skills" / "definitions"


# ---------------- schemas ----------------
def test_schema_validates_object():
    schema = {"type": "object", "properties": {"a": {"type": "integer", "minimum": 0}},
              "required": ["a"], "additionalProperties": False}
    validate({"a": 1}, schema)
    with pytest.raises(SchemaError):
        validate({"a": -1}, schema)
    with pytest.raises(SchemaError):
        validate({"a": 1, "b": 2}, schema)


def test_schema_enum_and_bool_not_int():
    schema = {"type": "string", "enum": ["x", "y"]}
    validate("x", schema)
    with pytest.raises(SchemaError):
        validate("z", schema)
    # bool must not satisfy integer
    with pytest.raises(SchemaError):
        validate(True, {"type": "integer"})


def test_schema_array_items():
    schema = {"type": "array", "items": {"type": "integer"}, "minItems": 1}
    validate([1, 2, 3], schema)
    with pytest.raises(SchemaError):
        validate([], schema)
    with pytest.raises(SchemaError):
        validate([1, "x"], schema)


def test_schema_ref_resolves():
    schema = {"type": "object", "properties": {"a": {"$ref": "#/defs/x"}},
              "defs": {"x": {"type": "integer"}}, "required": ["a"]}
    validate({"a": 5}, schema)
    with pytest.raises(SchemaError):
        validate({"a": "no"}, schema)


def test_collect_errors_returns_all():
    schema = {"type": "object", "properties": {"a": {"type": "integer", "minimum": 0},
              "b": {"type": "string"}}, "required": ["a", "b"]}
    errs = collect_errors({"a": -1, "b": 5}, schema)
    assert len(errs) >= 2


# ---------------- events ----------------
def test_event_bus_pubsub():
    bus = EventBus()
    seen = []
    bus.subscribe("test", lambda e: seen.append(e.payload["v"]))
    bus.subscribe("*", lambda e: seen.append(99))
    bus.emit("test", v=1)
    assert 1 in seen and 99 in seen


def test_event_bus_bad_subscriber_isolated():
    bus = EventBus()
    out = []
    def _bad(e): raise RuntimeError("boom")
    bus.subscribe("t", _bad)
    bus.subscribe("t", lambda e: out.append("ok"))
    bus.emit("t")
    assert out == ["ok"]


def test_event_unsubscribe():
    bus = EventBus()
    calls = []
    unsub = bus.subscribe("t", lambda e: calls.append(1))
    bus.emit("t")
    unsub()
    bus.emit("t")
    assert calls == [1]


# ---------------- errors / retry / fallback ----------------
def test_retry_succeeds_after_failures():
    calls = {"n": 0}
    @retry(max_attempts=3, base_delay=0, sleep=lambda s: None)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"
    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_reraises_after_max():
    @retry(max_attempts=2, base_delay=0, sleep=lambda s: None)
    def always():
        raise ValueError("nope")
    with pytest.raises(ValueError):
        always()


def test_run_with_fallback_uses_fallback():
    def primary(): raise RuntimeError("primary down")
    def fallback(): return "fallback"
    assert run_with_fallback(primary, [fallback]) == "fallback"


def test_run_with_fallback_all_fail():
    def a(): raise ValueError("a")
    def b(): raise ValueError("b")
    with pytest.raises(ValueError):
        run_with_fallback(a, [b])


# ---------------- state ----------------
def test_state_tokens_and_serialization():
    s = SessionState(run_id="r1", user_query="q", tokens_budget=100)
    s.spend_tokens(30)
    assert s.tokens_remaining() == 70
    with pytest.raises(ValueError):
        s.spend_tokens(-1)
    d = s.to_dict()
    s2 = SessionState.from_dict(d)
    assert s2.tokens_used == 30 and s2.run_id == "r1"


def test_state_snapshot_is_deep_copy():
    s = SessionState()
    s.requirements = {"game": "factorio"}
    snap = s.snapshot()
    snap["requirements"]["game"] = "satisfactory"
    assert s.requirements["game"] == "factorio"


# ---------------- context ----------------
def test_context_window_trims():
    cw = ContextWindow(budget=40, reserve_output=0)
    cw.add_system("system protected")  # protected
    for i in range(20):
        cw.add("user", f"msg-{i}-padding-padding")
    assert cw.used() <= cw.input_budget


def test_context_window_overflow_raises():
    cw = ContextWindow(budget=10, reserve_output=0)
    # a protected (system) message that alone exceeds the input budget cannot
    # be trimmed -> ContextOverflow
    with pytest.raises(ContextOverflow):
        cw.add_system("x" * 200)


def test_token_counter_pluggable():
    c = TokenCounter(count_fn=lambda t: len(t.split()))
    assert c.count("a b c") == 3


# ---------------- hooks ----------------
def test_hook_manager_dispatch_and_isolation():
    bus = EventBus()
    hm = HookManager(bus)
    out = []
    hm.register("pre_skill", lambda s, b, c: out.append(c.get("skill")))
    hm.register("pre_skill", lambda s, b, c: (_ for _ in ()).throw(RuntimeError("bad")))
    state = SessionState()
    hm.trigger("pre_skill", state, {"skill": "x"})
    assert out == ["x"]


def test_hooks_state_sync_in_memory():
    bus = EventBus()
    hm = HookManager(bus)
    state = SessionState(run_id="r")
    hm.register("post_skill", Hooks.state_sync())
    hm.trigger("post_skill", state, {"step": 1})
    assert state.metadata["snapshots"]


def test_hooks_unknown_point_raises():
    hm = HookManager()
    with pytest.raises(ValueError):
        hm.register("nope", lambda s, b, c: None)


# ---------------- tools ----------------
def test_default_tools_registered():
    reg = build_default_tools()
    for name in ["solve_grid", "solve_ratios", "balancer_design", "little_law",
                 "belts_required", "classify_verdict", "search_brain",
                 "list_recipes", "valid_verdicts", "append_knowledge",
                 "machine_config", "power_pollution_summary", "bottleneck_analysis"]:
        assert reg.has(name), name


def test_tool_invoke_validates_input():
    reg = build_default_tools()
    with pytest.raises(SchemaError):
        reg.invoke("balancer_design", {"input_belts": "x", "output_belts": 2})


def test_tool_invoke_balancer():
    reg = build_default_tools()
    out = reg.invoke("balancer_design", {"input_belts": 4, "output_belts": 4})
    assert out["splitters"] == 3 and out["balanced"] is True


def test_tool_invoke_little_law():
    reg = build_default_tools()
    out = reg.invoke("little_law", {"throughput_lambda": 10.0, "waiting_time_s": 2.0})
    assert out["L"] == 20.0


def test_tool_invoke_solve_grid():
    reg = build_default_tools()
    out = reg.invoke("solve_grid", {"target_item": "electronic-circuit",
                                    "target_rate": 10.0, "game": "factorio"})
    assert out["verdict"] in ["Optimized Layout", "Conditional (bottleneck)",
                              "Infeasible Target", "Inconclusive"]
    assert out["target_item"] == "electronic-circuit"


def test_tool_unknown_raises():
    reg = build_default_tools()
    with pytest.raises(ToolNotFound):
        reg.get("nope")


def test_tool_duplicate_register_raises():
    reg = ToolRegistry()
    t = Tool(name="t", description="d",
             input_schema={"type": "object"},
             output_schema={"type": "object"},
             handler=lambda: {})
    reg.register(t)
    with pytest.raises(ValueError):
        reg.register(t)


def test_tool_event_emission():
    bus = EventBus()
    reg = build_default_tools(bus=bus)
    events = []
    bus.subscribe("tool.completed", lambda e: events.append(e.type))
    reg.invoke("valid_verdicts", {})
    assert "tool.completed" in events


# ---------------- registry ----------------
def test_load_skill_definitions():
    reg = load_skill_definitions(DEFINITIONS)
    assert len(reg.names()) >= 6
    assert reg.validate_definitions() == []
    ordered = reg.ordered()
    assert ordered[0].name == "gather_requirements"
    assert ordered[-1].name == "quality_gate"


def test_skill_execute_runs_handler():
    reg = load_skill_definitions(DEFINITIONS)
    tools = build_default_tools()
    llm = DeterministicProvider()
    state = SessionState(user_query="Optimize my Factorio electronic-circuit line for 10/s")
    out = reg.execute("gather_requirements", state, tools, llm)
    assert out["game"] == "factorio"
    assert out["target_item"] == "electronic-circuit"
    assert state.requirements["game"] == "factorio"


def test_skill_not_found():
    reg = SkillRegistry()
    with pytest.raises(SkillNotFound):
        reg.get("missing")


def test_skill_descriptor_shape():
    reg = load_skill_definitions(DEFINITIONS)
    descs = reg.descriptors()
    assert all("name" in d and "inputs_schema" in d and "outputs_schema" in d for d in descs)


# ---------------- router ----------------
def test_router_intents():
    reg = load_skill_definitions(DEFINITIONS)
    router = ChainOfThoughtRouter()
    for q, intent in [("Optimize my Factorio line for 10/s", "optimize"),
                      ("Explain Little law", "explain"),
                      ("Compare 5/s vs 20/s gear", "compare"),
                      ("Assess feasibility of 50/s copper-plate", "assess")]:
        dec = router.route(q, SessionState(user_query=q), reg)
        assert dec.intent == intent
        assert dec.skill_sequence and dec.entry_skill


def test_router_explain_skips_core():
    reg = load_skill_definitions(DEFINITIONS)
    router = ChainOfThoughtRouter()
    dec = router.route("Explain Little law for factory games", SessionState(), reg)
    assert "core_analysis" not in dec.skill_sequence
    assert "knowledge_updater" in dec.skill_sequence


# ---------------- llm ----------------
def test_deterministic_provider_gather():
    p = DeterministicProvider()
    out = p.structured("gather_requirements", {"query": "Factorio electronic-circuit 10/s"})
    assert out["game"] == "factorio" and out["target_rate"] == 10.0


def test_deterministic_provider_unknown_skill_raises():
    p = DeterministicProvider()
    from agent.errors import LLMError
    with pytest.raises(LLMError):
        p.structured("no_such_skill", {})


def test_deterministic_provider_core_analysis():
    p = DeterministicProvider()
    out = p.structured("core_analysis", {"game": "factorio", "target_item": "electronic-circuit",
                                         "target_rate": 10.0, "data_available": True})
    assert out["engine_verdict"] in ["Optimized Layout", "Conditional (bottleneck)",
                                     "Infeasible Target", "Inconclusive"]
    assert len(out["stages"]) >= 1


def test_deterministic_provider_vietnamese():
    p = DeterministicProvider()
    out = p.structured("gather_requirements", {"query": "Tối ưu dây chuyền electronic-circuit Factorio 10/s"})
    assert out["language"] == "vi" and out["game"] == "factorio"


# ---------------- runner end-to-end ----------------
def test_runner_optimize():
    r = HarnessRunner()
    res = r.run("Optimize my Factorio electronic-circuit line for 10/s")
    assert res.ok
    assert res.state.verdict["verdict"] == "Conditional (bottleneck)"
    assert sum(1 for g in res.state.gate_results if g.get("passed")) == len(res.state.gate_results)
    assert res.state.tokens_used > 0
    assert "## Recommendation / Conclusion" in res.report


def test_runner_explain_passes_applicable_gates():
    r = HarnessRunner()
    res = r.run("Explain Little law for factory games")
    assert res.ok
    # all applicable gates pass
    applicable = [g for g in res.state.gate_results if g.get("detail") != "n/a (owning skill not run)"]
    assert all(g.get("passed") for g in applicable)


def test_runner_degraded_on_missing_item():
    r = HarnessRunner()
    res = r.run("Optimize my Factorio zzz-nonexistent-item line for 10/s")
    # unknown item has no seeded recipe -> graceful degradation (level >= 3)
    # and an honest Inconclusive verdict, not a hard failure.
    assert res.state.degradation_level >= 3
    assert res.state.verdict.get("verdict") == "Inconclusive"


def test_runner_report_contains_gates():
    r = HarnessRunner()
    res = r.run("Compare 5/s vs 20/s iron-gear-wheel Factorio")
    assert "Post-Execution Gate Checklist" in res.report


# ---------------- config ----------------
def test_config_loads():
    from config import load_settings
    s = load_settings()
    assert s.token_budget > 0
    assert s.llm.provider in ("deterministic", "openai")
    assert s.feature_flags.strict_gates is True


def test_config_env_override(monkeypatch):
    from config import load_settings
    monkeypatch.setenv("AUTOMATION_GRID_TOKEN_BUDGET", "4096")
    monkeypatch.setenv("AUTOMATION_GRID_LANGUAGE", "vi")
    s = load_settings()
    assert s.token_budget == 4096 and s.language == "vi"


def test_config_invalid_env_raises(monkeypatch):
    from config import load_settings
    monkeypatch.setenv("AUTOMATION_GRID_TOKEN_BUDGET", "not-an-int")
    with pytest.raises(ValueError):
        load_settings()


# ---------------- scripts (subprocess) ----------------
def test_script_run_harness():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_harness.py"),
         "Optimize my Factorio electronic-circuit line for 10/s", "--no-report"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["ok"] is True and data["verdict"] == "Conditional (bottleneck)"


def test_script_validate_skills():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_skills.py")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "all skill definitions valid" in result.stdout


def test_script_setup_local():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "setup_local.py")],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    assert "setup complete" in result.stdout