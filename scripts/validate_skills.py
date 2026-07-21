"""validate_skills.py - validate skills/definitions/*.json against the contract.

Checks every skill definition for: required fields, valid JSON Schema shape,
referenced prompt-template files exist, referenced tools exist in the default
tool registry, referenced gates are declared, and handler binding succeeds.
Exit 0 = all valid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import SkillRegistry, build_default_tools, load_skill_definitions  # noqa: E402
from agent.registry import REQUIRED_FIELDS  # noqa: E402

DEFINITIONS = ROOT / "skills" / "definitions"
PROMPT_DIR = ROOT / "references" / "prompt_templates"

VALID_GATES = {"U1", "U2", "U3", "U4", "U5", "U6", "G1", "G2", "G3", "G4"}


def main() -> int:
    passed = 0
    failed = 0
    failures: list[str] = []

    def ok(label: str) -> None:
        nonlocal passed
        passed += 1

    def fail(label: str) -> None:
        nonlocal failed
        failed += 1
        failures.append(label)

    files = sorted(DEFINITIONS.glob("*.json"))
    if not files:
        fail("no skill definition files found")
    tools = build_default_tools()
    tool_names = set(tools.names())

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data.get("name", path.stem)
        for f in REQUIRED_FIELDS:
            if f not in data:
                fail(f"{name}: missing field {f}")
            else:
                ok(f"{name}: field {f}")
        # schemas have top-level type
        for sk in ("inputs_schema", "outputs_schema"):
            if isinstance(data.get(sk), dict) and "type" in data[sk]:
                ok(f"{name}: {sk} has type")
            else:
                fail(f"{name}: {sk} missing top-level type")
        # prompt template file exists
        pt = data.get("prompt_template", "")
        pt_path = ROOT / pt
        if pt and pt_path.exists():
            ok(f"{name}: prompt_template exists")
        else:
            fail(f"{name}: prompt_template missing {pt}")
        # tools exist
        for t in data.get("tools", []):
            if t in tool_names:
                ok(f"{name}: tool {t} exists")
            else:
                fail(f"{name}: unknown tool {t}")
        # gates declared
        for g in data.get("gates", []):
            if g in VALID_GATES:
                ok(f"{name}: gate {g} valid")
            else:
                fail(f"{name}: unknown gate {g}")

    # registry loads + binds handlers
    try:
        reg = load_skill_definitions(DEFINITIONS)
        issues = reg.validate_definitions()
        if issues:
            for i in issues:
                fail(f"registry: {i}")
        else:
            ok("registry: loads + validates")
        if len(reg.names()) >= 6:
            ok(f"registry: {len(reg.names())} skills registered")
        else:
            fail(f"registry: only {len(reg.names())} skills (expected >=6)")
    except Exception as ex:  # noqa: BLE001
        fail(f"registry load failed: {ex}")

    total = passed + failed
    print(f"[validate_skills] {passed}/{total} checks passed")
    for f in failures:
        print("  - FAIL " + f)
    if failed:
        return 1
    print("[OK] all skill definitions valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())