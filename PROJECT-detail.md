# PROJECT-detail.md - Skill 198: automation-grid-game-design

## Executive Summary

`automation-grid-game-design` is a professional-grade harness for Claude Code
targeting the **Automation-Game Grid Logistics & Throughput Optimization**
domain. It transforms Claude into a domain expert that delivers structured,
evidence-backed outputs by combining real-time data aggregation, recognized
domain methods, academic research, and a **real computational engine**
(`automation_grid/`) into a single orchestrated workflow ending in a
risk/limitation-disclosed recommendation.

## Problem Statement

Practitioners in this domain face three structural gaps:
1. **Data fragmentation**: authoritative data scattered across wikis, calculators,
   and patch notes.
2. **Methodology gaps**: most advice lacks systematic, evidence-graded methods.
3. **No self-improvement**: static tools do not learn from new research.

This skill addresses all three via real-time aggregation, professional
frameworks, a real ratio/throughput engine, and a continuously-updated
knowledge crawl pipeline.

## Target Users & Use Cases

| User | Trigger Example | Skill Response |
|------|----------------|----------------|
| Practitioner | "Optimize my Factorio electronic-circuit line for 10/s" | Ratios + bottleneck + belt design + tradeoffs |
| Researcher | "Which flow/scheduling methods apply to game production chains?" | Method-grounded guidance with citations |
| Decision-maker | "Assess feasibility of 90/s blue-science with current power budget" | Risk-disclosed assessment with scenarios |
| Learner | "Explain Little's Law for factory games" | Educational framing with evidence + worked example |

## Harness Architecture

```
USER INPUT
    |
    v
[main.md - automation-grid-game-design]
    |
    +--> sub-gather-requirements.md  -> game, object, target rate, scope, language
    +--> sub-evidence-collector.md   -> recipe/machine/belt/module tables + method refs + news
    +--> sub-core-analysis.md        -> ratios, throughput/bottlenecks, belt/logistics, tradeoffs
    |                                 (cross-checked against automation_grid.solve_grid)
    +--> sub-knowledge-updater.md    -> tier-labeled academic citations + crawl gaps
    +--> sub-advisor.md              -> risk-disclosed conclusion, scenarios, risks, remediation
    |
    +--> [QUALITY GATE - main.md]
            ^ Claims cited to sources
            ^ Disclosure included
            ^ Evidence hierarchy respected (Tier 1-4)
            ^ Output formatted per template (U1-U6 + G1-G4)
```

## Full Sub-Skill Catalog

### 1. `sub-gather-requirements.md`
- **Purpose:** Clarify game, object, target rate, scope, timeframe, available
  inputs, target audience, and language before any data fetching.
- **Inputs:** Raw user message + any provided materials.
- **Outputs:** Structured requirements {game, object, target_rate (items/sec),
  scope, timeframe, available_inputs, target_audience, language, analysis_type}.
- **Tools:** Conversation only.
- **Quality Gate:** object + game confirmed; target rate in items/sec.

### 2. `sub-evidence-collector.md`
- **Purpose:** Fetch authoritative recipe/machine/belt/module tables + method
  references + recent developments.
- **Inputs:** Requirements object from Step 1.
- **Outputs:** Evidence bundle {current_data, authoritative_docs, recent_news,
  reference_benchmarks} with source + date + Tier per item.
- **Tools:** WebSearch, WebFetch, Read (SECOND-KNOWLEDGE-BRAIN.md).
- **Quality Gate:** current data + 1 authoritative document, or limitation flag.

