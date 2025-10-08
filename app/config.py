"""
Configuration management for the service.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(env_prefix="LARS_", case_sensitive=False)

    auth_token: Optional[str] = None
    sandbox_deny_net: bool = True
    sandbox_llm_allowed_hosts: List[str] = ["api.openai.com", "api.anthropic.com"]
    default_provider: str = "openai"
    max_exec_ms: int = 8000
    max_result_bytes: int = 32768
    max_stdout_bytes: int = 4096

    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()  # type: ignore[call-arg]
