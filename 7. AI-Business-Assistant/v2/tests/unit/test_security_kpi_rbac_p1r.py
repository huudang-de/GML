"""Unit tests for KPI-level RBAC authorization and domain mapping (Task 3 / P1r).

Specifications:
- Brief: task-3-brief.md
- DOMAIN_BY_DASHBOARD: D1 -> no_vay, D2 -> kho, D3 -> cong_no, D4 -> tien_gui, D5 -> dong_tien
- can_access_kpi(role: str, kpi_key: str) -> bool
- kpi_domain(kpi_key: str) -> str
"""

import pytest

from app.core.security import DOMAIN_BY_DASHBOARD, can_access_kpi, kpi_domain
from app.knowledge.loader import load_kpis


@pytest.mark.parametrize("role,kpi,ok", [
    ("ceo", "du_no_ngan_han", True),
    ("ke_toan_truong", "du_no_ngan_han", True),
    ("quan_ly_kho", "du_no_ngan_han", False),
    ("quan_ly_kho", "gia_tri_hang_ton_kho", True),
    ("quan_ly_kho", "vong_quay_hang_ton_kho", False),   # R9: cần ai_v_bctc
    ("ke_toan_truong", "gia_tri_hang_ton_kho", False),
    ("quan_tri_he_thong", "du_no_ngan_han", False),
    ("ceo", "khong_ton_tai", True),
    ("quan_ly_kho", "khong_ton_tai", False),
])
def test_can_access_kpi(role, kpi, ok):
    assert can_access_kpi(role, kpi) is ok


def test_kpi_domain_maps_all_28_kpis():
    assert kpi_domain("du_no_ngan_han") == "no_vay"
    assert kpi_domain("gia_tri_hang_ton_kho") == "kho"
    assert kpi_domain("gia_tri_phai_thu") == "cong_no"
    assert kpi_domain("tien_gui_co_ky_han") == "tien_gui"
    assert kpi_domain("dong_tien_rong") == "dong_tien"
    kpis = load_kpis()
    assert len(kpis) == 28
    assert all(kpi_domain(k) for k in kpis)


def test_kpi_domain_unknown_dashboard_raises(monkeypatch):
    class FakeKpi:
        dashboard = "D9"

    monkeypatch.setattr("app.knowledge.loader.get_kpi", lambda k: FakeKpi())
    with pytest.raises(ValueError, match="Unknown dashboard 'D9'"):
        kpi_domain("dummy_kpi")


def test_domain_by_dashboard_mapping():
    assert DOMAIN_BY_DASHBOARD == {
        "D1": "no_vay",
        "D2": "kho",
        "D3": "cong_no",
        "D4": "tien_gui",
        "D5": "dong_tien",
    }
