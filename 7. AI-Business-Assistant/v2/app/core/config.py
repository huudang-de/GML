"""Configuration management using pydantic-settings.

Enforces production safety gates (TC-T5-09) and centralizes environment configuration.
"""

from datetime import date
from pathlib import Path
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.errors import UnsafeDeploymentError

_DEFAULT_ENV_FILE = str(Path(__file__).resolve().parent.parent.parent / ".env")


class Settings(BaseSettings):
    """Application settings with environment variable loading and validation."""

    # Deployment Environment
    app_env: str = "development"  # development | staging | production

    # Data Profile & Cutoff Date
    data_profile: str = "real"  # real | synth
    as_of_date: date = date(2026, 7, 31)

    # Database Connection URIs - Real Profile
    postgres_uri_ro: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/data_warehouse"
    postgres_uri_app: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/data_warehouse"
    postgres_uri_admin: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/data_warehouse"

    # Database Connection URIs - Synthetic Profile
    postgres_uri_ro_synth: str = "postgresql+psycopg2://gml_ai_ro:ro_secret@localhost:5432/gml_synth"
    postgres_uri_app_synth: str = "postgresql+psycopg2://gml_ai_app:app_secret@localhost:5432/gml_synth"
    postgres_uri_admin_synth: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/gml_synth"

    # LLM Settings
    llm_provider: str = "gemini"  # gemini | ollama | mock
    llm_model: str = "gemini-3.8-flash"
    llm_tier: str = "free"  # free | paid
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # RAG Settings
    chroma_persist_dir: str = "data/chroma_db"
    rag_manifest_path: str = "data/rag_manifest.json"
    embedding_provider: str = "auto"
    embedding_model: str = "nomic-embed-text"

    # API Security, Rate Limiting & Cache Settings (T5)
    auth_tokens_json: str = ""
    rate_limit_per_minute: int = 60
    kpi_cache_ttl_seconds: int = 60
    session_ttl_days: int = 30
    api_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=(_DEFAULT_ENV_FILE, ".env"),
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

        real_dbs = {
            db
            for uri in [self.postgres_uri_ro, self.postgres_uri_admin, self.postgres_uri_app]
            if (db := _get_db(uri))
        }
        synth_dbs = {
            db
            for uri in [self.postgres_uri_ro_synth, self.postgres_uri_admin_synth, self.postgres_uri_app_synth]
            if (db := _get_db(uri))
        }

        if collision := real_dbs.intersection(synth_dbs):
            raise ValueError(
                f"Cross-profile database collision detected: {collision}. "
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


from functools import lru_cache


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()

