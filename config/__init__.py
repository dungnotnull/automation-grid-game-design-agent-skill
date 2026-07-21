"""config - type-safe configuration management for automation-grid-game-design.

Public API:
    Settings, LLMSettings, FeatureFlags, KnowledgeCrawlSettings
    load_settings(path=None) -> Settings
    settings  (eager singleton, validated at import)
"""
from .settings import (
    Settings,
    LLMSettings,
    FeatureFlags,
    KnowledgeCrawlSettings,
    load_settings,
    settings,
)

__all__ = [
    "Settings", "LLMSettings", "FeatureFlags", "KnowledgeCrawlSettings",
    "load_settings", "settings",
]