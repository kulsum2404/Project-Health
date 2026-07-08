"""
Application configuration — reads from .env via pydantic-settings.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Project Health Agent backend."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────
    database_url: str = "sqlite:///./project_health.db"

    # ── LLM Provider ──────────────────────────────────────────────────
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_max_tokens: int = 1024

    # ── Scheduler ─────────────────────────────────────────────────────
    scheduler_enabled: bool = False
    scheduler_cron: str = "0 9 * * 1"  # every Monday at 09:00

    # ── File storage ──────────────────────────────────────────────────
    upload_dir: str = "uploads"
    reports_dir: str = "reports"

    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Project Health Agent"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def reports_path(self) -> Path:
        p = Path(self.reports_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
