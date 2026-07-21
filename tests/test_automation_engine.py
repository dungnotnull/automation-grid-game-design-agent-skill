"""test_automation_engine.py - pytest suite for the automation_grid engine core."""
from __future__ import annotations

import math

import pytest

from automation_grid import (
    DEFAULT_REGISTRY, VERDICTS, Verdict,
    balancer_design, bottleneck_analysis, classify_verdict, little_law,
    machine_config, solve_grid, solve_ratios, belts_required,
)
from automation_grid.engine import Recipe, RecipeRegistry


# ---- recipe model ----
def test_recipe_base_rate():
    r = Recipe("x", "factorio", {"iron-plate": 2}, {"gear": 1}, 0.5, "assembling-machine-2")
    assert r.base_rate("gear") == 2.0  # 1 / 0.5
    assert r.base_rate("missing") == 0.0


def test_recipe_demand_per_output():
    r = Recipe("x", "factorio", {"iron-plate": 2}, {"gear": 1}, 0.5, "assembling-machine-2")
    d = r.demand_per_output("gear")
    assert d == {"iron-plate": 2.0}


def test_recipe_zero_craft_time_raises():
    with pytest.raises(ValueError):
        Recipe("x", "factorio", {"a": 1}, {"b": 1}, 0.0, "assembling-machine-2").base_rate("b")


# ---- registry ----
def test_registry_lookup():
    reg = RecipeRegistry()
    reg.add(Recipe("x", "factorio", {"a": 1}, {"b": 1}, 1.0, "assembling-machine-2"))
    assert reg.has("factorio", "b")
    assert not reg.has("factorio", "a")
    assert reg.get("factorio", "b").name == "x"


def test_default_registry_seeded():
    assert DEFAULT_REGISTRY.get("factorio", "electronic-circuit") is not None
    assert DEFAULT_REGISTRY.get("satisfactory", "reinforced-iron-plate") is not None


# ---- ratio solver ----
def test_solve_ratios_factorio_electronic_circuit():
    stages = solve_ratios("electronic-circuit", 10.0, DEFAULT_REGISTRY, "factorio")
    items = {s.output_item for s in stages}
    assert {"electronic-circuit", "copper-cable", "copper-plate", "iron-plate"} <= items
    ec = next(s for s in stages if s.output_item == "electronic-circuit")
    # base machine produces 2/s -> 5 machines for 10/s
    assert ec.count_rounded == 5
    assert math.isclose(ec.target_rate, 10.0, rel_tol=1e-9)


def test_solve_ratios_rejects_nonpositive_rate():
    with pytest.raises(ValueError):
        solve_ratios("electronic-circuit", 0.0, DEFAULT_REGISTRY, "factorio")


def test_solve_ratios_unknown_item_treated_as_raw():
    # iron-ore is not a seeded recipe -> recorded as raw demand, no stage
    stages = solve_ratios("iron-plate", 10.0, DEFAULT_REGISTRY, "factorio")
    assert all(s.output_item == "iron-plate" for s in stages)


# ---- belts ----
def test_belts_required_factorio_express():
    # express belt = 45 items/s; to carry 90 items/s need 2 belts
    assert belts_required(90.0, "factorio", "express-transport-belt") == 2
    # 45 items/s exactly fits 1 express belt
    assert belts_required(45.0, "factorio", "express-transport-belt") == 1


def test_belts_required_picks_top_tier():
    # 100 items/s on factorio top tier (45/s) -> ceil(2.22) = 3 belts
    assert belts_required(100.0, "factorio") == 3


def test_belts_required_satisfactory_mk5():
    # mk5 = 13 items/s; 26 items/s -> 2 belts
    assert belts_required(26.0, "satisfactory", "mk5-conveyor") == 2


def test_belts_required_unknown_game_raises():
    with pytest.raises(KeyError):
        belts_required(10.0, "no-such-game")


# ---- Little's Law ----
def test_littles_law():
    assert little_law(10.0, 2.0) == 20.0
    assert little_law(0.0, 5.0) == 0.0


# ---- bottleneck ----
def test_bottleneck_picks_tightest():
    stages = solve_ratios("electronic-circuit", 10.0, DEFAULT_REGISTRY, "factorio")
    rep = bottleneck_analysis(stages)
    assert rep.bottleneck_stage is not None
    assert 0.0 <= rep.bottleneck_utilization <= 1.0 + 1e-9
    assert len(rep.stages) == len(stages)
    assert rep.stages[0][1] >= rep.stages[-1][1]  # sorted desc


def test_bottleneck_empty_stages():
    rep = bottleneck_analysis([])
    assert rep.bottleneck_stage is None
    assert rep.recommendations


# ---- balancer ----
def test_balancer_1_1_passthrough():
    b = balancer_design(1, 1)
    assert b["splitters"] == 0


def test_balancer_4_4():
    b = balancer_design(4, 4)
    assert b["splitters"] == 3
    assert b["balanced"] is True


def test_balancer_2_4():
    b = balancer_design(2, 4)
    assert b["splitters"] >= 1


def test_balancer_rejects_zero():
    with pytest.raises(ValueError):
        balancer_design(0, 4)


# ---- modules ----
def test_machine_config_speed_module():
    mc = machine_config("assembling-machine-3", "factorio", ["speed-module-3"])
    assert mc.effective_craft_speed() == pytest.approx(1.25 * 1.5)


def test_machine_config_unknown_machine_raises():
    with pytest.raises(KeyError):
        machine_config("no-such-machine", "factorio")


# ---- verdict classification ----
def test_classify_verdict_optimized():
    class FakeBot:
        bottleneck_utilization = 0.5
    assert classify_verdict(FakeBot(), feasible=True, data_available=True) == Verdict.OPTIMIZED


def test_classify_verdict_conditional():
    class FakeBot:
        bottleneck_utilization = 0.99
    assert classify_verdict(FakeBot(), feasible=True, data_available=True) == Verdict.CONDITIONAL


def test_classify_verdict_infeasible():
    class FakeBot:
        bottleneck_utilization = 0.5
    assert classify_verdict(FakeBot(), feasible=False, data_available=True) == Verdict.INFEASIBLE


def test_classify_verdict_inconclusive_no_data():
    class FakeBot:
        bottleneck_utilization = 0.5
    assert classify_verdict(FakeBot(), feasible=True, data_available=False) == Verdict.INCONCLUSIVE


def test_valid_verdicts_match():
    assert set(VERDICTS) == set(v.value for v in Verdict)


# ---- end to end ----
def test_solve_grid_degraded_mode():
    sol = solve_grid("electronic-circuit", 10.0, DEFAULT_REGISTRY, "factorio", data_available=False)
    assert sol.verdict == Verdict.INCONCLUSIVE
    assert sol.stages == []


def test_solve_grid_satisfactory():
    sol = solve_grid("reinforced-iron-plate", 5.0, DEFAULT_REGISTRY, "satisfactory")
    assert sol.verdict.value in VERDICTS
    assert sol.power_kw_total >= 0
    assert sol.pollution_per_min_total == 0.0  # Satisfactory has no pollution


def test_solve_grid_power_pollution_summary():
    sol = solve_grid("copper-plate", 30.0, DEFAULT_REGISTRY, "factorio")
    assert sol.power_kw_total > 0
    assert sol.pollution_per_min_total > 0
    assert sol.bottleneck.bottleneck_stage is not None
