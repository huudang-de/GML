"""Authentication and Token Verification Service.

Specifications:
- TC-T5-02, TC-T5-05, TC-T5-09
- Spec §5 T5, §11.7
- SHA-256 token hashing with constant-time comparison
- Environment-aware dev token provisioning (blocked in production)
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.security import Role
from app.services.iam_service import verify_session_token


class AuthenticationError(Exception):
    """Raised when token authentication fails or token is expired."""
    def __init__(self, message: str = "Token không hợp lệ hoặc đã hết hạn.", status_code: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UserPrincipal(BaseModel):
    """Authenticated user principal representing identity and role."""

    user_id: str
    role: Role
    display_name: str
    expires_at: datetime | None = None
    username: str | None = None
    email: str | None = None
    allowed_profiles: list[str] = Field(default_factory=lambda: ["real", "synth"])
    must_change_password: bool = False
    session_id: int | None = None


def _hash_token(raw_token: str) -> str:
    """Compute hex SHA-256 digest of token string."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


class TokenAuthVerifier:
    """Verifies bearer tokens using SHA-256 digests and manages token identities."""

    def __init__(self, settings: Settings, iam_engine: Engine | None = None) -> None:
        self.settings = settings
        self.iam_engine = iam_engine
        self._tokens_by_hash: dict[str, UserPrincipal] = {}
        self._load_tokens()

    def _load_tokens(self) -> None:
        is_prod = (self.settings.app_env or "").strip().lower() == "production"

        # 1. Dev tokens ONLY when not in production
        if not is_prod:
            dev_tokens = [
                ("gml-dev-token-ceo", UserPrincipal(user_id="usr_ceo", role="ceo", display_name="Nguyễn Văn A (CEO)")),
                ("gml-dev-token-ktt", UserPrincipal(user_id="usr_ktt", role="ke_toan_truong", display_name="Trần Thị B (Kế toán trưởng)")),
                ("gml-dev-token-kho", UserPrincipal(user_id="usr_kho", role="quan_ly_kho", display_name="Lê Văn C (Quản lý kho)")),
                ("gml-dev-token-admin", UserPrincipal(user_id="usr_admin", role="quan_tri_he_thong", display_name="Quản trị hệ thống")),
            ]
            for raw_tok, principal in dev_tokens:
                self._tokens_by_hash[_hash_token(raw_tok)] = principal

        # 2. Parse auth_tokens_json if provided
        tokens_json = (self.settings.auth_tokens_json or "").strip()
        if tokens_json:
            try:
                parsed = json.loads(tokens_json)
                def _build_static_principal(item: dict[str, Any]) -> UserPrincipal:
                    exp = item.get("expires_at")
                    exp_dt = datetime.fromisoformat(exp) if exp else None
                    profiles = item.get("allowed_profiles")
                    return UserPrincipal(
                        user_id=item["user_id"],
                        username=item.get("username"),
                        email=item.get("email"),
                        role=item["role"],
                        display_name=item.get("display_name", item["user_id"]),
                        expires_at=exp_dt,
                        allowed_profiles=list(profiles) if profiles is not None else ["real", "synth"],
                        must_change_password=bool(item.get("must_change_password", False)),
                    )

                if isinstance(parsed, list):
                    for item in parsed:
                        raw_tok = item.get("token")
                        if not raw_tok:
                            continue
                        self._tokens_by_hash[_hash_token(raw_tok)] = _build_static_principal(item)
                elif isinstance(parsed, dict):
                    for raw_tok, item in parsed.items():
                        self._tokens_by_hash[_hash_token(raw_tok)] = _build_static_principal(item)
            except Exception as e:
                # If production and auth_tokens_json fails to parse, error will surface
                if is_prod:
                    raise ValueError(f"Failed to parse production auth_tokens_json: {e}") from e

    def verify_bearer_token(self, raw_token: str, now: datetime | None = None) -> UserPrincipal:
        """Verify token against stored hashes using constant-time comparison."""
        if not raw_token or not raw_token.strip():
            raise AuthenticationError("Token không được để trống (401 UNAUTHORIZED).")

        cand_hash = _hash_token(raw_token)
        matched_principal: UserPrincipal | None = None

        for stored_hash, principal in self._tokens_by_hash.items():
            if hmac.compare_digest(cand_hash, stored_hash):
                matched_principal = principal
                break

        if matched_principal is not None:
            current_time = now or datetime.now(timezone.utc)
            if matched_principal.expires_at is not None:
                exp_time = matched_principal.expires_at
                if exp_time.tzinfo is None:
                    exp_time = exp_time.replace(tzinfo=timezone.utc)
                if current_time.tzinfo is None:
                    current_time = current_time.replace(tzinfo=timezone.utc)
                if current_time >= exp_time:
                    raise AuthenticationError("Token đã hết hạn (401 UNAUTHORIZED).")
            return matched_principal

        # 2. Fall back to stateful PostgreSQL IAM session lookup
        engine = self.iam_engine
        created_engine = False
        if engine is None:
            try:
                from db.apply_db import get_iam_engine

                engine = get_iam_engine(app_uri=self.settings.get_app_uri(profile="real"))
                created_engine = True
            except Exception:
                engine = None

        session_data: dict[str, Any] | None = None
        if engine is not None:
            try:
                session_data = verify_session_token(engine, raw_token, now=now)
            except SQLAlchemyError:
                session_data = None
            finally:
                if created_engine and hasattr(engine, "dispose"):
                    engine.dispose()

        if session_data is None:
            raise AuthenticationError("Token không hợp lệ hoặc không tồn tại (401 UNAUTHORIZED).")

        return UserPrincipal(
            user_id=session_data["user_id"],
            username=session_data.get("username"),
            email=session_data.get("email"),
            role=session_data["role"],
            display_name=session_data["display_name"],
            expires_at=session_data.get("expires_at"),
            allowed_profiles=list(session_data.get("allowed_profiles") or ["real"]),
            must_change_password=bool(session_data.get("must_change_password", False)),
            session_id=session_data.get("session_id"),
        )
