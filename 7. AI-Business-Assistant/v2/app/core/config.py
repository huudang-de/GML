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

    # Database Connection URIs - Real Profile
    postgres_uri_ro: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/gml"
    postgres_uri_app: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/gml"
    postgres_uri_admin: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/gml"

    # Database Connection URIs - Synthetic Profile
    postgres_uri_ro_synth: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/gml_synth"
    postgres_uri_app_synth: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/gml_synth"
    postgres_uri_admin_synth: str = "postgresql+psycopg2://dev:Inda1234@localhost:5432/gml_synth"

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

    @model_validator(mode="after")
    def check_profile_database_isolation(self) -> "Settings":
        """Review Focus #4: Block cross-contamination if real and synth URIs share the same database."""
        from sqlalchemy.engine import make_url

        def _get_db(uri: str) -> str:
            try:
                return (make_url(uri).database or "").strip().lower()
            except Exception:
                return ""

        ro_real_db = _get_db(self.postgres_uri_ro)
        ro_synth_db = _get_db(self.postgres_uri_ro_synth)
        if ro_real_db and ro_synth_db and ro_real_db == ro_synth_db:
            raise ValueError(
                f"Review Focus #4: postgres_uri_ro and postgres_uri_ro_synth point to the same database ('{ro_real_db}'). "
                "Real and synthetic profiles must use isolated databases to prevent cross-contamination."
            )

        admin_real_db = _get_db(self.postgres_uri_admin)
        admin_synth_db = _get_db(self.postgres_uri_admin_synth)
        if admin_real_db and admin_synth_db and admin_real_db == admin_synth_db:
            raise ValueError(
                f"Review Focus #4: postgres_uri_admin and postgres_uri_admin_synth point to the same database ('{admin_real_db}'). "
                "Real and synthetic profiles must use isolated databases to prevent cross-contamination."
            )

        app_real_db = _get_db(self.postgres_uri_app)
        app_synth_db = _get_db(self.postgres_uri_app_synth)
        if app_real_db and app_synth_db and app_real_db == app_synth_db:
            raise ValueError(
                f"Review Focus #4: postgres_uri_app and postgres_uri_app_synth point to the same database ('{app_real_db}'). "
                "Real and synthetic profiles must use isolated databases to prevent cross-contamination."
            )

        return self

    def _resolve_profile(self, profile: str | None = None) -> str:
        target = (profile or self.data_profile).strip().lower()
        if target not in ("real", "synth"):
            raise ValueError(f"Invalid profile '{target}'. Must be 'real' or 'synth'.")
        return target

    def get_ro_uri(self, profile: str | None = None) -> str:
        """Return the read-only PostgreSQL URI for the given or configured profile."""
        p = self._resolve_profile(profile)
        return self.postgres_uri_ro if p == "real" else self.postgres_uri_ro_synth

    def get_app_uri(self, profile: str | None = None) -> str:
        """Return the application state PostgreSQL URI for the given or configured profile."""
        p = self._resolve_profile(profile)
        return self.postgres_uri_app if p == "real" else self.postgres_uri_app_synth

    def get_admin_uri(self, profile: str | None = None) -> str:
        """Return the admin PostgreSQL URI for the given or configured profile."""
        from sqlalchemy.engine import make_url

        try:
            real_db = (make_url(self.postgres_uri_admin).database or "").strip().lower()
            synth_db = (make_url(self.postgres_uri_admin_synth).database or "").strip().lower()
            if real_db and synth_db and real_db == synth_db:
                raise ValueError(
                    f"Review Focus #4: Database names for real ('{real_db}') and synth ('{synth_db}') cannot be identical."
                )
        except ValueError:
            raise
        except Exception:
            pass

        p = self._resolve_profile(profile)
        return self.postgres_uri_admin if p == "real" else self.postgres_uri_admin_synth
