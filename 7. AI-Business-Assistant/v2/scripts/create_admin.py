"""CLI script to bootstrap the initial quan_tri_he_thong (System Admin) account.

Usage:
    python -m scripts.create_admin --username admin.it --display-name "Quản trị IT" [--email it@gominhlong.vn]

Specifications:
- Design §5.7
- Idempotent: if username already exists, reports cleanly without overwriting password.
- Prints generated one-time temporary password when a new account is created.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine

V2_DIR = Path(__file__).resolve().parent.parent
if str(V2_DIR) not in sys.path:
    sys.path.insert(0, str(V2_DIR))

from app.core.config import get_settings
from app.services import iam_service
from db.apply_db import get_iam_engine


def create_admin_account(
    engine: Engine,
    username: str,
    display_name: str,
    email: str | None = None,
) -> dict[str, Any]:
    """Idempotently create an internal quan_tri_he_thong account."""
    uname = (username or "").strip().lower()
    if not uname:
        raise ValueError("Tên đăng nhập (--username) không được để trống.")
    dname = (display_name or "").strip()
    if not dname:
        raise ValueError("Họ tên hiển thị (--display-name) không được để trống.")

    with engine.connect() as conn:
        existing = conn.execute(
            sa.text(
                "SELECT user_id, username, display_name, email, role, is_active "
                "FROM iam.app_user WHERE lower(username) = :uname"
            ),
            {"uname": uname},
        ).fetchone()

    if existing is not None:
        m = existing._mapping
        return {
            "created": False,
            "user": {
                "user_id": m["user_id"],
                "username": m["username"],
                "display_name": m["display_name"],
                "email": m["email"],
                "role": m["role"],
                "is_active": bool(m["is_active"]),
            },
            "temporary_password": None,
        }

    user_dict, temp_pw = iam_service.create_user(
        engine,
        username=uname,
        display_name=dname,
        role="quan_tri_he_thong",
        allowed_profiles=["real", "synth"],
        email=email,
        must_change_password=True,
        actor_user_id="cli_bootstrap",
    )
    return {
        "created": True,
        "user": user_dict,
        "temporary_password": temp_pw,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap an internal System Admin (quan_tri_he_thong) account."
    )
    parser.add_argument("--username", required=True, help="Admin login username")
    parser.add_argument("--display-name", required=True, help="Display name")
    parser.add_argument("--email", default=None, help="Optional email address")
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = get_iam_engine(app_uri=settings.get_app_uri(profile="real"))
    try:
        result = create_admin_account(
            engine,
            username=args.username,
            display_name=args.display_name,
            email=args.email,
        )
    finally:
        engine.dispose()

    user = result["user"]
    if not result["created"]:
        print(
            f"Tài khoản '{user['username']}' đã tồn tại (user_id={user['user_id']}, "
            f"role={user['role']}). Không ghi đè mật khẩu."
        )
        return 0

    print(
        f"Đã tạo tài khoản Quản trị hệ thống '{user['username']}' "
        f"(user_id={user['user_id']})."
    )
    print(f"Mật khẩu tạm (chỉ hiển thị một lần): {result['temporary_password']}")
    print("Người dùng sẽ được yêu cầu đổi mật khẩu ngay khi đăng nhập lần đầu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
