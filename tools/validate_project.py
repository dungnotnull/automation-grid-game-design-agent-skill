"""validate_project.py - Skill 198: automation-grid-game-design

8-File Contract + production-grade project validator. Checks required files,
sub-skill structure, knowledge base integrity, package import, encoding, and
documentation consistency. Exit 0 = pass, non-zero = failures.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_grid import (
    BELT_THROUGHPUT, KNOWLEDGE_CONFIG, MACHINE_SPECS, MODULE_EFFECTS,
    QUALITY_GATES, VERDICTS, build_registry, valid_verdicts,
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


# ---- 1. 8-File Contract ----
REQUIRED_FILES = [
    "CLAUDE.md", "PROJECT-detail.md", "PROJECT-DEVELOPMENT-PHASE-TRACKING.md",
    "README.md", "SECOND-KNOWLEDGE-BRAIN.md", "skills/main.md", "LICENSE",
    "requirements.txt", "SKILL.md",
]
for f in REQUIRED_FILES:
    require((ROOT / f).exists(), f"required file present: {f}")

subs = sorted((ROOT / "skills").glob("sub-*.md"))
require(len(subs) >= 5, "at least 5 sub-skills", f"found {len(subs)}")
expected_subs = {
    "sub-gather-requirements", "sub-evidence-collector", "sub-core-analysis",
    "sub-knowledge-updater", "sub-advisor",
}
got_subs = {s.stem for s in subs}
require(got_subs == expected_subs, "sub-skill set exact", f"got {got_subs - expected_subs} / missing {expected_subs - got_subs}")

# ---- 2. Frontmatter + sections on sub-skills ----
FM = re.compile(r"^---\s*\n(.*?\n)---", re.S)
for s in subs:
    txt = read(s)
    m = FM.search(txt)
    require(bool(m), f"{s.name}: frontmatter")
    if m:
        require("name:" in m.group(1) and "description:" in m.group(1),
                f"{s.name}: name+description in frontmatter")
    for sec in ["Role & Persona", "Workflow", "Output Format", "Quality Gates"]:
        require(sec in txt, f"{s.name}: section '{sec}'")

main_txt = read(ROOT / "skills" / "main.md")
for sec in ["Role & Persona", "Quality Gates", "Graceful Degradation", "Harness Execution Protocol"]:
    require(sec in main_txt, f"main.md: section '{sec}'")
require("Pre-Flight" in main_txt, "main.md: pre-flight language detection")
require("LIMITATION" in main_txt, "main.md: limitation banner")

# ---- 3. Quality gate + verdict coverage ----
for g in QUALITY_GATES:
    require(g["id"] in main_txt, f"main.md: gate {g['id']} present")
adv = read(ROOT / "skills" / "sub-advisor.md")
for v in valid_verdicts():
    require(v in adv or v in main_txt, f"verdict present: {v}")

# ---- 4. Knowledge base integrity ----
brain = read(ROOT / "SECOND-KNOWLEDGE-BRAIN.md")
require("Tier 1" in brain and "Tier 4" in brain, "brain: evidence hierarchy tiers")
dois = re.findall(r"10\.\d{4,9}/[^\s|)]+", brain)
require(len(dois) >= 2, "brain: >=2 DOI-cited references", f"found {len(dois)}")
for sec in ["## 1. Core Concepts & Frameworks", "## 4. Authoritative Data Sources",
            "## 6. Self-Update Protocol", "## 7. Knowledge Update Log"]:
    require(sec in brain, f"brain: section '{sec}'")

# ---- 5. Package import + engine sanity ----
require(build_registry is not None, "package: registry builder exists")
try:
    reg = build_registry()
    sol_stages = reg.get("factorio", "electronic-circuit")
    require(sol_stages is not None, "registry: factorio electronic-circuit recipe")
except Exception as ex:
    fail("registry build", str(ex))
require("factorio" in BELT_THROUGHPUT and "satisfactory" in BELT_THROUGHPUT, "config: belt tables")
require("factorio" in MACHINE_SPECS and "satisfactory" in MACHINE_SPECS, "config: machine specs")
require(MODULE_EFFECTS.get("factorio", {}).get("speed-module-3") is not None, "config: module effects")
require(len(KNOWLEDGE_CONFIG["arxiv_categories"]) > 0, "config: arxiv categories non-empty")
require(len(KNOWLEDGE_CONFIG["rss_feeds"]) > 0, "config: rss feeds non-empty")

# ---- 5b. Agent framework + modular directories ----
require((ROOT / "agent" / "__init__.py").exists(), "agent package present")
require((ROOT / "config" / "settings.py").exists(), "config package present")
require((ROOT / "scripts" / "run_harness.py").exists(), "scripts/run_harness.py present")
require((ROOT / "scripts" / "validate_skills.py").exists(), "scripts/validate_skills.py present")
require((ROOT / "scripts" / "setup_local.py").exists(), "scripts/setup_local.py present")
require((ROOT / "scripts" / "seed_recipes.py").exists(), "scripts/seed_recipes.py present")
require((ROOT / "scripts" / "ingest_knowledge.py").exists(), "scripts/ingest_knowledge.py present")
require((ROOT / "references" / "domain_methods.md").exists(), "references/domain_methods.md present")
require((ROOT / "assets" / "README.md").exists(), "assets/README.md present")
defs = sorted((ROOT / "skills" / "definitions").glob("*.json"))
require(len(defs) >= 6, "skills/definitions: >=6 json files", f"found {len(defs)}")
templates = sorted((ROOT / "references" / "prompt_templates").glob("*.md"))
require(len(templates) >= 6, "references/prompt_templates: >=6 files", f"found {len(templates)}")
schemas = sorted((ROOT / "assets" / "schemas").glob("*.json"))
require(len(schemas) >= 5, "assets/schemas: >=5 json schemas", f"found {len(schemas)}")
try:
    import agent  # noqa: F401
    require(True, "agent package imports")
except Exception as ex:
    fail("agent import", str(ex))
try:
    from agent import HarnessRunner, load_skill_definitions
    reg = load_skill_definitions(ROOT / "skills" / "definitions")
    require(len(reg.names()) >= 6, "agent: >=6 skills registered", f"{reg.names()}")
    res = HarnessRunner().run("Optimize my Factorio electronic-circuit line for 10/s")
    require(res.ok, "agent: smoke run ok", res.state.verdict.get("verdict", ""))
    gates_ok = sum(1 for g in res.state.gate_results if g.get("passed"))
    require(gates_ok == len(res.state.gate_results), "agent: all gates pass",
            f"{gates_ok}/{len(res.state.gate_results)}")
except Exception as ex:
    fail("agent smoke run", str(ex))
try:
    from config import load_settings
    cfg = load_settings()
    require(cfg.token_budget > 0, "config: token_budget positive")
    require(cfg.llm.provider in ("deterministic", "openai"), "config: provider valid")
except Exception as ex:
    fail("config load", str(ex))

# ---- 6. Docs consistency ----
pdpt = read(ROOT / "PROJECT-DEVELOPMENT-PHASE-TRACKING.md")
require("100%" in pdpt, "PDPT: 100% markers")
readme = read(ROOT / "README.md")
require("Usage" in readme, "README: usage section")
pd = read(ROOT / "PROJECT-detail.md")
require("Harness Architecture" in pd, "PROJECT-detail: harness architecture")
require("Idea (Vietnamese)" in pd, "PROJECT-detail: Vietnamese idea")

# ---- report ----
def main() -> int:
    total = passed + failed
    print(f"[validate_project] {passed}/{total} checks passed")
    if failures:
        for f in failures:
            print("  - FAIL " + f)
        return 1
    print("[OK] 8-File Contract + production checks PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
