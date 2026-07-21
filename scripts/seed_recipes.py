"""seed_recipes.py - export / extend the seeded recipe database.

Exports the in-memory recipe database (Factorio + Satisfactory) to
``assets/recipes.json`` so it is machine-readable and diff-friendly, and can
optionally merge extra recipes from a user-provided JSON file into a fresh
registry (validating each against the engine before printing a summary).

Usage:
    python scripts/seed_recipes.py                      # export seeded DB
    python scripts/seed_recipes.py --import extra.json  # validate + merge extras
    python scripts/seed_recipes.py --game factorio      # filter export by game
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_grid import DEFAULT_REGISTRY, build_registry  # noqa: E402
from automation_grid.engine import Recipe, RecipeRegistry  # noqa: E402

EXPORT_PATH = ROOT / "assets" / "recipes.json"


def _recipe_to_dict(r: Recipe) -> dict:
    return {
        "name": r.name, "game": r.game,
        "inputs": r.inputs, "outputs": r.outputs,
        "craft_time": r.craft_time, "machine": r.machine, "category": r.category,
    }


def export_registry(game: str | None = None) -> dict:
    out: dict[str, list[dict]] = {}
    for r in DEFAULT_REGISTRY.items():
        if game and r.game != game:
            continue
        out.setdefault(r.game, []).append(_recipe_to_dict(r))
    return out


def import_extras(path: Path) -> dict:
    """Validate + merge extra recipes from a JSON file; return a summary."""
    data = json.loads(path.read_text(encoding="utf-8"))
    reg = build_registry()
    added: list[str] = []
    rejected: list[str] = []
    recipes = data if isinstance(data, list) else data.get("recipes", [])
    for entry in recipes:
        try:
            r = Recipe(
                name=entry["name"], game=entry["game"],
                inputs=entry.get("inputs", {}), outputs=entry.get("outputs", {}),
                craft_time=float(entry["craft_time"]),
                machine=entry["machine"], category=entry.get("category", "crafting"),
            )
            r.base_rate(next(iter(r.outputs)))  # validate craft_time > 0
            reg.add(r)
            added.append(f"{r.game}:{r.name}")
        except Exception as ex:  # noqa: BLE001
            rejected.append(f"{entry.get('name','?')}: {ex}")
    return {"added": added, "rejected": rejected, "total": len(reg.items())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export / extend the seeded recipe database.")
    ap.add_argument("--import", dest="import_path", help="merge extra recipes from a JSON file")
    ap.add_argument("--game", default=None, help="filter export by game")
    ap.add_argument("--out", default=str(EXPORT_PATH), help="export output path")
    args = ap.parse_args(argv)

    if args.import_path:
        summary = import_extras(Path(args.import_path))
        print(json.dumps(summary, indent=2))
        return 0 if not summary["rejected"] else 1

    exported = export_registry(args.game)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(exported, indent=2), encoding="utf-8")
    total = sum(len(v) for v in exported.values())
    print(f"exported {total} recipes across {len(exported)} games -> {out_path}")
    for g, items in exported.items():
        print(f"  {g}: {len(items)} recipes")
    return 0


if __name__ == "__main__":
    sys.exit(main())