"""Integration tests for Migration 002 (DataAgent Adoption schema extensions).

Specifications:
- Spec §5.1 (Amended Architecture Spec)
- Plan P1r Task 2
- TC-T1-08: Migration 002 idempotency, columns, tables, and constraints
- TC-T1-09: gml_ai_ro role cannot access or mutate new app tables
"""

import pytest
import sqlalchemy as sa

from db.apply_db import (
    apply_all,
    get_admin_engine,
    get_app_engine,
    get_ro_engine,
)

APP_COLUMNS = {"period", "evidence", "dedup_key", "escalated_at"}


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test records before and after each test."""
    def _do_clean():
        try:
            with get_admin_engine().begin() as c:
                c.execute(sa.text("DELETE FROM app.action_item WHERE created_by = 'u' OR title LIKE 'TEST_%'"))
                c.execute(sa.text("DELETE FROM app.pinned_kpi WHERE user_id = 'u' OR user_id LIKE 'TEST_%'"))
                c.execute(sa.text("DELETE FROM app.alert_event WHERE rule_id LIKE 'TEST_%'"))
        except Exception:
            # During initial RED test execution, tables might not exist yet
            pass

    _do_clean()
    yield
    _do_clean()


def test_tc_t1_08_migration_002_idempotent_and_schema():
    """Verify apply_all can run repeatedly without error and all columns/tables exist."""
    apply_all()
    apply_all()  # idempotent execution check

    with get_admin_engine().connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='app' AND table_name='alert_event'"
                )
            )
        }
        assert APP_COLUMNS <= cols, f"Missing columns in app.alert_event: {APP_COLUMNS - cols}"

        tables = {
            r[0]
            for r in c.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='app'"
                )
            )
        }
        assert {"action_item", "pinned_kpi"} <= tables, f"Missing tables in app: {{'action_item', 'pinned_kpi'}} - {tables}"


def test_action_item_status_check_rejects_unknown():
    """Verify app.action_item status CHECK constraint rejects unknown statuses."""
    with pytest.raises(Exception):
        with get_app_engine().begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO app.action_item ("
                    "title, kpi_key, level, source_type, source_ref, assigned_role, status, created_by"
                    ") VALUES ('x', 'k', 'canh_bao', 'alert', '1', 'ceo', 'hack', 'u')"
                )
            )


def test_action_item_unique_source_ref_title():
    """Verify app.action_item uniqueness constraint on (source_type, source_ref, title)."""
    with get_app_engine().begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO app.action_item ("
                "title, kpi_key, level, source_type, source_ref, assigned_role, status, created_by"
                ") VALUES ('TEST_TITLE_1', 'kpi_test', 'canh_bao', 'alert', 'ref_1', 'ceo', 'open', 'u')"
            )
        )

    with pytest.raises(Exception) as exc_info:
        with get_app_engine().begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO app.action_item ("
                    "title, kpi_key, level, source_type, source_ref, assigned_role, status, created_by"
                    ") VALUES ('TEST_TITLE_1', 'kpi_test', 'nghiem_trong', 'alert', 'ref_1', 'cfo', 'open', 'u')"
                )
            )
    err = str(exc_info.value).lower()
    assert "unique" in err or "duplicate" in err


def test_alert_dedup_key_unique_but_nulls_allowed():
    """Verify app.alert_event dedup_key allows multiple NULLs but rejects duplicates."""
    with get_app_engine().begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, dedup_key) "
                "VALUES ('TEST_DEDUP', 'kpi_test', 'canh_bao', 'msg 1', NULL)"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, dedup_key) "
                "VALUES ('TEST_DEDUP', 'kpi_test', 'canh_bao', 'msg 2', NULL)"
            )
        )
        c.execute(
            sa.text(
                "INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, dedup_key) "
                "VALUES ('TEST_DEDUP', 'kpi_test', 'canh_bao', 'msg 3', 'TEST_KEY_2026_07')"
            )
        )

    # Second insert with identical dedup_key must raise IntegrityError
    with pytest.raises(Exception) as exc_info:
        with get_app_engine().begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO app.alert_event (rule_id, kpi_key, severity, message, dedup_key) "
                    "VALUES ('TEST_DEDUP', 'kpi_test', 'canh_bao', 'msg 4', 'TEST_KEY_2026_07')"
                )
            )
    err = str(exc_info.value).lower()
    assert "unique" in err or "duplicate" in err


def test_pinned_kpi_constraints():
    """Verify app.pinned_kpi unique constraint and data_profile check."""
    # Check valid insert
    with get_app_engine().begin() as c:
        c.execute(
            sa.text(
                "INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position) "
                "VALUES ('u', 'real', 'kpi_rev', 1)"
            )
        )

    # Duplicate (user_id, data_profile, kpi_key) rejected
    with pytest.raises(Exception) as exc_info:
        with get_app_engine().begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position) "
                    "VALUES ('u', 'real', 'kpi_rev', 2)"
                )
            )
    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    # Invalid data_profile rejected
    with pytest.raises(Exception):
        with get_app_engine().begin() as c:
            c.execute(
                sa.text(
                    "INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key, position) "
                    "VALUES ('u', 'invalid_profile', 'kpi_rev', 3)"
                )
            )


def test_tc_t1_09_ro_role_cannot_touch_new_tables():
    """TC-T1-09: gml_ai_ro cannot SELECT or INSERT on app.action_item or app.pinned_kpi."""
    for stmt in (
        "SELECT 1 FROM app.action_item",
        "INSERT INTO app.pinned_kpi (user_id, data_profile, kpi_key) VALUES ('u', 'real', 'k')",
    ):
        with pytest.raises(Exception) as exc_info:
            with get_ro_engine().connect() as c:
                c.execute(sa.text(stmt))
                c.commit()
        assert "permission denied" in str(exc_info.value).lower(), f"Expected permission denied for {stmt}"
