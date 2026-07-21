"""automation_grid.recipes - seeded recipe databases for factory/automation games.

Recipes are real-world values (approximated to published wiki figures at base
machine speed). Quantities are per-craft; craft_time is seconds at base speed.
These seed the engine's RecipeRegistry so the skill can produce concrete
worked examples and tests without a live data fetch.
"""
from __future__ import annotations

from .engine import Recipe, RecipeRegistry


def factorio_recipes() -> list[Recipe]:
    return [
        Recipe(
            name="iron-plate", game="factorio",
            inputs={"iron-ore": 1.0}, outputs={"iron-plate": 1.0},
            craft_time=3.2, machine="electric-furnace", category="smelting",
        ),
        Recipe(
            name="copper-plate", game="factorio",
            inputs={"copper-ore": 1.0}, outputs={"copper-plate": 1.0},
            craft_time=3.2, machine="electric-furnace", category="smelting",
        ),
        Recipe(
            name="steel-plate", game="factorio",
            inputs={"iron-plate": 5.0}, outputs={"steel-plate": 1.0},
            craft_time=16.0, machine="electric-furnace", category="smelting",
        ),
        Recipe(
            name="copper-cable", game="factorio",
            inputs={"copper-plate": 1.0}, outputs={"copper-cable": 2.0},
            craft_time=0.5, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="iron-gear-wheel", game="factorio",
            inputs={"iron-plate": 2.0}, outputs={"iron-gear-wheel": 1.0},
            craft_time=0.5, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="electronic-circuit", game="factorio",
            inputs={"copper-cable": 3.0, "iron-plate": 1.0},
            outputs={"electronic-circuit": 1.0},
            craft_time=0.5, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="advanced-circuit", game="factorio",
            inputs={"electronic-circuit": 2.0, "copper-cable": 4.0, "plastic-bar": 1.0},
            outputs={"advanced-circuit": 1.0},
            craft_time=6.0, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="processing-unit", game="factorio",
            inputs={"advanced-circuit": 2.0, "electronic-circuit": 20.0, "sulfuric-acid": 5.0},
            outputs={"processing-unit": 1.0},
            craft_time=10.0, machine="assembling-machine-3", category="crafting",
        ),
        Recipe(
            name="engine-unit", game="factorio",
            inputs={"steel-plate": 1.0, "iron-gear-wheel": 1.0},
            outputs={"engine-unit": 1.0},
            craft_time=3.0, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="electric-motor", game="factorio",
            inputs={"engine-unit": 1.0, "electronic-circuit": 2.0, "copper-cable": 6.0},
            outputs={"electric-motor": 1.0},
            craft_time=6.0, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="science-pack-1", game="factorio",
            inputs={"copper-plate": 1.0, "iron-gear-wheel": 1.0},
            outputs={"automation-science-pack": 1.0},
            craft_time=5.0, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="science-pack-2", game="factorio",
            inputs={"transport-belt": 1.0, "inserter": 1.0},
            outputs={"logistic-science-pack": 1.0},
            craft_time=6.0, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="transport-belt", game="factorio",
            inputs={"iron-plate": 1.0, "iron-gear-wheel": 1.0},
            outputs={"transport-belt": 2.0},
            craft_time=0.5, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="inserter", game="factorio",
            inputs={"electronic-circuit": 1.0, "iron-gear-wheel": 1.0, "iron-plate": 1.0},
            outputs={"inserter": 1.0},
            craft_time=0.5, machine="assembling-machine-2", category="crafting",
        ),
        Recipe(
            name="plastic-bar", game="factorio",
            inputs={"coal": 1.0, "petroleum-gas": 20.0},
            outputs={"plastic-bar": 2.0},
            craft_time=1.0, machine="chemical-plant", category="chemistry",
        ),
        Recipe(
            name="sulfuric-acid", game="factorio",
            inputs={"water": 100.0, "sulfur": 5.0},
            outputs={"sulfuric-acid": 50.0},
            craft_time=1.0, machine="chemical-plant", category="chemistry",
        ),
    ]


def satisfactory_recipes() -> list[Recipe]:
    # Satisfactory craft_time is per-craft in seconds; outputs per craft.
    return [
        Recipe(
            name="iron-ingot", game="satisfactory",
            inputs={"iron-ore": 1.0}, outputs={"iron-ingot": 1.0},
            craft_time=2.0, machine="smelter", category="smelting",
        ),
        Recipe(
            name="copper-ingot", game="satisfactory",
            inputs={"copper-ore": 1.0}, outputs={"copper-ingot": 1.0},
            craft_time=2.0, machine="smelter", category="smelting",
        ),
        Recipe(
            name="steel-ingot", game="satisfactory",
            inputs={"iron-ingot": 3.0, "coal": 3.0}, outputs={"steel-ingot": 3.0},
            craft_time=4.0, machine="foundry", category="smelting",
        ),
        Recipe(
            name="iron-plate", game="satisfactory",
            inputs={"iron-ingot": 3.0}, outputs={"iron-plate": 2.0},
            craft_time=6.0, machine="constructor", category="constructing",
        ),
        Recipe(
            name="iron-rod", game="satisfactory",
            inputs={"iron-ingot": 1.0}, outputs={"iron-rod": 1.0},
            craft_time=4.0, machine="constructor", category="constructing",
        ),
        Recipe(
            name="screw", game="satisfactory",
            inputs={"iron-rod": 1.0}, outputs={"screw": 4.0},
            craft_time=6.0, machine="constructor", category="constructing",
        ),
        Recipe(
            name="reinforced-iron-plate", game="satisfactory",
            inputs={"iron-plate": 6.0, "screw": 12.0}, outputs={"reinforced-iron-plate": 1.0},
            craft_time=12.0, machine="assembler", category="assembling",
        ),
        Recipe(
            name="rotor", game="satisfactory",
            inputs={"iron-rod": 5.0, "screw": 25.0}, outputs={"rotor": 1.0},
            craft_time=15.0, machine="assembler", category="assembling",
        ),
        Recipe(
            name="modular-frame", game="satisfactory",
            inputs={"reinforced-iron-plate": 2.0, "iron-rod": 1.0},
            outputs={"modular-frame": 2.0},
            craft_time=60.0, machine="assembler", category="assembling",
        ),
        Recipe(
            name="smart-plating", game="satisfactory",
            inputs={"reinforced-iron-plate": 1.0, "rotor": 1.0},
            outputs={"smart-plating": 1.0},
            craft_time=30.0, machine="manufacturer", category="manufacturing",
        ),
        Recipe(
            name="copper-wire", game="satisfactory",
            inputs={"copper-ingot": 1.0}, outputs={"copper-wire": 2.0},
            craft_time=4.0, machine="constructor", category="constructing",
        ),
        Recipe(
            name="cable", game="satisfactory",
            inputs={"copper-wire": 2.0}, outputs={"cable": 1.0},
            craft_time=2.0, machine="constructor", category="constructing",
        ),
    ]


def build_registry() -> RecipeRegistry:
    reg = RecipeRegistry()
    for r in factorio_recipes() + satisfactory_recipes():
        reg.add(r)
    return reg


DEFAULT_REGISTRY = build_registry()
