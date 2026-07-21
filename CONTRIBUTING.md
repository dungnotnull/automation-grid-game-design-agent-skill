# Contributing to automation-grid-game-design

Thank you for your interest in improving this skill! This project is a
production-grade, evidence-backed analysis harness for Automation-Game Grid
Logistics & Throughput Optimization (Factorio, Satisfactory, Dyson Sphere
Program).

## How to contribute

1. **Fork & branch.** Create a descriptively named branch from `main`.
2. **Discuss first.** For non-trivial changes, open an issue describing the
   change before writing code.
3. **Write real code.** No stubs, no commented-out code, no dummy returns.
   Every function must be complete and tested.
4. **Keep units consistent.** The engine uses **items per second** everywhere.
   Recipe `craft_time` is seconds at base machine speed; belt/machine tables
   are items/sec. Do not mix items/min into the engine.
5. **Cite sources.** Any new recipe/machine/belt figure must reference the wiki
   or calculator it came from. Add the source to `SECOND-KNOWLEDGE-BRAIN.md`.
6. **Add tests.** New engine logic must be covered in `tests/test_automation_engine.py`.
   New crawl logic in `tests/test_crawl_pipeline.py`.
7. **Run the full suite before pushing:**

   ```bash
   python -m pytest tests/ tools/test_knowledge_updater.py -q
   python tools/validate_project.py
   python tools/run_test_scenarios.py
   ```

   All three must exit 0.

## Code style

- Python 3.9+ compatible; use `from __future__ import annotations`.
- Type hints on all public functions.
- `dataclass` for structured records; `Enum` for closed value sets.
- Structured logging via `automation_grid.logging_utils.get_logger` (not `print`
  in library code).
- UTF-8, no BOM, LF line endings.

## Knowledge base updates

- Append-only: new crawled entries go under `## 7. Knowledge Update Log`.
- Dedup by SHA256 of DOI/URL (case/whitespace-insensitive).
- Never edit seeded Section 2 citations except to correct a factual error (note
  the correction in the entry).

## Pull request checklist

- [ ] Tests pass (`pytest`, `validate_project.py`, `run_test_scenarios.py`).
- [ ] No fabricated recipe/belt/machine values; sources cited.
- [ ] Documentation updated (README / CLAUDE / SECOND-KNOWLEDGE-BRAIN as needed).
- [ ] `PROJECT-DEVELOPMENT-PHASE-TRACKING.md` updated if scope changes.

## Licensing

By contributing you agree your contributions are licensed under the project's
MIT License.