### 3. `sub-core-analysis.md`
- **Purpose:** Ratios, throughput/bottlenecks (Little's Law), belt/logistics
  balancing, power/pollution/space tradeoffs, scaling scenarios.
- **Inputs:** Game, recipes, target output rate, available resources, language.
- **Outputs:** Ratios + throughput/bottleneck analysis + belt/logistics design
  + tradeoffs + best/base/worst scenarios + engine verdict.
- **Tools:** Read (SECOND-KNOWLEDGE-BRAIN.md), WebFetch (calculators/wikis),
  `automation_grid` engine, arithmetic.
- **Quality Gate (G1-G4):** ratios computed from recipe graphs; bottlenecks via
  Little's Law; belt balancing specified; tradeoffs addressed.

### 4. `sub-knowledge-updater.md`
- **Purpose:** Query SECOND-KNOWLEDGE-BRAIN.md; surface tier-labeled citations;
  flag gaps for the crawl pipeline.
- **Inputs:** Topic keywords from the current analysis.
- **Outputs:** 3-5 citations with Tier labels + flagged gaps + coverage rating.
- **Tools:** Read (SECOND-KNOWLEDGE-BRAIN.md), `automation_grid.search_brain`,
  WebSearch (gap-fill, max 2).
- **Quality Gate:** >= 1 academic source surfaced; coverage rating provided.

### 5. `sub-advisor.md`
- **Purpose:** Synthesize all prior analysis into a risk-disclosed conclusion.
- **Inputs:** Core analysis scorecard + evidence bundle + knowledge-base evidence.
- **Outputs:** Verdict (one of 4 declared) + scenarios + key risks + evidence
  chain + remediation + mandatory disclosure.
- **Tools:** Reasoning, `automation_grid.classify_verdict`, optional
  sub-knowledge-updater.
- **Quality Gate:** verdict is exactly one of {Optimized Layout, Conditional
  (bottleneck), Infeasible Target, Inconclusive}; disclosure before conclusion.

## Computational Engine (`automation_grid/`)

The engine is the authoritative numeric backend. Units are **items/sec**
throughout.

- **`config.py`** - belt throughput (Factorio 15/30/45 items/s; Satisfactory
  Mk1..Mk6 1/2/4.5/8/13/20 items/s), machine specs (craft_speed, power, pollution),
  module effects, evidence tiers, verdicts, quality gates, crawl config.
- **`engine.py`** - `Recipe`, `RecipeRegistry`, `solve_ratios` (reverse demand
  propagation), `bottleneck_analysis` (Little's Law), `balancer_design`
  (splitter trees), `power_pollution_summary`, `classify_verdict`, `solve_grid`.
- **`recipes.py`** - seeded Factorio + Satisfactory recipe database.
- **`knowledge.py`** - SECOND-KNOWLEDGE-BRAIN read/parse/dedup/append.
- **`logging_utils.py`** - structured rotating-file logging.

### Verdict decision rule
```
not data_available  -> Inconclusive
not feasible        -> Infeasible Target
util >= 0.98        -> Conditional (bottleneck)
else                -> Optimized Layout
```

## Modular Agent Framework (v2.0)

The harness is now backed by a real, runnable agent framework (`agent/`) and
modular directories, elevating the project to production-grade, open-source
standard.

### Agent framework (`agent/`)
- **SkillRegistry** (`registry.py`) - data-driven skill registration,
  resolution, execution, and validation. Skills load from
  `skills/definitions/*.json` and bind to handlers in `skill_handlers.py`.
- **ChainOfThoughtRouter** (`router.py`) - intent classification
  (optimize/compare/explain/assess) + explicit reasoning trace + ordered
  skill-sequence selection.
- **ToolRegistry** (`tools.py`) - rich tool definitions (JSON input/output
  schemas + Python handlers) backed by the `automation_grid` engine; dynamic
  invocation with schema validation + event emission.
- **HookManager** (`hooks.py`) - lifecycle / state-sync / event-emission
  hooks; faulty hooks are isolated (never break the harness).
- **EventBus** (`events.py`) - thread-safe pub/sub for structured event
  emission (skill/tool/gate/router/llm/context events).
- **ContextWindow + TokenCounter** (`context.py`) - context-window budget
  management with trim-to-budget semantics + pluggable token counting.
- **LLM providers** (`llm.py`) - `DeterministicProvider` (offline,
  engine-backed, fully functional) and `OpenAICompatibleProvider` (real HTTP,
  auto-selected when an API key is set, with graceful fallback).
- **HarnessRunner** (`runner.py`) - end-to-end orchestrator with
  production-grade error handling and graceful degradation (levels 0-4).

### Modular directories
- `/scripts` - automation, seeding, ingestion, local setup, CLI
  (`run_harness.py`, `validate_skills.py`, `setup_local.py`, `seed_recipes.py`,
  `ingest_knowledge.py`).
- `/references` - domain knowledge + prompt base-templates for RAG/agent
  grounding (`prompt_templates/*.md`, `domain_methods.md`).
- `/assets` - static resources, JSON Schemas, system diagrams, exported
  recipes (`schemas/*.json`, `diagrams/*.mmd`, `recipes.json`).
- `/config` - type-safe configuration (env vars, LLM parameters, feature
  flags) in `settings.py` + `default.json`, validated at load time.

### SKILL.md
`SKILL.md` is the comprehensive skill-registry documentation: how skills are
registered, resolved, executed, and validated, with input/output JSON
schemas, hooks, tools, the router, providers, and error handling.

## Skill File Format Specification

```markdown
---
name: {skill-name}
description: {one-line summary}
---
## Role & Persona
## Workflow (Harness Flow)
## Sub-skills Available   (main.md only)
## Tools
## Output Format
## Quality Gates
```

## E2E Execution Flow

```
1. User invokes /automation-grid-game-design [query]
2. main.md -> sub-gather-requirements -> structured requirements
3. sub-evidence-collector -> data bundle
4. sub-core-analysis -> ratios + throughput + logistics (engine-verified)
5. sub-knowledge-updater -> academic evidence entries
6. sub-advisor -> final draft with verdict + disclosure
7. main.md Quality Gate -> verify, auto-fix, deliver
```

**Error handling:** primary sources fail -> fallback chain -> knowledge base ->
explicit limitation flag; never silently proceed with stale data; degraded mode
maps the verdict to Inconclusive when decisive data is unavailable.

## SECOND-KNOWLEDGE-BRAIN Integration

- **Sources crawled:** ArXiv (cs.AI, cs.CE, cs.RO) + Semantic Scholar + RSS
  (Factorio forum, r/factorio, r/SatisfactoryGame, r/DysonSphereProgram).
- **Crawl config:** `KNOWLEDGE_CONFIG` in `automation_grid/config.py`.
- **Dedup:** SHA256 of DOI/URL (case/whitespace-insensitive).
- **Scoring:** recency(0.4) + keyword_relevance(0.4) + citation_count(0.2).

## Quality Gates Definition

Universal gates U1-U6 (see library SKILL-STANDARD.md) plus the domain gates
G1-G4 defined in `skills/main.md`.

## Test Scenarios

See `tests/test-scenarios.md` for 5 concrete scenario tests; the pytest suite
in `tests/` and `tools/run_test_scenarios.py` exercise them computationally.

## Key Design Decisions

1. Domain sub-skills kept separate (distinct methods/data).
2. Authoritative domain sources as primary; global fallback secondary.
3. Disclosure enforced at the quality-gate level, not optional.
4. SECOND-KNOWLEDGE-BRAIN as living memory updated by crawl pipeline.
5. Graceful degradation to knowledge base with explicit limitation flags.
6. A real computational engine backs every numeric claim; the harness prose
   interprets engine output rather than replacing it.
7. All engine units are items/sec for consistency; belt tables corrected to
   Factorio's canonical 15/30/45 items/s.

## Idea (Vietnamese)

> Tao skill tu dong hoa quy trinh thiet ke va toi uu hoa he thong tu dong
> (Automation Grid) trong cac game mo phong nha may (Factorio, Satisfactory),
> viec danh gia va dua de xuat phai dua tren cac phuong phap danh gia uy tin
> tren the gioi va dua ra cac de xuat, giai phap cai tien, khong ngung di crawl
> data tu cac ban thiet ke (blueprints) toi uu cua cong dong hoac document uy
> tin lien quan de cap nhat kien thuc cho skill ngay cang tot hon, xuhuong hon.
