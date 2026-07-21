# config/

Dedicated, type-safe configuration management for the automation-grid-game-design
system. Handles environment variables, LLM parameters, and system-wide feature
flags.

## Files
- `default.json` - baseline configuration (version, language, log level, token
  budget, LLM block, feature flags, knowledge-crawl schedule).
- `settings.py` - frozen dataclass settings (`Settings`, `LLMSettings`,
  `FeatureFlags`, `KnowledgeCrawlSettings`) loaded from `default.json` and
  overridden by `AUTOMATION_GRID_*` environment variables. All values are
  validated at load time; an invalid value raises immediately (fail-fast).
- `__init__.py` - re-exports the public API and the eager `settings` singleton.

## Usage
```python
from config import load_settings, settings
s = load_settings()
print(s.token_budget, s.llm.provider, s.feature_flags.strict_gates)
```

## Environment variables
See the module docstring in `settings.py` for the full `AUTOMATION_GRID_*` list.
Setting `AUTOMATION_GRID_API_KEY` automatically switches the LLM provider from
`deterministic` to the OpenAI-compatible HTTP provider.