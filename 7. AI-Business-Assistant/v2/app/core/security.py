"""Role-Based Access Control (RBAC) and Security Catalog Loader.

Adheres to:
- Spec §11.9 (Role-to-View Authorization Matrix)
- Plan Task 1 / Task 2 interfaces
- Plan Task 3 / P1r interfaces (KPI-level RBAC and domain mapping)
"""

from pathlib import Path
from typing import Literal, Optional, Set
import yaml

Role = Literal["ceo", "ke_toan_truong", "quan_ly_kho", "quan_tri_he_thong"]

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "catalog.yaml"

DOMAIN_BY_DASHBOARD: dict[str, str] = {
    "D1": "no_vay",
    "D2": "kho",
    "D3": "cong_no",
    "D4": "tien_gui",
    "D5": "dong_tien",
}


def load_catalog(catalog_path: Optional[Path] = None) -> dict:
    """Load the YAML catalog containing view definitions and RBAC rules.

    Args:
        catalog_path: Optional path to catalog.yaml. Defaults to v2/db/catalog.yaml.

    Returns:
        dict: Parsed YAML catalog dictionary.
    """
    path = catalog_path or DEFAULT_CATALOG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_allowed_views(role: str, catalog_path: Optional[Path] = None) -> Set[str]:
    """Retrieve the set of allowed ai_views for a given user role.

    Based on Spec §11.9:
    - ceo: All 7 views
    - ke_toan_truong: 6 financial views (excluding ai_v_ton_kho)
    - quan_ly_kho: 1 view (ai_v_ton_kho)
    - quan_tri_he_thong: 0 views (empty set)
    - unknown roles: empty set

    Args:
        role: Role identifier string (e.g. 'ceo', 'ke_toan_truong').
        catalog_path: Optional override for catalog.yaml path.

    Returns:
        Set[str]: Set of view names (e.g. {'ai_v_no_vay', ...}).
    """
    catalog = load_catalog(catalog_path)
    views = catalog.get("views", {})
    allowed: Set[str] = set()

    role_norm = role.strip().lower()
    for view_name, meta in views.items():
        roles = [r.strip().lower() for r in meta.get("allowed_roles", [])]
        if role_norm in roles:
            allowed.add(view_name)

    return allowed


def can_access_kpi(role: str, kpi_key: str) -> bool:
    """Check if a given role has permission to access the specified KPI.

    Uses KPI definition source views: required views must be a subset of allowed views for the role.
    If the KPI key is not found in the knowledge base, falls back to role in ('ceo', 'quan_tri_he_thong').
    Import get_kpi lazily to prevent circular imports with knowledge.loader.

    Args:
        role: Role identifier string (e.g. 'ceo', 'quan_ly_kho').
        kpi_key: Identifier key of the KPI.

    Returns:
        bool: True if authorized, False otherwise.
    """
    from app.knowledge.loader import get_kpi

    try:
        kpi_def = get_kpi(kpi_key)
        required_views = set(kpi_def.nguon_view)
        allowed_views = get_allowed_views(role)
        return required_views.issubset(allowed_views)
    except KeyError:
        return role in ("ceo", "quan_tri_he_thong")


def kpi_domain(kpi_key: str) -> str:
    """Return the operational domain for a given KPI key.

    Maps dashboard identifier (D1-D5) to domain string:
    - D1 -> no_vay
    - D2 -> kho
    - D3 -> cong_no
    - D4 -> tien_gui
    - D5 -> dong_tien

    Raises:
        KeyError: If kpi_key is not found in knowledge base.
        ValueError: If the KPI definition specifies an unknown dashboard.
    """
    from app.knowledge.loader import get_kpi

    kpi_def = get_kpi(kpi_key)
    if kpi_def.dashboard not in DOMAIN_BY_DASHBOARD:
        raise ValueError(
            f"Unknown dashboard '{kpi_def.dashboard}' for KPI '{kpi_key}'. "
            f"Expected one of {list(DOMAIN_BY_DASHBOARD.keys())}."
        )
    return DOMAIN_BY_DASHBOARD[kpi_def.dashboard]

