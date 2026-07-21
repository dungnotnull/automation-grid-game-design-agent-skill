"""config.settings - type-safe configuration management.

Loads ``config/default.json`` and overrides values from environment variables
(prefixed ``AUTOMATION_GRID_``). All settings are validated at load time and
exposed as a frozen dataclass, so the rest of the system gets a single,
type-checked configuration object.

Environment variables:
    AUTOMATION_GRID_LOG_LEVEL            -> log_level (DEBUG|INFO|WARNING|ERROR)
    AUTOMATION_GRID_LANGUAGE             -> language (en|vi)
    AUTOMATION_GRID_TOKEN_BUDGET         -> token_budget (int)
    AUTOMATION_GRID_RESERVE_OUTPUT       -> reserve_output_tokens (int)
    AUTOMATION_GRID_API_KEY              -> llm.api_key (enables HTTP provider)
    AUTOMATION_GRID_API_BASE             -> llm.api_base
    AUTOMATION_GRID_MODEL                -> llm.model
    AUTOMATION_GRID_LLM_TEMPERATURE      -> llm.temperature (float)
    AUTOMATION_GRID_LLM_MAX_TOKENS       -> llm.max_tokens (int)
    AUTOMATION_GRID_LLM_TIMEOUT          -> llm.timeout_seconds (float)
    AUTOMATION_GRID_PROVIDER             -> llm.provider (deterministic|openai)
    AUTOMATION_GRID_OFFLINE              -> knowledge_crawl.offline (bool)
    AUTOMATION_GRID_STATE_SNAPSHOTS      -> feature_flags.enable_state_snapshots (bool)
    AUTOMATION_GRID_STRICT_GATES         -> feature_flags.strict_gates (bool)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = Path(__file__).resolve().parent
ROOT = CONFIG_DIR.parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.json"

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
_VALID_LANGUAGES = {"en", "vi"}
_VALID_PROVIDERS = {"deterministic", "openai"}


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v


def _env_bool(name: str, default: bool) -> bool:
    v = _env(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    v = _env(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError as ex:
        raise ValueError(f"{name} must be an integer, got {v!r}") from ex


def _env_float(name: str, default: float) -> float:
    v = _env(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError as ex:
        raise ValueError(f"{name} must be a float, got {v!r}") from ex


@dataclass(frozen=True)
class LLMSettings:
    provider: str = "deterministic"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: float = 60.0
    max_retries: int = 3
    base_retry_delay_seconds: float = 0.5

    def __post_init__(self) -> None:
        if self.provider not in _VALID_PROVIDERS:
            raise ValueError(f"provider must be in {_VALID_PROVIDERS}, got {self.provider!r}")
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be in [0, 2]")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")


@dataclass(frozen=True)
class FeatureFlags:
    use_deterministic_provider: bool = True
    enable_state_snapshots: bool = False
    enable_knowledge_crawl: bool = True
    strict_gates: bool = True
    emit_events: bool = True


@dataclass(frozen=True)
class KnowledgeCrawlSettings:
    schedule_academic: str = "0 8 * * 1"
    schedule_news: str = "0 7 * * *"
    max_new_entries_per_run: int = 20
    offline: bool = False


@dataclass(frozen=True)
class Settings:
    version: str = "2.0.0"
    domain: str = "Automation-Game Grid Logistics & Throughput Optimization"
    language: str = "en"
    log_level: str = "INFO"
    token_budget: int = 8192
    reserve_output_tokens: int = 1024
    context_trim_droppable_only: bool = True
    llm: LLMSettings = field(default_factory=LLMSettings)
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    knowledge_crawl: KnowledgeCrawlSettings = field(default_factory=KnowledgeCrawlSettings)

    def __post_init__(self) -> None:
        if self.log_level not in _VALID_LOG_LEVELS:
            raise ValueError(f"log_level must be in {_VALID_LOG_LEVELS}, got {self.log_level!r}")
        if self.language not in _VALID_LANGUAGES:
            raise ValueError(f"language must be in {_VALID_LANGUAGES}, got {self.language!r}")
        if self.token_budget <= 0:
            raise ValueError("token_budget must be positive")
        if not (0 <= self.reserve_output_tokens < self.token_budget):
            raise ValueError("reserve_output_tokens must be in [0, token_budget)")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_default(path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_settings(path: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> Settings:
    """Load settings from JSON then override with environment variables."""
    data = _load_default(path or DEFAULT_CONFIG_PATH)
    llm_data = dict(data.get("llm", {}))
    flags_data = dict(data.get("feature_flags", {}))
    crawl_data = dict(data.get("knowledge_crawl", {}))

    # Environment overrides
    log_level = _env("AUTOMATION_GRID_LOG_LEVEL", data.get("log_level", "INFO"))
    language = _env("AUTOMATION_GRID_LANGUAGE", data.get("language", "en"))
    token_budget = _env_int("AUTOMATION_GRID_TOKEN_BUDGET", int(data.get("token_budget", 8192)))
    reserve = _env_int("AUTOMATION_GRID_RESERVE_OUTPUT", int(data.get("reserve_output_tokens", 1024)))

    provider = _env("AUTOMATION_GRID_PROVIDER", llm_data.get("provider", "deterministic"))
    api_key = _env("AUTOMATION_GRID_API_KEY", "") or ""
    if api_key and provider == "deterministic":
        provider = "openai"
    llm = LLMSettings(
        provider=provider,
        model=_env("AUTOMATION_GRID_MODEL", llm_data.get("model", "gpt-4o-mini")),
        api_key=api_key,
        api_base=_env("AUTOMATION_GRID_API_BASE", llm_data.get("api_base", "https://api.openai.com/v1")),
        temperature=_env_float("AUTOMATION_GRID_LLM_TEMPERATURE", float(llm_data.get("temperature", 0.2))),
        max_tokens=_env_int("AUTOMATION_GRID_LLM_MAX_TOKENS", int(llm_data.get("max_tokens", 1024))),
        timeout_seconds=_env_float("AUTOMATION_GRID_LLM_TIMEOUT", float(llm_data.get("timeout_seconds", 60.0))),
        max_retries=int(llm_data.get("max_retries", 3)),
        base_retry_delay_seconds=float(llm_data.get("base_retry_delay_seconds", 0.5)),
    )

    flags = FeatureFlags(
        use_deterministic_provider=(provider == "deterministic"),
        enable_state_snapshots=_env_bool("AUTOMATION_GRID_STATE_SNAPSHOTS",
                                         bool(flags_data.get("enable_state_snapshots", False))),
        enable_knowledge_crawl=bool(flags_data.get("enable_knowledge_crawl", True)),
        strict_gates=_env_bool("AUTOMATION_GRID_STRICT_GATES", bool(flags_data.get("strict_gates", True))),
        emit_events=bool(flags_data.get("emit_events", True)),
    )

    crawl = KnowledgeCrawlSettings(
        schedule_academic=crawl_data.get("schedule_academic", "0 8 * * 1"),
        schedule_news=crawl_data.get("schedule_news", "0 7 * * *"),
        max_new_entries_per_run=int(crawl_data.get("max_new_entries_per_run", 20)),
        offline=_env_bool("AUTOMATION_GRID_OFFLINE", bool(crawl_data.get("offline", False))),
    )

    return Settings(
        version=data.get("version", "2.0.0"),
        domain=data.get("domain", "Automation-Game Grid Logistics & Throughput Optimization"),
        language=language,
        log_level=log_level,
        token_budget=token_budget,
        reserve_output_tokens=reserve,
        context_trim_droppable_only=bool(data.get("context_trim_droppable_only", True)),
        llm=llm,
        feature_flags=flags,
        knowledge_crawl=crawl,
    )


# Eager singleton (validated at import time so misconfiguration fails fast).
settings = load_settings()