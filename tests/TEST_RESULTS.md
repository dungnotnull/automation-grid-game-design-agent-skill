# TEST_RESULTS.md - Skill 198: automation-grid-game-design

> Last updated: 2026-07-20 (v2.0.0). All results produced offline.

## Summary

| Suite | Result |
|-------|--------|
| `python -m pytest tests/ tools/test_knowledge_updater.py -q` | **93 passed** |
| `python tools/validate_project.py` | **96/96 checks passed** |
| `python tools/run_test_scenarios.py` | **115/115 checks passed** |
| `python scripts/validate_skills.py` | **92/92 checks passed** |
| `python scripts/setup_local.py` | exit 0, ready |
| `python scripts/run_harness.py "Optimize my Factorio electronic-circuit line for 10/s"` | ok, verdict=Conditional (bottleneck), 10/10 gates |

## pytest breakdown

| File | Tests | Coverage |
|------|------|----------|
| `tests/test_automation_engine.py` | recipe model, registry, ratio solver, belts, Little's Law, bottleneck, balancer, modules, verdicts, end-to-end grid | engine core |
| `tests/test_crawl_pipeline.py` | hash dedup, scoring, config validation, dry-run offline, append dedup, brain hashes, CrawlEntry | crawl pipeline |
| `tests/test_validate_project.py` | validate_project + run_test_scenarios + knowledge_updater dry-run subprocesses | validators |
| `tests/test_agent_framework.py` | schemas, events, errors/retry/fallback, state, context window, hooks, tools (13), registry, router (4 intents), LLM providers, runner end-to-end, config env overrides, scripts subprocesses | agent framework |

## Scenario coverage (run_test_scenarios.py)

- S1 standard: Factorio electronic-circuit @ 10/s -> Conditional (bottleneck).
- S2 minimal: Satisfactory reinforced-iron-plate @ 5/s.
- S3 comparison: iron-gear-wheel 5/s vs 20/s -> belts/machines scale up.
- S4 risk/bottleneck: copper-plate @ 50/s -> utilization + recommendations.
- S5 degraded: data_available=False -> Inconclusive, no stages fabricated.
- A optimize intent (agent): full pipeline, all gates pass.
- B explain intent (agent): core_analysis skipped, applicable gates pass.
- C degraded (agent): unknown item -> level 3, Inconclusive.
- D tool registry + skill definitions load + validate.

## Contract coverage (validate_project.py)

8-File Contract + sub-skill structure + frontmatter + quality gates + verdicts
+ knowledge-base integrity + package import + belt/machine/module tables +
crawl config + docs consistency + **agent framework + config + modular
directories + offline smoke run**.

## Notes

- The harness runs deterministically offline via `agent.DeterministicProvider`.
- No network, no API key, no model pulling required for any green result.
- CI matrix: Python 3.9 / 3.10 / 3.11 / 3.12.