"""Unit tests for P2r Task 1: Time-series models, loader, and knowledge layer.

Specifications:
- Task 1 of P2r: Models + Loader + Time-series data
- Pydantic models: SeriesQuery, KpiDefinition.series_ref
- Loader functions: load_series_queries, get_series_query
- 16 Standard KPIs with series_ref
"""

from pathlib import Path
import pytest
import yaml

from app.knowledge.loader import (
    get_kpi,
    get_role_profile,
    get_series_query,
    load_kpis,
    load_role_profiles,
    load_series_queries,
)
from app.knowledge.models import KpiDefinition, RoleProfile, SeriesQuery


def test_series_query_loaded_verbatim_for_du_no_ngan_han():
    sq = get_series_query("du_no_ngan_han")
    assert sq is not None
    assert sq.id == "S_du_no_ngan_han"
    assert sq.kpi_key == "du_no_ngan_han"
    assert sq.views_used == ["ai_v_no_vay"]
    assert sq.grain == "month"
    assert "34111%" in sq.sql_text and "period" in sq.sql_text.lower()


def test_kpi_without_series_ref_returns_none():
    assert get_series_query("ltv_ratio") is None
    assert get_series_query("non_existent_kpi") is None


def test_new_inventory_series_exist():
    for k in ("so_luong_hang_ton_kho", "tong_ma_san_pham"):
        sq = get_series_query(k)
        assert sq is not None, f"Missing series query for {k}"
        assert sq.views_used == ["ai_v_ton_kho"]
        assert sq.grain == "month"
        assert "period" in sq.sql_text.lower()


def test_all_16_series_queries_loaded_and_have_sql():
    expected_16 = [
        "du_no_ngan_han",
        "du_no_dai_han",
        "ty_le_su_dung_han_muc",
        "dong_tien_rong",
        "dong_tien_vao",
        "dong_tien_ra",
        "tien_va_tuong_duong_tien",
        "ty_le_no_tren_tong_nguon_von",
        "gia_tri_hang_ton_kho",
        "gia_tri_phai_thu",
        "gia_tri_phai_tra",
        "han_muc_phe_duyet",
        "han_muc_duoc_cap",
        "han_muc_con_lai",
        "so_luong_hang_ton_kho",
        "tong_ma_san_pham",
    ]
    series_queries = load_series_queries()
    assert len(series_queries) == 16

    kpis = load_kpis()
    for kpi_key in expected_16:
        assert kpi_key in series_queries, f"Missing {kpi_key} in load_series_queries()"
        sq = series_queries[kpi_key]
        assert sq.id == f"S_{kpi_key}"
        assert sq.kpi_key == kpi_key
        assert sq.grain == "month"
        assert len(sq.views_used) >= 1
        assert len(sq.sql_text.strip()) > 0
        assert "period" in sq.sql_text.lower()
        assert "value" in sq.sql_text.lower()

        # Check kpi_definition has series_ref
        kpi = kpis.get(kpi_key)
        assert kpi is not None
        assert kpi.series_ref == f"S_{kpi_key}"


def test_load_series_queries_bypasses_cache_when_custom_path_provided(tmp_path: Path):
    custom_yaml = tmp_path / "custom_series.yaml"
    dummy_sql = tmp_path / "dummy.sql"
    dummy_sql.write_text("SELECT 1 AS period, 2 AS value;", encoding="utf-8")

    data = {
        "queries": [
            {
                "id": "S_dummy",
                "kpi_key": "dummy_kpi",
                "sql_file": "dummy.sql",
                "views_used": ["ai_v_bctc"],
                "grain": "month",
            }
        ]
    }
    custom_yaml.write_text(yaml.dump(data), encoding="utf-8")

    res = load_series_queries(custom_yaml)
    assert "dummy_kpi" in res
    assert res["dummy_kpi"].sql_text == "SELECT 1 AS period, 2 AS value;"

    # Default cached loader must remain intact and contain original 16
    default_res = load_series_queries()
    assert "dummy_kpi" not in default_res
    assert "du_no_ngan_han" in default_res


def test_role_profiles_shape():
    p = get_role_profile("quan_ly_kho")
    assert p.role == "quan_ly_kho"
    assert p.greeting_title == "Quản lý kho"
    assert p.overview_kpis == ["gia_tri_hang_ton_kho", "so_luong_hang_ton_kho", "tong_ma_san_pham"]
    assert len(p.suggested_questions) == 4

    p_ceo = get_role_profile("ceo")
    assert p_ceo.role == "ceo"
    assert p_ceo.greeting_title == "Tổng Giám đốc"
    assert p_ceo.overview_kpis == [
        "du_no_ngan_han",
        "ty_le_su_dung_han_muc",
        "tien_va_tuong_duong_tien",
        "dong_tien_rong",
        "gia_tri_phai_thu",
        "gia_tri_hang_ton_kho",
    ]
    assert len(p_ceo.suggested_questions) == 4

    p_ktt = get_role_profile("ke_toan_truong")
    assert p_ktt.role == "ke_toan_truong"
    assert p_ktt.greeting_title == "Kế toán trưởng"
    assert p_ktt.overview_kpis == [
        "du_no_ngan_han",
        "ty_le_su_dung_han_muc",
        "tien_va_tuong_duong_tien",
        "dong_tien_rong",
        "gia_tri_phai_thu",
        "gia_tri_phai_tra",
    ]
    assert len(p_ktt.suggested_questions) == 4

    p_admin = get_role_profile("quan_tri_he_thong")
    assert p_admin.role == "quan_tri_he_thong"
    assert p_admin.greeting_title == "Quản trị hệ thống"
    assert p_admin.overview_kpis == []
    assert p_admin.suggested_questions == []

    p_unknown = get_role_profile("unknown")
    assert p_unknown.role == "unknown"
    assert p_unknown.greeting_title == ""
    assert p_unknown.overview_kpis == []
    assert p_unknown.suggested_questions == []


def test_get_role_profile_normalizes_role_name():
    p1 = get_role_profile("  CEO  ")
    assert p1.role == "ceo"
    assert p1.greeting_title == "Tổng Giám đốc"

    p2 = get_role_profile("Quan_Ly_Kho")
    assert p2.role == "quan_ly_kho"
    assert p2.greeting_title == "Quản lý kho"


def test_load_role_profiles_bypasses_cache_when_custom_path_provided(tmp_path: Path):
    custom_yaml = tmp_path / "custom_role_profiles.yaml"
    data = {
        "custom_role": {
            "role": "custom_role",
            "greeting_title": "Chuyên viên Tùy chỉnh",
            "overview_kpis": ["du_no_ngan_han"],
            "suggested_questions": ["Câu hỏi kiểm thử 1?"],
        }
    }
    custom_yaml.write_text(yaml.dump(data), encoding="utf-8")

    res = load_role_profiles(custom_yaml)
    assert "custom_role" in res
    assert res["custom_role"].greeting_title == "Chuyên viên Tùy chỉnh"
    assert res["custom_role"].overview_kpis == ["du_no_ngan_han"]

    # Default cached loader must remain intact and contain CEO
    default_res = load_role_profiles()
    assert "custom_role" not in default_res
    assert "ceo" in default_res


def test_all_overview_kpis_exist_in_kpi_definitions():
    profiles = load_role_profiles()
    kpis = load_kpis()
    for role_name, profile in profiles.items():
        for kpi_key in profile.overview_kpis:
            assert kpi_key in kpis, f"Role {role_name} has unknown overview KPI {kpi_key}"

