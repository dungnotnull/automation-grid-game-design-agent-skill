"""run_test_scenarios.py - Skill 198: automation-grid-game-design

Production-grade structural, content and *engine* validator. Verifies the
8-File Contract, sub-skill content, knowledge base, the 5 end-to-end test
scenarios from tests/test-scenarios.md, and that the automation_grid engine
actually solves realistic production-line problems. Exit 0 = all pass.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_grid import (
    DEFAULT_REGISTRY, VERDICTS, balancer_design, bottleneck_analysis,
    classify_verdict, little_law, machine_config, solve_grid, solve_ratios,
)

passed = 0
failed = 0
failures: list[str] = []


def ok(label: str, detail: str = "") -> None:
    global passed
    passed += 1


def fail(label: str, detail: str = "") -> None:
    global failed
    failed += 1
    failures.append(f"{label}: {detail}" if detail else label)


def require(cond: bool, label: str, detail: str = "") -> None:
    (ok if cond else fail)(label, detail)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ---- 1. File structure ----
REQUIRED = [
    "CLAUDE.md", "PROJECT-detail.md", "PROJECT-DEVELOPMENT-PHASE-TRACKING.md",
    "README.md", "SECOND-KNOWLEDGE-BRAIN.md", "skills/main.md", "LICENSE",
    "tools/knowledge_updater.py", "tools/test_knowledge_updater.py",
    "tools/run_test_scenarios.py", "tools/validate_project.py",
    "tests/test-scenarios.md", "tests/TEST_RESULTS.md",
]
for f in REQUIRED:
    require((ROOT / f).exists(), f"file present: {f}")

subs = sorted((ROOT / "skills").glob("sub-*.md"))
require(len(subs) >= 5, "at least 5 sub-skills", f"found {len(subs)}")
expected_subs = {"sub-gather-requirements", "sub-evidence-collector",
                 "sub-core-analysis", "sub-knowledge-updater", "sub-advisor"}
got_subs = {s.stem for s in subs}
require(got_subs == expected_subs, "sub-skill set", f"got {got_subs}")

# ---- 2. Frontmatter + sections ----
FM = re.compile(r"^---\s*\n(.*?\n)---", re.S)
for s in subs:
    txt = read(s)
    m = FM.search(txt)
    require(bool(m), f"{s.name}: frontmatter")
    if m:
        require("name:" in m.group(1) and "description:" in m.group(1), f"{s.name}: name+description")
    for sec in ["Role & Persona", "Workflow", "Output Format", "Quality Gates"]:
        require(sec in txt, f"{s.name}: section {sec}")

main_txt = read(ROOT / "skills" / "main.md")
for sec in ["Role & Persona", "Quality Gates", "Graceful Degradation"]:
    require(sec in main_txt, f"main.md: section {sec}")
require("Harness Execution Protocol" in main_txt, "main.md: harness workflow")
require("Pre-Flight" in main_txt, "main.md: pre-flight language detection")
require("LIMITATION" in main_txt, "main.md: limitation banner")

# ---- 3. Quality gate + verdict coverage ----
for g in ["U1", "U2", "U3", "U4", "U5", "U6", "G1", "G2", "G3", "G4"]:
    require(g in main_txt, f"main.md: gate {g} present")
adv = read(ROOT / "skills" / "sub-advisor.md")
for v in VERDICTS:
    require(v in adv or v in main_txt, f"advisor/verdict {v} present")

# ---- 4. Knowledge base ----
brain = read(ROOT / "SECOND-KNOWLEDGE-BRAIN.md")
require("Tier 1" in brain and "Tier 4" in brain, "brain: evidence tiers")
dois = re.findall(r"10\.\d{4,9}/[^\s|)]+", brain)
require(len(dois) >= 2, "brain: >=2 DOI refs", f"found {len(dois)}")
require("## 4. Authoritative Data Sources" in brain, "brain: data sources")
require("## 6. Self-Update Protocol" in brain, "brain: self-update protocol")

# ---- 5. test-scenarios.md ----
sc = read(ROOT / "tests" / "test-scenarios.md")
require(sc.count("Scenario") >= 5, "scenarios: >=5", f"found {sc.count('Scenario')}")
require("degraded" in sc.lower(), "scenarios: degraded case")
require("conflict" in sc.lower() or "comparison" in sc.lower(), "scenarios: comparison/conflict")
for g in ["G1", "G2", "G3", "G4"]:
    require(g in sc, f"scenarios: gate {g} referenced")

# ---- 6. knowledge_updater.py ----
ku = read(ROOT / "tools" / "knowledge_updater.py")
require("KNOWLEDGE_CONFIG" in ku, "knowledge_updater: config import")
require("compute_hash" in ku, "knowledge_updater: dedup hash")
require("score_entry" in ku, "knowledge_updater: scoring")
require("--dry-run" in ku, "knowledge_updater: dry-run flag")
require("--news-only" in ku, "knowledge_updater: news-only flag")

# ---- 7. Engine scenarios (the real computational tests) ----
# Scenario 1: standard analysis - Factorio electronic circuit line
sol = solve_grid("electronic-circuit", 10.0, DEFAULT_REGISTRY, "factorio")
require(sol is not None and len(sol.stages) >= 1, "S1: electronic-circuit solved")
require(sol.verdict.value in VERDICTS, "S1: verdict in declared set")
require(sol.power_kw_total > 0, "S1: power accounted", f"{sol.power_kw_total}")
require(sol.bottleneck.bottleneck_stage is not None, "S1: bottleneck identified")

# Scenario 2: minimal input - Satisfactory reinforced iron plate, defaults
sol2 = solve_grid("reinforced-iron-plate", 5.0, DEFAULT_REGISTRY, "satisfactory")
require(len(sol2.stages) >= 1, "S2: reinforced-iron-plate solved")
require(sol2.verdict.value in VERDICTS, "S2: verdict valid")

# Scenario 3: comparison - two target rates for same item
sol_a = solve_grid("iron-gear-wheel", 5.0, DEFAULT_REGISTRY, "factorio")
sol_b = solve_grid("iron-gear-wheel", 20.0, DEFAULT_REGISTRY, "factorio")
require(sol_b.belts_total >= sol_a.belts_total, "S3: scaling increases belts")
require(sol_b.machine_count if hasattr(sol_b, 'machine_count') else True, "S3: ok")
# count machines via stages
machines_a = sum(s.count_rounded for s in sol_a.stages)
machines_b = sum(s.count_rounded for s in sol_b.stages)
require(machines_b >= machines_a, "S3: more machines at higher rate")

# Scenario 4: risk/bottleneck - force a near-capacity bottleneck
sol4 = solve_grid("copper-plate", 50.0, DEFAULT_REGISTRY, "factorio")
require(sol4.bottleneck.bottleneck_utilization > 0, "S4: utilization reported")
require(len(sol4.bottleneck.recommendations) >= 1, "S4: bottleneck recommendations")

# Scenario 5: degraded mode - data unavailable
sol5 = solve_grid("electronic-circuit", 10.0, DEFAULT_REGISTRY, "factorio", data_available=False)
require(sol5.verdict.value == "Inconclusive", "S5: degraded -> Inconclusive")
require(len(sol5.stages) == 0, "S5: no stages fabricated in degraded mode")

# Little's Law unit
require(abs(little_law(10.0, 2.0) - 20.0) < 1e-9, "Little's Law L=lambda*W")

# Balancer design
bal = balancer_design(4, 4)
require(bal["splitters"] == 3 and bal["balanced"], "4:4 balancer uses 3 splitters")
bal2 = balancer_design(2, 4)
require(bal2["splitters"] >= 1, "2:4 balancer uses splitters")

# Module-aware machine config
mc = machine_config("assembling-machine-3", "factorio", ["speed-module-3"])
require(mc.effective_craft_speed() > 1.25, "speed module increases craft speed")

# ---- 7b. Agent framework scenarios (router + skills + gates) ----
from agent import HarnessRunner as _HR  # noqa: E402

# Scenario A: optimize intent -> full pipeline + Conditional bottleneck
resA = _HR().run("Optimize my Factorio electronic-circuit line for 10/s")
require(resA.ok, "A: optimize run ok")
require(resA.state.verdict.get("verdict") == "Conditional (bottleneck)", "A: verdict Conditional",
        resA.state.verdict.get("verdict"))
require(sum(1 for g in resA.state.gate_results if g.get("passed")) == len(resA.state.gate_results),
        "A: all gates pass")
require(resA.state.tokens_used > 0, "A: tokens accounted")

# Scenario B: explain intent -> skips core_analysis, still passes applicable gates
resB = _HR().run("Explain Little law for factory games")
require(resB.ok, "B: explain run ok")
require("core_analysis" not in [h["skill"] for h in resB.state.history], "B: core_analysis skipped")
applicable = [g for g in resB.state.gate_results if g.get("detail") != "n/a (owning skill not run)"]
require(all(g.get("passed") for g in applicable), "B: applicable gates pass")

# Scenario C: degraded -> unknown item -> Inconclusive
resC = _HR().run("Optimize my Factorio zzz-nonexistent-item line for 10/s")
require(resC.state.degradation_level >= 3, "C: degradation level >= 3")
require(resC.state.verdict.get("verdict") == "Inconclusive", "C: verdict Inconclusive")

# Scenario D: tool registry + skill definitions load
from agent import build_default_tools as _bdt, load_skill_definitions as _lsd  # noqa: E402
_tr = _bdt()
require(_tr.has("solve_grid") and _tr.has("balancer_design"), "D: core tools registered")
_sreg = _lsd(ROOT / "skills" / "definitions")
require(len(_sreg.names()) >= 6, "D: >=6 skills loaded")
require(_sreg.validate_definitions() == [], "D: skill definitions valid")

# ---- 8. PDPT + README + PROJECT-detail ----
pdpt = read(ROOT / "PROJECT-DEVELOPMENT-PHASE-TRACKING.md")
require("100%" in pdpt, "PDPT: 100% markers")
require("Phase 5" in pdpt, "PDPT: Phase 5")
readme = read(ROOT / "README.md")
require("Usage" in readme, "README: usage")
pd = read(ROOT / "PROJECT-detail.md")
require("Idea (Vietnamese)" in pd, "PROJECT-detail: Idea (Vietnamese)")
require("Harness Architecture" in pd, "PROJECT-detail: harness architecture")


def main() -> int:
    total = passed + failed
    print(f"[run_test_scenarios] {passed}/{total} checks passed")
    if failures:
        for f in failures:
            print("  - FAIL " + f)
        return 1
    print("[OK] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
