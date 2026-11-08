"""Role-Based Access Control (RBAC) and Security Catalog Loader.

Adheres to:
- Spec §11.9 (Role-to-View Authorization Matrix)
- Plan Task 1 / Task 2 interfaces
"""

from pathlib import Path
from typing import Literal, Optional, Set
import yaml

Role = Literal["ceo", "ke_toan_truong", "quan_ly_kho", "quan_tri_he_thong"]

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "catalog.yaml"


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
