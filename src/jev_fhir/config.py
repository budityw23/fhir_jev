"""Application configuration loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for the Jev × FHIR service."""

    jev_api_key: str = "mock-key"
    jev_base_url: str = "https://api.typesafe.ai"
    mock_jev: bool = False
    quality_threshold_default: int = 70
    route_confidence_minimum: float = 0.5
    notifiable_confidence_minimum: float = 0.8
    notifiable_review_minimum: float = 0.5
    jev_model: str = "jev-latest"
    jev_timeout_s: float = 5.0
    jev_max_retries: int = 2
    jev_retry_budget_s: float = 12.0
    labels_dir: Path = PROJECT_ROOT / "benchmarks" / "dataset" / "labels"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for application dependency injection."""
    return Settings()
