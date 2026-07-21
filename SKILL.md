# SKILL.md - automation-grid-game-design Skill Registry

> Comprehensive registry documentation for the automation-grid-game-design
> skill: how skills are **registered**, **resolved**, **executed**, and
> **validated**, including input/output JSON schemas, hooks, tools, and the
> chain-of-thought router.

This document is the canonical reference for the agent framework that powers
the skill. The framework lives in `agent/`; machine-readable skill
definitions live in `skills/definitions/*.json`; prompt base-templates live in
`references/prompt_templates/`; JSON Schemas live in `assets/schemas/`.

---

## 1. Architecture at a glance

```
USER QUERY
   |
   v
HarnessRunner (agent/runner.py)
   |-- ContextWindow + TokenCounter     (context budget, trimming)
   |-- ChainOfThoughtRouter             (intent + reasoning -> skill sequence)
   |-- SkillRegistry                    (resolve + execute skills)
   |     |-- skills/definitions/*.json   (data-driven skill specs)
   |     |-- agent/skill_handlers.py     (per-skill execution handlers)
   |-- ToolRegistry                     (schema + handler tools)
   |     |-- automation_grid engine      (solve_grid, Little's Law, balancer, ...)
   |-- LLMProvider                       (deterministic | OpenAI-compatible)
   |-- HookManager + EventBus            (lifecycle, state-sync, events)
   v
FINAL REPORT (markdown) + RunResult (JSON)
```

The harness is **fully runnable offline**: the default
`DeterministicProvider` computes real, engine-backed structured outputs, so
the entire pipeline executes and is unit-testable with no network and no API
key. An OpenAI-compatible HTTP provider is selected automatically when
`AUTOMATION_GRID_API_KEY` is set.

---

## 2. Skill registry

### 2.1 Registration

Skills are registered in two layers:

1. **Data layer** - `skills/definitions/<skill>.json` declares the skill's
   name, description, ordered `step`, `inputs_schema`, `outputs_schema`,
   `prompt_template` reference, allowed `tools`, and applicable `gates`.
2. **Code layer** - `agent/skill_handlers.HANDLERS` maps each skill name to a
   Python handler `f(state, tools, llm, ctx) -> dict`.

`agent.registry.load_skill_definitions(definitions_dir)` loads every JSON
file, binds each to its handler (looked up by name in `HANDLERS`), and
validates the resulting `SkillRegistry` (schemas have a top-level `type`,
tools are non-empty strings, handlers exist). A skill whose handler is
missing raises `SkillNotFound` at load time - fail-fast, no silent stubs.

### 2.2 Resolution

`SkillRegistry.get(name)` resolves a skill by name (raises `SkillNotFound`).
`SkillRegistry.ordered()` returns skills sorted by `step` - the canonical
harness execution order. The `ChainOfThoughtRouter` selects a *subset*
sequence per intent (e.g. `explain` skips the production-line analysis).

### 2.3 Execution

`SkillRegistry.execute(name, state, tools, llm, ctx)`:

1. Emits `skill.started` on the EventBus.
2. Calls the handler, which derives inputs from `SessionState`, calls
   `llm.structured(skill, inputs)`, and writes the result back into state.
3. Validates the handler output against the skill's `outputs_schema`
   (`agent.schemas.validate_instance`); raises `SchemaError` on mismatch.
4. Emits `skill.completed` (or `skill.failed` / `skill.output_invalid`).

### 2.4 Validation

Two levels of validation:

- **Static** - `SkillRegistry.validate_definitions()` checks every skill has
  schemas + handler + well-formed tool refs. `scripts/validate_skills.py`
  additionally checks prompt-template files exist, tools exist in the default
  `ToolRegistry`, and gates are declared.
- **Runtime** - every skill output is validated against its `outputs_schema`
  on each execution; every tool invocation validates input + output against
  the tool's schemas.

---

## 3. Registered skills

| Step | Skill | Description | Tools | Gates |
|------|-------|-------------|------|-------|
| 1 | `gather_requirements` | Clarify game, object, target rate, scope, language. | list_recipes | U4 |
| 2 | `evidence_collector` | Fetch recipe/machine/belt/module tables + method refs. | list_recipes, search_brain | U1, U3 |
| 3 | `core_analysis` | Ratios, Little's Law, belt/balancer, tradeoffs, scenarios (engine-verified). | solve_grid, solve_ratios, bottleneck_analysis, balancer_design, little_law, belts_required, power_pollution_summary, machine_config | G1, G2, G3, G4 |
| 4 | `knowledge_updater` | Tier-labeled academic citations + crawl gaps. | search_brain, append_knowledge | U1, U3 |
| 5 | `advisor` | Risk-disclosed conclusion, scenarios, risks, evidence chain. | classify_verdict, valid_verdicts | U2, U6 |
| 6 | `quality_gate` | Verify applicable U1-U6 + G1-G4 gates. | - | U1-U6, G1-G4 |

