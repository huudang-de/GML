"""CLI script to seed the 4 development/staging demo accounts.

Usage:
    python -m scripts.seed_demo_users

Specifications:
- Design §5.7
- Strictly refuses to run when APP_ENV == 'production'.
- Preserves legacy user_ids: usr_ceo, usr_ktt, usr_kho, usr_admin.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

from sqlalchemy.engine import Engine

V2_DIR = Path(__file__).resolve().parent.parent
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

from app.core.config import Settings, get_settings
from app.services.iam_service import seed_default_demo_users
from db.apply_db import get_iam_engine


def run_seed_demo_users(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> list[dict[str, Any]]:
    """Seed demo accounts unless running in production."""
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "Từ chối chạy seed_demo_users: không được phép tạo tài khoản demo ở môi trường production."
        )

    cfg = settings or get_settings()
    if (cfg.app_env or "").strip().lower() == "production":
        raise RuntimeError(
            "Từ chối chạy seed_demo_users: không được phép tạo tài khoản demo ở môi trường production."
        )

    target_engine = engine or get_iam_engine(app_uri=cfg.get_app_uri(profile="real"))
    created_engine = engine is None
    try:
        return seed_default_demo_users(target_engine)
    finally:
        if created_engine and hasattr(target_engine, "dispose"):
            target_engine.dispose()


def main() -> int:
    try:
        users = run_seed_demo_users()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Đã đảm bảo {len(users)} tài khoản demo tồn tại:")
    for u in users:
        print(f"  - {u['user_id']}: {u['username']} (role={u['role']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
