# test-scenarios.md - Skill 198: automation-grid-game-design

Five concrete end-to-end scenarios. Each lists inputs, expected steps,
applicable quality gates, and the engine cross-check. The scenarios exercise
all universal gates U1-U6 and the domain gates G1, G2, G3, G4, plus all four
verdict categories. They are executed computationally by `tools/run_test_scenarios.py`
and mirrored in the pytest suite `tests/test_automation_engine.py`.

---

## Scenario 1: Standard analysis (Factorio electronic-circuit line)
- **Input:** "Optimize a Factorio electronic-circuit line for 10 items/sec
  with assembling-machine-2 and express belts."
- **Expected:** sub-gather-requirements -> sub-evidence-collector ->
  sub-core-analysis -> sub-knowledge-updater -> sub-advisor -> quality gate.
- **Engine cross-check:** `automation_grid.solve_grid("electronic-circuit", 10.0,
  DEFAULT_REGISTRY, "factorio")` -> stages >= 1, power > 0, bottleneck stage
  identified, verdict in the declared set (Conditional for a capacity-bound
  electronic-circuit stage).
- **Gates:** U1-U6 + G1, G2, G3, G4.
- **Verdict target:** Optimized Layout or Conditional (bottleneck).

## Scenario 2: Minimal-input analysis (Satisfactory reinforced-iron-plate)
- **Input:** "Satisfactory reinforced-iron-plate, 5/s" (terse, defaults applied).
- **Expected:** defaults applied with explicit assumption statement (machine
  tiers, belt tier); never fabricate missing values.
- **Engine cross-check:** `solve_grid("reinforced-iron-plate", 5.0,
  DEFAULT_REGISTRY, "satisfactory")` -> verdict valid, pollution == 0
  (Satisfactory has no pollution in the seeded model).
- **Gates:** U1-U6 + G1, G2, G3, G4.

## Scenario 3: Comparison scenario (two rates, same item)
- **Input:** "Compare iron-gear-wheel at 5/s vs 20/s."
- **Expected:** side-by-side scorecard + evidence-based winner; sub-core-analysis
  applied to both; higher rate requires >= as many machines and >= as many belts.
- **Engine cross-check:** `solve_grid("iron-gear-wheel", 5.0, ...)` vs
  `solve_grid("iron-gear-wheel", 20.0, ...)` -> belts_total and machine count
  scale up with the target rate.
- **Gates:** U3 (evidence hierarchy), U6, G1, G2, G3, G4.

## Scenario 4: Risk / bottleneck scenario (Factorio copper-plate at high rate)
- **Input:** "Assess risk of a Factorio copper-plate line at 50 items/sec."
- **Expected:** multi-scenario (best/base/worst) risk output with bottleneck
  utilization and recommendations.
- **Engine cross-check:** `solve_grid("copper-plate", 50.0, ...)` ->
  bottleneck_utilization > 0 and >= 1 bottleneck recommendation.
- **Gates:** U2 (disclosure), G1, G2, G3, G4.

## Scenario 5: Degraded-mode scenario (data unavailable)
- **Input:** primary sources unreachable OR a required input variable missing.
- **Expected:** fallback chain + LIMITATION notice (degradation Level 2-3); no
  fabricated values; verdict maps to Inconclusive when the missing input is
  decisive; no stages fabricated.
- **Engine cross-check:** `solve_grid("electronic-circuit", 10.0, ...,
  data_available=False)` -> verdict == Inconclusive, stages == [].
- **Gates:** U2, graceful-degradation levels, G1, G2, G3, G4.

### Gate coverage matrix

| Gate | S1 | S2 | S3 | S4 | S5 |
|------|----|----|----|----|----|
| G1 | ok | ok | ok | ok | ok |
| G2 | ok | ok | ok | ok | ok |
| G3 | ok | ok | ok | ok | ok |
| G4 | ok | ok | ok | ok | ok |
| U1-U6 | ok | ok | ok | ok | ok |

### Verdict coverage
Optimized Layout, Conditional (bottleneck), Infeasible Target, Inconclusive
(exercised across scenarios 1-5; the engine unit tests in
`tests/test_automation_engine.py` cover all four verdict branches explicitly).
