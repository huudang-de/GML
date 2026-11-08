"""Integration tests for Task 1: Synthetic Data Generation, View Alignment, and Isolation.

Specifications:
- Spec §3.1, §6.1, §6 Warning
- Plan Task 1: T1-synth
- TC-T1-05: Deterministic synthetic warehouse generator checksum (EV-03)
- TC-T1-06: Zero SYNTH_ markers in real data warehouse
- TC-T1-07: 5 labeled anomalies verifiable in synthetic views
- Review Focus #4: Profile URI isolation (real vs synth)
"""

from pathlib import Path
import pytest
import sqlalchemy as sa
import yaml

from app.core.config import Settings
from db.apply_db import get_ro_engine
from db.synthetic.generate import generate_synthetic_warehouse


def test_profile_uri_isolation_and_no_cross_contamination():
    """Verify real and synth profile URIs are isolated and reject collision."""
    settings = Settings(
        postgres_uri_ro="postgresql+psycopg2://user:pass@localhost:5432/data_warehouse",
        postgres_uri_ro_synth="postgresql+psycopg2://user:pass@localhost:5432/gml_synth",
        postgres_uri_admin="postgresql+psycopg2://user:pass@localhost:5432/data_warehouse",
        postgres_uri_admin_synth="postgresql+psycopg2://user:pass@localhost:5432/gml_synth",
        postgres_uri_app="postgresql+psycopg2://user:pass@localhost:5432/data_warehouse",
        postgres_uri_app_synth="postgresql+psycopg2://user:pass@localhost:5432/gml_synth",
    )
    assert settings.get_ro_uri("real") != settings.get_ro_uri("synth")
    assert settings.get_app_uri("real") != settings.get_app_uri("synth")
    assert settings.get_admin_uri("real") != settings.get_admin_uri("synth")

    # Rejection of identical database names (Review Focus #4)
    with pytest.raises(ValueError) as exc:
        Settings(
            postgres_uri_ro="postgresql+psycopg2://u:p@localhost:5432/data_warehouse",
            postgres_uri_ro_synth="postgresql+psycopg2://u:p@localhost:5432/data_warehouse",
        )
    err_text = str(exc.value).lower()
    assert "same database" in err_text or "isolated" in err_text


def test_uat_extended_view_columns_match_uat02_uat03():
    """Verify new view columns match UAT_02 (ton kho) and UAT_03 (cong no) ground truth."""
    ro_engine = get_ro_engine(profile="real")
    with ro_engine.connect() as conn:
        # AR UAT_03
        ar_sql = """
            SELECT SUM(ending_debit_balance)
            FROM ai_views.ai_v_cong_no
            WHERE ar_ap_type = 'AR'
              AND partner_group IN ('Khách hàng', 'Khách hàng/ nhà cung cấp')
              AND rn = 1;
        """
        ar_val = float(conn.execute(sa.text(ar_sql)).scalar() or 0)
        assert abs(ar_val - 36326095573.00) <= 0.01, f"AR expected 36326095573.00, got {ar_val}"

        # AP UAT_03
        ap_sql = """
            SELECT SUM(ending_credit_balance)
            FROM ai_views.ai_v_cong_no
            WHERE ar_ap_type = 'AP'
              AND partner_group IN ('Nhà cung cấp', 'Khách hàng/ nhà cung cấp')
              AND rn = 1;
        """
        ap_val = float(conn.execute(sa.text(ap_sql)).scalar() or 0)
        assert abs(ap_val - 60452900187.23) <= 0.01, f"AP expected 60452900187.23, got {ap_val}"

        # Inward UAT_02
        inward_sql = """
            SELECT SUM(total_value)
            FROM ai_views.ai_v_ton_kho
            WHERE record_type = 'inward'
              AND exchange_rate > 1;
        """
        inward_val = float(conn.execute(sa.text(inward_sql)).scalar() or 0)
        assert abs(inward_val - 163157504466.00) <= 0.01, f"Inward expected 163157504466.00, got {inward_val}"


def test_tc_t1_05_deterministic_generator_checksum():
    """TC-T1-05: Generator produces identical checksums across repeat executions."""
    c1 = generate_synthetic_warehouse(seed=42)
    c2 = generate_synthetic_warehouse(seed=42)
    assert c1 == c2, "Checksums differed between identical seed runs!"
    checksum_file = Path(__file__).resolve().parent.parent.parent / "db" / "synthetic" / "CHECKSUM.txt"
    assert checksum_file.exists(), "CHECKSUM.txt file does not exist!"
    content = checksum_file.read_text(encoding="utf-8").strip()
    assert len(content) > 0, "CHECKSUM.txt file is empty!"
    assert any(tbl in content for tbl in c1.keys())


def test_tc_t1_06_real_profile_contains_zero_synth_markers():
    """TC-T1-06: Real data profile contains zero 'SYNTH_' marker records."""
    ro_engine = get_ro_engine(profile="real")
    views = [
        "ai_v_no_vay", "ai_v_dong_tien", "ai_v_bctc", "ai_v_ton_kho",
        "ai_v_cong_no", "ai_v_tien_gui", "ai_v_ke_hoach"
    ]
    with ro_engine.connect() as conn:
        for v in views:
            col_res = conn.execute(sa.text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'ai_views' AND table_name = '{v}'
                  AND data_type IN ('text', 'character varying')
            """)).fetchall()
            text_cols = [r[0] for r in col_res]
            if not text_cols:
                continue
            conditions = " OR ".join([f"{c} LIKE '%SYNTH\\_%' ESCAPE '\\'" for c in text_cols])
            query = f"SELECT COUNT(*) FROM ai_views.{v} WHERE {conditions}"
            count = conn.execute(sa.text(query)).scalar()
            assert count == 0, f"Found {count} rows with SYNTH_ marker in real view {v}!"


def test_tc_t1_07_labeled_anomalies_match_synthetic_views():
    """TC-T1-07: Labeled anomalies in anomalies.yaml are verifiable in ai_views on synthetic DB."""
    anomalies_file = Path(__file__).resolve().parent.parent.parent / "db" / "synthetic" / "anomalies.yaml"
    assert anomalies_file.exists(), "anomalies.yaml not found!"
    with open(anomalies_file, "r", encoding="utf-8") as f:
        anomalies_doc = yaml.safe_load(f)

    anomalies = anomalies_doc.get("anomalies", [])
    assert len(anomalies) >= 5, f"Expected at least 5 anomalies, got {len(anomalies)}"

    synth_ro_engine = get_ro_engine(profile="synth")
    with synth_ro_engine.connect() as conn:
        for anom in anomalies:
            anom_id = anom["id"]
            sql = anom["verification_sql"]
            expected = float(anom["expected_value"])
            tolerance = float(anom.get("tolerance", 1e-4))

            res = conn.execute(sa.text(sql)).scalar()
            assert res is not None, f"Query returned None for anomaly {anom_id}: {sql}"
            actual = float(res)

            diff = abs(actual - expected)
            rel_diff = diff / max(abs(expected), 1e-9)
            assert diff <= tolerance or rel_diff <= tolerance, (
                f"Anomaly {anom_id} ({anom.get('kpi')}): actual={actual}, expected={expected}, "
                f"diff={diff}, tolerance={tolerance}"
            )
