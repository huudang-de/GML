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
    get_series_query,
    load_kpis,
    load_series_queries,
)
from app.knowledge.models import KpiDefinition, SeriesQuery


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
