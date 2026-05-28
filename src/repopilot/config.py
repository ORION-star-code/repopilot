"""Application configuration with safe local defaults."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from repopilot.models import ExecutionMode, derive_execution_mode


class Settings(BaseSettings):
    """Central settings for CLI, API, and future workers.

    Environment variables use the ``REPOPILOT_`` prefix.
    """

    model_config = SettingsConfigDict(env_prefix="REPOPILOT_", env_file=".env", extra="ignore")

    app_name: str = "RepoPilot"
    environment: Literal["local", "dev", "test", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    sandbox_enabled: bool = False
    sandbox_network_enabled: bool = False
    github_writes_enabled: bool = False
    shell_execution_enabled: bool = False
    high_risk_actions_require_approval: bool = True
    max_repair_retries: int = Field(default=2, ge=0, le=10)
    default_test_command: list[str] = Field(
        default_factory=lambda: ["python", "-m", "pytest", "-q"]
    )

    @property
    def execution_mode(self) -> ExecutionMode:
        """Derive execution mode from sandbox and shell configuration."""
        return derive_execution_mode(self.sandbox_enabled, self.shell_execution_enabled)


@lru_cache
def get_settings() -> Settings:
    """Return process-wide settings."""
    return Settings()
