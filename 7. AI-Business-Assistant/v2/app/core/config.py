"""Configuration management using pydantic-settings.

Enforces production safety gates (TC-T5-09) and centralizes environment configuration.
"""

from datetime import date
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.errors import UnsafeDeploymentError


class Settings(BaseSettings):
    """Application settings with environment variable loading and validation."""

    # Deployment Environment
    app_env: str = "development"  # development | staging | production

    # Data Profile & Cutoff Date
    data_profile: str = "real"  # real | synth
    as_of_date: date = date(2026, 7, 31)

    # Database Connection URIs
    postgres_uri_ro: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/gml"
    postgres_uri_app: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/gml"
    postgres_uri_admin: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/gml"

    # LLM Settings
    llm_provider: str = "gemini"  # gemini | ollama | mock
    llm_model: str = "gemini-2.0-flash"
    llm_tier: str = "free"  # free | paid
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def check_production_safety(self) -> "Settings":
        """TC-T5-09: Block unsafe cloud LLM free-tier in production environments.

        Under company data privacy policies (C3/ADR-005), free-tier cloud LLMs
        may use prompt data for model training. Production requires either a paid
        cloud tier or a self-hosted local model (Ollama).
        """
        env_norm = self.app_env.strip().lower()
        provider_norm = self.llm_provider.strip().lower()
        tier_norm = self.llm_tier.strip().lower()

        if env_norm == "production" and provider_norm != "ollama" and tier_norm == "free":
            raise UnsafeDeploymentError(
                "TC-T5-09: Production deployment prohibits free-tier cloud LLM due to data privacy policies (C3/ADR-005). "
                "Use paid tier or local Ollama."
            )
        return self
