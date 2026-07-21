# automation-grid-game-design

**Automation Grid System Design & Optimization in Factory/Automation Games**

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-blue)](https://claude.ai/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-93%20passed-brightgreen)](#testing)
[![Status](https://img.shields.io/badge/status-production--ready-success)](#)

A professional-grade Claude Code harness, **computational engine**, and
**modular agent framework** for **Automation-Game Grid Logistics & Throughput
Optimization**. It gathers real-time authoritative data, applies recognized
domain methods (recipe-graph ratio solving, Little's Law throughput/bottleneck
analysis, splitter-balancer design, power/pollution tradeoffs), integrates
academic research, and delivers evidence-backed, risk-disclosed outputs.

Supported games: **Factorio**, **Satisfactory**, **Dyson Sphere Program**.

## Features

<details>
<summary><b>Core capabilities</b></summary>

- **Modular agent framework** (`agent/`): skill registry, chain-of-thought
  router, lifecycle hooks, rich tool definitions (JSON schemas + handlers),
  context-window/token management, event bus, typed error handling, and an
  end-to-end orchestrator.
- **Real computational engine** (`automation_grid/`): recipe-graph ratio
  solver, Little's Law bottleneck analysis, belt/balancer design,
  power/pollution accounting, best/base/worst scenarios, verdict classification.
- **Fully runnable offline**: a deterministic, engine-backed LLM provider
  produces real structured outputs (no API key, no network). An
  OpenAI-compatible HTTP provider is auto-selected when an API key is set.
- **Type-safe configuration** (`config/`): env-var + JSON settings, LLM
  parameters, and system-wide feature flags, validated at load time.
- **Data-driven skills** (`skills/definitions/*.json`) bound to handlers,
  with prompt base-templates (`references/`) and JSON Schemas (`assets/`).
- Real-time data aggregation from authoritative game wikis & calculators.
- Systematic domain analysis methods (Tier-graded evidence).
- Academic research integration with an auto-updating knowledge base.
- Risk/limitation-disclosed outputs with scenario coverage.
- Self-improving knowledge pipeline (weekly academic + daily news crawl).
- Graceful degradation (5 levels) - never fabricates missing data.
- 10 quality gates (U1-U6 universal + G1-G4 domain) with auto-fix + 2-retry max.

</details>

## Why This Skill

Automation-Game Grid Logistics & Throughput Optimization practitioners face
fragmented data, inconsistent methodology, and tools that do not self-improve.
This skill unifies authoritative real-time data, recognized domain methods,
and a continuously-updated academic knowledge base - backed by a real
computational engine and a production-grade agent framework - into one
evidence-backed, risk-disclosed workflow.

## Installation

```bash
pip install -r requirements.txt
# or, for development:
pip install -e ".[dev]"
```

Install the skill files to `~/.claude/skills/` or use via the project `CLAUDE.md`.

## Quick Start

```bash
# Local setup (idempotent readiness check)
python scripts/setup_local.py

# Run the full harness on a query (offline, deterministic by default)
python scripts/run_harness.py "Optimize my Factorio electronic-circuit line for 10/s"
```

## Usage

### As a Claude Code skill
```
/automation-grid-game-design [your query]
```

### As a Python engine
```python
import automation_grid as ag

sol = ag.solve_grid("electronic-circuit", 10.0, ag.DEFAULT_REGISTRY, "factorio")
print(sol.verdict.value)        # Conditional (bottleneck)
print(ag.balancer_design(4, 4)) # 4:4 throughput balancer, 3 splitters
print(ag.little_law(10.0, 2.0)) # 20 items
```

### As an agent framework
```python
from agent import HarnessRunner
result = HarnessRunner().run("Optimize my Factorio electronic-circuit line for 10/s")
print(result.state.verdict["verdict"])   # Conditional (bottleneck)
print(result.report)
```

### With a real LLM (OpenAI-compatible)
```bash
AUTOMATION_GRID_API_KEY=sk-... python scripts/run_harness.py "..."
```

### Knowledge crawl pipeline
```bash
python scripts/ingest_knowledge.py --dry-run            # preview (config-aware)
python scripts/ingest_knowledge.py --news-only          # RSS news only
python scripts/ingest_knowledge.py --offline            # no network (CI)
python tools/knowledge_updater.py --dry-run --news-only --offline
```

## Architecture

```
automation_grid/        # importable computational engine
  config.py engine.py recipes.py knowledge.py logging_utils.py
agent/                  # modular agent framework
  schemas.py events.py errors.py state.py context.py hooks.py
  tools.py registry.py router.py llm.py skill_handlers.py runner.py
config/                 # type-safe settings (env + JSON + feature flags)
  settings.py default.json
skills/
  main.md + 5 sub-skills (Claude harness prose)
  definitions/*.json     # machine-readable skill specs (schemas + tools + gates)
references/
  prompt_templates/*.md  # base prompt templates (RAG grounding)
  domain_methods.md
assets/
  schemas/*.json         # JSON Schemas for every structured output
  diagrams/*.mmd          # harness + framework diagrams
  recipes.json           # exported seeded recipe database
scripts/                # automation, seeding, ingestion, setup, CLI
  run_harness.py validate_skills.py setup_local.py seed_recipes.py ingest_knowledge.py
tools/                  # crawl pipeline + validators
tests/                  # pytest suite (engine, crawl, validators, agent framework)
SKILL.md                # comprehensive skill-registry documentation
SECOND-KNOWLEDGE-BRAIN.md  # self-improving knowledge base
```

Harness flow: requirements -> evidence -> core analysis -> knowledge ->
synthesis -> quality gate. The `agent.HarnessRunner` wires a chain-of-thought
router, the skill registry, the tool registry, the LLM provider, hooks and a
context window to execute that flow end-to-end. See `SKILL.md` and
`PROJECT-detail.md` for the full architecture.

## Quality Gates

Universal gates U1-U6 plus domain gates defined in `skills/main.md`:

| Gate | Check |
|------|-------|
| U1 | >=3 sources cited, >=1 academic/authoritative |
| U2 | Disclosure/limitations before recommendation |
| U3 | Evidence hierarchy stated per source (Tier 1-4) |
| U4 | Language matches user preference |
| U5 | Output uses declared template (all sections) |
| U6 | Every claim traceable to >=1 source or flagged |
| G1 | Ratios computed from recipe graphs |
| G2 | Bottlenecks identified via throughput analysis (Little's Law) |
| G3 | Belt/logistics balancing specified (splitters/balancers) |
| G4 | Power/pollution/space tradeoffs addressed |

## Data Sources

- Game wikis (Factorio, Satisfactory, Dyson Sphere Program)
- Community calculators (FactorioLab, Kirk McDonald, Satisfactory Calculator)
- Throughput/balancer references; production-chain math references
- Blueprint libraries (factorioprints); mod/tool docs
- Academic: CHI PLAY, IEEE Trans. Games, Entertainment Computing,
  Computers & Operations Research, Simulation & Gaming, J. Simulation

## Testing

```bash
python -m pytest tests/ tools/test_knowledge_updater.py -q
python tools/validate_project.py        # 8-File Contract + production checks
python tools/run_test_scenarios.py      # structural + engine + agent scenarios
python scripts/validate_skills.py       # skill-definitions contract
python scripts/setup_local.py           # local readiness check
```

All commands exit 0 on success and run fully offline. Current status:
**93 pytest tests passed**, **96/96 contract checks passed**,
**115/115 scenario checks passed**, **92/92 skill-definition checks passed**.

## Knowledge Base

`SECOND-KNOWLEDGE-BRAIN.md` is auto-updated via `tools/knowledge_updater.py`
(ArXiv + Semantic Scholar + RSS). Dedup by SHA256 of DOI/URL; composite
scoring (recency + keyword relevance + citation count).

### Crawl schedule (cron)
```cron
# Weekly academic update (Mondays 08:00)
0 8 * * 1 python tools/knowledge_updater.py >> logs/knowledge_update.log 2>&1
# Daily news update (07:00)
0 7 * * * python tools/knowledge_updater.py --news-only >> logs/knowledge_news.log 2>&1
```

## Development

- Configuration: edit `config/default.json` or set `AUTOMATION_GRID_*` env vars.
- Add a skill: drop a `skills/definitions/<name>.json`, add a handler in
  `agent/skill_handlers.HANDLERS`, add a prompt template in
  `references/prompt_templates/`, and (optionally) a JSON Schema in
  `assets/schemas/`. Run `python scripts/validate_skills.py`.
- Add a tool: register a `Tool` in `agent.tools.build_default_tools`.

## Roadmap

- [x] Phase 0: Architecture
- [x] Phase 1: Core sub-skills (5)
- [x] Phase 2: Main harness + gates
- [x] Phase 3: Knowledge pipeline
- [x] Phase 4: Testing
- [x] Phase 5: Integration & polish (v1.1.0)
- [x] Phase 6: Modular agent framework (skill registry, router, hooks, tools)
- [x] Phase 7: Skill registry data + references + assets + schemas
- [x] Phase 8: Type-safe config + scripts (setup/seed/ingest/run/validate)
- [x] Phase 9: Production hardening + docs - PRODUCTION READY v2.0.0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions must keep
`python tools/validate_project.py`, `python tools/run_test_scenarios.py`,
`python scripts/validate_skills.py`, and the pytest suite green.

## License

MIT - see [LICENSE](LICENSE).

## Acknowledgments

Domain data from the Factorio, Satisfactory, and Dyson Sphere Program
communities and wikis; academic grounding from operations-research and
game-studies literature.

## Citation

```bibtex
@software{automation-grid-game-design,
  title  = {automation-grid-game-design: Automation Grid System Design & Optimization in Factory/Automation Games},
  year   = {2026},
  version= {2.0.0}
}
```