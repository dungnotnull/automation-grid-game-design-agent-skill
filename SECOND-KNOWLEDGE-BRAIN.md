# SECOND-KNOWLEDGE-BRAIN.md - Skill 198: automation-grid-game-design

> **Living Knowledge Base** - updated by `tools/knowledge_updater.py` on a weekly
> schedule. All entries date-stamped; new entries appended at the bottom.
> Evidence hierarchy: Systematic Review > Meta-Analysis > Guideline/RCT >
> Cohort > Expert Consensus > News.

---

## 1. Core Concepts & Frameworks

### 1.1 Foundational Methods

- **Production chains & recipe graphs.** A recipe graph maps inputs to outputs
  with rates (items/sec). Intermediate products flow between stages; recipe
  selection depends on productivity/speed modules and machine tier.
- **Ratios (reverse demand propagation).**
  `assembler_count = target_rate / (craft_speed * recipe_output_per_craft / craft_time * (1 + productivity_bonus))`.
  Ingredient demand is back-propagated as the child stage's target rate; exact
  integer ratios use the LCM across stages.
- **Throughput & bottlenecks (Little's Law).** `L = lambda * W` (expected items
  in system = throughput * mean residence time). The bottleneck is the stage
  with the highest utilization; its capacity bounds the line:
  `throughput_cap = stage_rate / utilization`.
- **Logistics & layout.** Belt throughput by tier (Factorio: 15/30/45 items/s;
  Satisfactory: Mk1..Mk6 = 1/2/4.5/8/13/20 items/s). Splitters/balancers
  (1:n, n:n lane balancers), train/bot logistics, modular blueprints.
- **Tradeoffs.** Power (sum of machine power * count), pollution/min, spatial
  footprint, module/beacon cost. Speed modules raise throughput AND power;
  productivity modules raise output AND pollution; efficiency modules cut power.

### 1.2 Evidence Hierarchy (this domain)

- **Tier 1**: Systematic review / meta-analysis / official standard
- **Tier 2**: Peer-reviewed academic paper / RCT
- **Tier 3**: Industry report / professional association guideline
- **Tier 4**: News / blog / vendor material

### 1.3 Knowledge categories covered

- Production chains & recipe graphs
- Throughput & bottleneck analysis (Little's Law)
- Belt/logistics balancing (splitters, balancers)
- Power & pollution tradeoffs
- Spatial layout & modular blueprints
- Scaling & ratio math

---

## 2. Key Research Papers & Standards

| Title | Authors | Year | Venue | DOI/URL | Tier |
|------|---------|------|-------|---------|------|
| Little's Law | Little, J. D. C. | 1961 | Oper. Res. 9(3) | 10.1287/opre.9.3.383 | 1 |
| Flow-shop scheduling: a review | Framinan et al. | 2004 | Eur. J. Oper. Res. | 10.1016/S0377-2217(03)00358-8 | 1 |
| Does gamification work? | Hamari et al. | 2014 | Comput. Hum. Behav. | 10.1016/j.chb.2014.03.006 | 2 |
| Gamification effects on motivation | Sailer & Homner | 2017 | Comput. Hum. Behav. | 10.1016/j.chb.2017.09.030 | 2 |

Authoritative venues registered:
Proceedings of CHI PLAY (ACM); IEEE Transactions on Games; Entertainment
Computing (Elsevier); Computers & Operations Research (flow/scheduling);
Simulation & Gaming (SAGE); Journal of Simulation.

---

## 3. State-of-the-Art Methods & Tools

State of the art: automated ratio solvers (FactorioLab, Kirk McDonald),
blueprint optimization, ML bottleneck detection from game telemetry, modular
scaling patterns, throughput simulation, beacon/module optimization.
Crawl targets: CHI PLAY, IEEE Trans. Games, Entertain. Comput.,
Comput. Oper. Res., J. Simulation.

---

## 4. Authoritative Data Sources

### 4.1 Domain authoritative sources
- Game wikis (Factorio: wiki.factorio.com; Satisfactory: satisfactory.wiki.gg;
  Dyson Sphere Program: dsp-wiki.com)
- Community calculators (FactorioLab, Kirk McDonald, Satisfactory Calculator)
- Throughput/balancer references
- Production-chain math references
- Blueprint libraries (factorioprints.com)
- Mod/tool docs

### 4.2 Academic & research sources
- Proceedings of CHI PLAY (ACM)
- IEEE Transactions on Games
- Entertainment Computing (Elsevier)
- Computers & Operations Research (flow/scheduling)
- Simulation & Gaming (SAGE)
- Journal of Simulation

---

## 5. Analytical Frameworks

Knowledge categories covered: production chains & recipe graphs; throughput &
bottleneck analysis (Little's Law); belt/logistics balancing; power & pollution
tradeoffs; spatial layout & modular blueprints; scaling & ratio math.

Cross-reference the sub-skill workflows in `skills/*.md` for the domain methods
applied at each step. The fixed bookends (requirements -> evidence -> knowledge
-> synthesis -> quality gate) are mandatory; the core analysis sub-skill
implements the domain-specific methods, backed by the `automation_grid` engine.

---

## 6. Self-Update Protocol

- **Crawl pipeline:** `tools/knowledge_updater.py` (imports `automation_grid`)
- **Schedule:** weekly academic (Mondays 08:00) + daily news (07:00);
  documented in `CLAUDE.md` and `README.md`.
- **Sources:** ArXiv (cs.AI, cs.CE, cs.RO), Semantic Scholar, RSS feeds
  (Factorio forum, r/factorio, r/SatisfactoryGame, r/DysonSphereProgram).
- **Dedup:** SHA256 of DOI/URL (case/whitespace-insensitive).
- **Scoring:** composite 0-10 = recency(0.4) + keyword_relevance(0.4)
  + citation_count(0.2).
- **Gap-fill:** sub-knowledge-updater flags missing values as crawl queries.
- **Append rule:** new entries appended under Section 7 with date stamp +
  relevance score + Tier label.

---

## 7. Knowledge Update Log

_(Appended automatically by the crawl pipeline. Baseline seeded with the
references in Section 2. Run `python tools/knowledge_updater.py` to populate.)_
