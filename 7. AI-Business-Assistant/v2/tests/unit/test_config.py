import pytest
from datetime import date
from app.core.config import Settings
from app.core.errors import UnsafeDeploymentError, SqlRejected, DbExecutionError, sanitize_db_error
from app.core.security import get_allowed_views, load_catalog


def test_tc_t5_09_block_unsafe_production_config():
    """TC-T5-09: APP_ENV=production + cloud LLM free tier -> refuse startup."""
    with pytest.raises(UnsafeDeploymentError, match="(?i)production"):
        Settings(
            app_env="production",
            llm_provider="gemini",
            llm_tier="free",
        )


def test_production_allows_paid_or_local_llm():
    """Paid cloud LLM or local Ollama should be accepted in production."""
    s_paid = Settings(app_env="production", llm_provider="gemini", llm_tier="paid")
    assert s_paid.app_env == "production"
    s_local = Settings(app_env="production", llm_provider="ollama", llm_tier="free")
    assert s_local.llm_provider == "ollama"


def test_default_settings_and_as_of_date():
    """Default settings should have valid defaults and as_of_date=2026-07-31."""
    s = Settings(_env_file=None)
    assert s.data_profile in ("real", "synth")
    assert s.as_of_date == date(2026, 7, 31)
    assert "postgresql" in s.postgres_uri_ro
    assert "gml_synth" in s.postgres_uri_admin_synth
    assert "dev:Inda1234" not in s.postgres_uri_admin_synth


def test_cross_profile_collision_set_disjointness():
    """Any overlap between real and synth database sets must raise ValueError."""
    with pytest.raises(ValueError, match="Cross-profile database collision detected"):
        Settings(
            postgres_uri_ro="postgresql+psycopg2://u:p@localhost:5432/shared_db",
            postgres_uri_admin="postgresql+psycopg2://u:p@localhost:5432/real_admin",
            postgres_uri_app="postgresql+psycopg2://u:p@localhost:5432/real_app",
            postgres_uri_ro_synth="postgresql+psycopg2://u:p@localhost:5432/synth_ro",
            postgres_uri_admin_synth="postgresql+psycopg2://u:p@localhost:5432/shared_db",  # Collides with postgres_uri_ro
            postgres_uri_app_synth="postgresql+psycopg2://u:p@localhost:5432/synth_app",
        )



def test_rbac_allowed_views_match_spec_section_11_9():
    """RBAC matrix from catalog.yaml must match Spec §11.9 exactly."""
    assert get_allowed_views("ceo") == {
        "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc",
        "ai_v_ton_kho", "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach",
    }
    assert get_allowed_views("ke_toan_truong") == {
        "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc",
        "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach",
    }
    assert get_allowed_views("quan_ly_kho") == {"ai_v_ton_kho"}
    assert get_allowed_views("quan_tri_he_thong") == set()
    # Unknown role should return empty set
    assert get_allowed_views("unknown_role") == set()


def test_sanitize_db_error_strips_silver_and_credentials():
    """DB error messages must not leak silver schema, passwords, or file paths."""
    raw = (
        'OperationalError: connection to "postgresql://postgres:secret123@localhost:5432/gml" '
        'failed: relation "silver.fact_cashflow" does not exist at D:\\secret\\path.py'
    )
    cleaned = sanitize_db_error(raw)
    assert "secret123" not in cleaned
    assert "silver." not in cleaned
    assert "D:\\secret" not in cleaned
    assert "[REDACTED" in cleaned


def test_sanitize_db_error_handles_exception_instances():
    """sanitize_db_error must accept Exception objects as well as strings."""
    exc = RuntimeError(
        "psycopg2.OperationalError: postgresql+psycopg2://admin:super_secret@10.0.0.1:5432/db "
        "table silver.fact_loan in file /var/app/db/connection.py"
    )
    cleaned = sanitize_db_error(exc)
    assert "super_secret" not in cleaned
    assert "silver." not in cleaned
    assert "/var/app" not in cleaned


def test_catalog_load_structure():
    """Verify load_catalog parses 7 views with required metadata."""
    catalog = load_catalog()
    assert "views" in catalog
    views = catalog["views"]
    assert len(views) == 7
    for view_name, meta in views.items():
        assert "description" in meta
        assert "grain" in meta
        assert "allowed_roles" in meta
        assert "columns" in meta
        assert len(meta["columns"]) > 0