Each skill's machine-readable spec is in `skills/definitions/<skill>.json`;
its prompt base-template is in `references/prompt_templates/<skill>.md`; its
output JSON Schema is mirrored in `assets/schemas/<skill>.schema.json`.

---

## 4. Input / Output JSON schemas

Every skill declares `inputs_schema` and `outputs_schema` (JSON Schema
draft-07 subset). The framework's pure-stdlib validator
(`agent.schemas`) supports: `type`, `properties`, `required`, `enum`,
`minimum`, `maximum`, `minItems`, `maxItems`, `items`, `additionalProperties`,
`pattern`, `minLength`, `maxLength`, `const`, `$ref` (local), and `type`
as a list (union). For full JSON Schema support install `jsonschema`; the
shipped validator covers 100% of this project's schemas.

Canonical schemas (see `assets/schemas/`):

- `requirements.schema.json` - `gather_requirements` output
- `evidence.schema.json` - `evidence_collector` output
- `analysis.schema.json` - `core_analysis` output
- `knowledge.schema.json` - `knowledge_updater` output
- `verdict.schema.json` - `advisor` output

Example (`verdict.schema.json`, excerpt):
```json
{
  "type": "object",
  "required": ["verdict", "key_risks", "evidence_chain", "remediation", "disclosure"],
  "properties": {
    "verdict": {"type": "string", "enum": [
      "Optimized Layout", "Conditional (bottleneck)",
      "Infeasible Target", "Inconclusive"]}
  }
}
```

---

## 5. Tools

Tools are defined in `agent.tools` as `Tool(name, description,
input_schema, output_schema, handler)`. `build_default_tools()` registers
the real engine-backed tool set:

| Tool | Input | Output | Backed by |
|------|-------|--------|-----------|
| `solve_grid` | target_item, target_rate, game, buffer_time_s?, data_available? | full grid solution + verdict | `automation_grid.solve_grid` |
| `solve_ratios` | target_item, target_rate, game | stage list | `automation_grid.solve_ratios` |
| `bottleneck_analysis` | target_item, target_rate, game, buffer_time_s? | bottleneck report | `automation_grid.bottleneck_analysis` |
| `balancer_design` | input_belts, output_belts | topology + splitter count | `automation_grid.balancer_design` |
| `little_law` | throughput_lambda, waiting_time_s | {lambda, W, L} | `automation_grid.little_law` |
| `belts_required` | rate_items_per_sec, game, belt? | belt count | `automation_grid.belts_required` |
| `classify_verdict` | bottleneck_utilization, feasible, data_available? | verdict | `automation_grid.classify_verdict` |
| `power_pollution_summary` | target_item, target_rate, game | tradeoff totals | `automation_grid.power_pollution_summary` |
| `machine_config` | machine, game, modules? | effective craft speed + effects | `automation_grid.machine_config` |
| `search_brain` | keywords, max_results? | citations | `automation_grid.search_brain` |
| `list_recipes` | game? | recipe output items | `automation_grid.DEFAULT_REGISTRY` |
| `valid_verdicts` | - | declared verdict set | `automation_grid.valid_verdicts` |
| `append_knowledge` | entry | appended + dedup count | `automation_grid.knowledge.append_entry` |

`ToolRegistry.invoke(name, arguments)` validates the arguments against the
tool's `input_schema`, runs the handler, validates the result against the
`output_schema`, and emits `tool.invoked` / `tool.completed` / `tool.failed`
events. Invalid input/output raises `SchemaError`.

---

## 6. Hooks

Lifecycle hooks are managed by `agent.hooks.HookManager` and triggered at
named points: `pre_run`, `post_run`, `pre_skill`, `post_skill`, `on_tool`,
`on_gate`, `on_error`, `on_event`. A failing hook is **isolated** (it emits
`hook.failed` and cannot break the harness).

Built-in hook factories (`agent.hooks.Hooks`):

| Hook | Purpose |
|------|---------|
| `structured_log(logger)` | Emit every lifecycle event to a structured logger. |
| `state_sync(snapshot_dir?)` | Snapshot `SessionState` after each skill step (persisted if dir given). |
| `event_emission(tap)` | Re-emit lifecycle events onto a metrics tap bus. |
| `token_budget_guard()` | Escalate degradation when the token budget is exhausted. |
| `metrics_collector(sink?)` | Collect a flat metrics record per skill step. |

