# CLAUDE.md - Skill 198: automation-grid-game-design

## Skill Identity
- **Skill Name:** `automation-grid-game-design`
- **Tagline:** Automation Grid System Design & Optimization in Factory/Automation Games - Automation-Game Grid Logistics & Throughput Optimization analysis & decision-support harness.
- **Current Phase:** Phase 9 - Production Hardening & Docs (PRODUCTION READY v2.0.0)
- **Folder:** `D:\972026\198-automation-grid-game-design\`

---

## Problem This Skill Solves

This skill provides a structured, evidence-backed analytical workflow for
**Automation-Game Grid Logistics & Throughput Optimization** (Factorio,
Satisfactory, Dyson Sphere Program). It gathers authoritative real-time and
reference data, applies recognized domain methods (recipe-graph ratio solving,
Little's Law throughput/bottleneck analysis, splitter-balancer design,
power/pollution tradeoffs), cross-references academic research, and delivers
actionable outputs that are fully evidenced, risk/limitation-disclosed, and
traceable to authoritative sources - continuously self-improving through an
automated knowledge crawl pipeline. A real computational engine
(`automation_grid/`) and a modular agent framework (`agent/`) back every
numeric claim and orchestrate the whole workflow.

---

## Harness Flow Summary

```
/automation-grid-game-design invoked
|
+-- Step 1: sub-gather-requirements   -> clarify game, object, target rate, scope, language.
+-- Step 2: sub-evidence-collector    -> fetch recipe/machine/belt/module tables + method refs + news.
+-- Step 3: sub-core-analysis         -> ratios, throughput/bottlenecks (Little's Law), belt/logistics, tradeoffs, scenarios.
+-- Step 4: sub-knowledge-updater     -> query SECOND-KNOWLEDGE-BRAIN.md; tier-labeled citations; flag crawl gaps.
+-- Step 5: sub-advisor               -> risk-disclosed conclusion, scenarios, risks, evidence chain, remediation.
\-- Step 6: main (quality gate)       -> verify evidence hierarchy, disclosure, output polish (U1-U6 + G1-G4).
```

The same flow is executable programmatically via `agent.HarnessRunner`, which
wires a chain-of-thought router, the skill registry, the tool registry, an LLM
provider, hooks, and a context window.

---

## Sub-Skills

| `skills/sub-gather-requirements.md` | Clarify game, object, target rate, scope, timeframe, inputs, audience, language. |
| `skills/sub-evidence-collector.md` | Fetch authoritative recipe/machine/belt/module tables + method refs + recent news. |
| `skills/sub-core-analysis.md` | Ratios, throughput/bottlenecks (Little's Law), belt/logistics, tradeoffs, scenarios. |
| `skills/sub-knowledge-updater.md` | Query SECOND-KNOWLEDGE-BRAIN.md; tier-labeled citations; flag crawl gaps. |
| `skills/sub-advisor.md` | Synthesize risk-disclosed conclusion, scenarios, risks, evidence chain, remediation. |

Machine-readable skill specs: `skills/definitions/*.json` (bound to handlers in
`agent/skill_handlers.py`). Full registry documentation: `SKILL.md`.

---

## Tools Required

- **WebSearch** - live domain news, reports, standards updates
- **WebFetch** - scrape Automation-Game Grid Logistics & Throughput Optimization authoritative sources
- **Read / Write** - read SECOND-KNOWLEDGE-BRAIN.md; append knowledge entries
- **Bash** - run `scripts/ingest_knowledge.py` / `tools/knowledge_updater.py`; run engine cross-checks
- **automation_grid** (Python package) - authoritative ratio/throughput/balancer engine
- **agent** (Python package) - skill registry, router, hooks, tools, runner
- **Skill** - invoke sub-skills sequentially through the harness

---

## Knowledge Sources

### Domain Authoritative Sources
- Game wikis (Factorio, Satisfactory, Dyson Sphere Program)
- Community calculators (FactorioLab, Kirk McDonald, Satisfactory Calculator)
- Throughput/balancer references; production-chain math references
- Blueprint libraries (factorioprints); mod/tool docs

### Academic & Research Sources
- Proceedings of CHI PLAY (ACM); IEEE Transactions on Games
- Entertainment Computing (Elsevier); Computers & Operations Research
- Simulation & Gaming (SAGE); Journal of Simulation

### Academic Crawl Targets
- ArXiv categories cs.AI, cs.CE, cs.RO
- Semantic Scholar keyword clusters
- RSS: Factorio forum, r/factorio, r/SatisfactoryGame, r/DysonSphereProgram

---

## Supporting Python Modules

| File / Package | Purpose |
|------|---------|
| `automation_grid/` | Production-grade engine: config, engine, recipes, knowledge, logging. |
| `agent/` | Modular agent framework: skill registry, router, hooks, tools, context, events, LLM providers, runner. |
| `config/` | Type-safe settings (env + JSON + feature flags), validated at load. |
| `scripts/run_harness.py` | CLI entry point for the full harness. |
| `scripts/validate_skills.py` | Skill-definitions contract validator. |
| `scripts/setup_local.py` | Idempotent local setup / readiness check. |
| `scripts/seed_recipes.py` | Export / extend the seeded recipe database. |
| `scripts/ingest_knowledge.py` | Config-aware knowledge crawl wrapper. |
| `tools/knowledge_updater.py` | Crawl pipeline: ArXiv + Semantic Scholar + RSS -> SECOND-KNOWLEDGE-BRAIN.md. |
| `tools/validate_project.py` | 8-File Contract + production validator. |
| `tools/run_test_scenarios.py` | Structural + content + engine + agent scenario validator. |
| `tools/test_knowledge_updater.py` | Standalone unit tests for the crawl pipeline. |

---

## Automated Knowledge Update Schedule

```cron
# Weekly academic update (Mondays 8:00 AM)
0 8 * * 1 python D:/972026/198-automation-grid-game-design/tools/knowledge_updater.py >> logs/knowledge_update.log 2>&1

# Daily news update (Daily 7:00 AM)
0 7 * * * python D:/972026/198-automation-grid-game-design/tools/knowledge_updater.py --news-only >> logs/knowledge_news.log 2>&1
```

Manual: `python scripts/ingest_knowledge.py --dry-run` | `--news-only` | `--offline`
(equivalently `python tools/knowledge_updater.py ...`).

---

## Active Development Tasks

- [x] Phase 0: Architecture & source map
- [x] Phase 1: Core sub-skills (production-grade)
- [x] Phase 2: Main harness + quality gates + degradation
- [x] Phase 3: Knowledge pipeline + engine + tests + cron
- [x] Phase 4: Testing & validation (pytest + validators pass)
- [x] Phase 5: Integration & polish (v1.1.0)
- [x] Phase 6: Modular agent framework (skill registry, router, hooks, tools)
- [x] Phase 7: Skill registry data + references + assets + JSON schemas
- [x] Phase 8: Type-safe config + scripts (setup/seed/ingest/run/validate)
- [x] Phase 9: Production hardening + docs (PRODUCTION READY v2.0.0)

---

## References

- `PROJECT-detail.md` - full technical specification
- `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` - build roadmap
- `SKILL.md` - comprehensive skill-registry documentation
- `SECOND-KNOWLEDGE-BRAIN.md` - self-improving knowledge base
- `D:\972026\SKILL-STANDARD.md` - library-wide standard