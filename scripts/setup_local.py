"""setup_local.py - local setup routine for automation-grid-game-design.

Idempotent local setup: ensures required directories exist, validates the
config, the skill definitions, the engine import, and prints a readiness
checklist. Safe to run repeatedly; does not mutate source files.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ensure_dirs() -> list[str]:
    created: list[str] = []
    for d in ("logs", "assets", "references", "config", "scripts", "skills/definitions"):
        p = ROOT / d
        p.mkdir(parents=True, exist_ok=True)
    return created


def main() -> int:
    print("automation-grid-game-design local setup")
    print("=" * 48)
    ensure_dirs()
    print("[ok] required directories present")

    try:
        from config import load_settings
        s = load_settings()
        print(f"[ok] config loaded: provider={s.llm.provider} budget={s.token_budget}")
    except Exception as ex:  # noqa: BLE001
        print(f"[FAIL] config load: {ex}")
        return 1

    try:
        import automation_grid as ag  # noqa: F401
        print(f"[ok] automation_grid import: v{ag.__version__}, "
              f"{len(list(ag.DEFAULT_REGISTRY.items()))} recipes")
    except Exception as ex:  # noqa: BLE001
        print(f"[FAIL] automation_grid import: {ex}")
        return 1

    try:
        import agent  # noqa: F401
        print(f"[ok] agent framework import: v{agent.__version__}")
    except Exception as ex:  # noqa: BLE001
        print(f"[FAIL] agent import: {ex}")
        return 1

    # validate skill definitions
    try:
        from agent import load_skill_definitions
        reg = load_skill_definitions(ROOT / "skills" / "definitions")
        print(f"[ok] skill definitions: {len(reg.names())} skills -> {reg.names()}")
    except Exception as ex:  # noqa: BLE001
        print(f"[FAIL] skill definitions: {ex}")
        return 1

    # smoke run
    try:
        from agent import HarnessRunner
        res = HarnessRunner().run("Optimize my Factorio electronic-circuit line for 10/s")
        verdict = res.state.verdict.get("verdict", "n/a")
        gates = sum(1 for g in res.state.gate_results if g.get("passed"))
        print(f"[ok] smoke run: verdict={verdict} gates={gates}/{len(res.state.gate_results)}")
    except Exception as ex:  # noqa: BLE001
        print(f"[FAIL] smoke run: {ex}")
        return 1

    print("=" * 48)
    print("setup complete; ready for development / production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())