---

## 7. Events

`agent.events.EventBus` is a thread-safe synchronous pub/sub bus. Events are
immutable `Event(type, payload, timestamp)` records. Subscribe with
`bus.subscribe(type, fn)` (or `"*"` for all); publish with `bus.emit(type,
**payload)`. The bus keeps a bounded history for diagnostics. Emitted event
types include: `run.started`, `run.completed`, `run.degraded`, `skill.started`,
`skill.completed`, `skill.failed`, `tool.invoked`, `tool.completed`,
`tool.failed`, `router.decision`, `llm.structured`, `llm.fallback`,
`context.trimmed`, `state.synced`, `tokens.exhausted`, `hook.failed`.

---

## 8. Context window & token management

`agent.context.ContextWindow` enforces a token budget (default 8192, from
`config.settings`). It keeps a `reserve_output` margin (default 1024) for the
final report. When the input budget is exceeded it drops the oldest
non-protected (non-system) messages first and emits `context.trimmed`; if
nothing droppable remains it raises `ContextOverflow` so the runner can apply
degradation. `TokenCounter` is pluggable (default heuristic ~4 chars/token; a
real tokenizer can be injected).

---

## 9. Router (chain-of-thought)

`agent.router.ChainOfThoughtRouter` classifies the user intent
(`optimize` | `compare` | `explain` | `assess`) via keyword patterns, emits
an explicit reasoning trace, and selects the ordered skill sequence:

- `optimize` / `compare` / `assess` -> full 6-skill sequence.
- `explain` -> `gather_requirements` -> `knowledge_updater` -> `advisor` ->
  `quality_gate` (skips recipe/evidence/core analysis).

The router is deterministic and unit-testable; override `classify_intent` to
plug in an LLM-based classifier.

---

## 10. LLM providers

`agent.llm` defines the `LLMProvider` interface (`complete`, `structured`)
and two real providers:

- `DeterministicProvider` - offline, engine-backed. `structured(skill,
  inputs)` dispatches to a per-skill generator that parses the query, calls
  the `automation_grid` engine, and queries the knowledge base to produce
  real, schema-validated outputs. This is the default and is **not** a stub.
- `OpenAICompatibleProvider` - real HTTP client (uses `requests` when
  available) for any OpenAI-compatible chat endpoint. Selected automatically
  when `AUTOMATION_GRID_API_KEY` is set; falls back to the deterministic
  provider on any HTTP/parse failure (graceful degradation).

`build_provider(api_key, base_url, model, bus)` selects the provider per
`config.settings`.

---

## 11. Error handling & graceful degradation

`agent.errors` defines a typed exception hierarchy
(`AgentError`, `SkillNotFound`, `ToolNotFound`, `SchemaError`,
`ContextOverflow`, `LLMError`, `GateFailed`, `DegradedMode`) plus a `retry`
decorator (exponential backoff, injectable sleep) and `run_with_fallback`
(primary + fallback chain). The runner catches `AgentError` per skill,
increments the degradation level (0-4), emits `run.degraded`, and continues;
at level 4 it stops and emits a `DATA UNAVAILABLE` / `Inconclusive` result -
never fabricating output.

---

## 12. Quality gates

Universal gates U1-U6 + domain gates G1-G4 (defined in
`automation_grid.config.QUALITY_GATES` and `skills/main.md`). The
`quality_gate` skill enforces only the **applicable** gates for a run (a gate
is applicable iff its owning skill ran), so `explain`-intent runs are not
penalised for skipping the production-line domain gates. Non-applicable gates
are recorded as `n/a`.

---

## 13. Running the harness

```bash
# CLI (uses config.settings; deterministic by default)
python scripts/run_harness.py "Optimize my Factorio electronic-circuit line for 10/s"

# JSON summary only
python scripts/run_harness.py --query "..." --json --no-report

# Use a real LLM (OpenAI-compatible)
AUTOMATION_GRID_API_KEY=sk-... python scripts/run_harness.py "..."
```

Programmatic:
```python
from agent import HarnessRunner
result = HarnessRunner().run("Optimize my Factorio electronic-circuit line for 10/s")
print(result.state.verdict["verdict"])   # Conditional (bottleneck)
print(result.report)
```

---

## 14. Validation & testing

```bash
python scripts/validate_skills.py     # skill definitions contract
python tools/validate_project.py      # 8-File Contract + production checks
python tools/run_test_scenarios.py   # structural + engine scenarios
python -m pytest tests/ tools/test_knowledge_updater.py -q
```

All commands exit 0 on success and run fully offline.