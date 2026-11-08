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
from pydantic import BaseModel

from app.core.config import Settings
from app.core.security import Role


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


def _hash_token(raw_token: str) -> str:
    """Compute hex SHA-256 digest of token string."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


class TokenAuthVerifier:
    """Verifies bearer tokens using SHA-256 digests and manages token identities."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
                if isinstance(parsed, list):
                    for item in parsed:
                        raw_tok = item.get("token")
                        if not raw_tok:
                            continue
                        exp = item.get("expires_at")
                        exp_dt = datetime.fromisoformat(exp) if exp else None
                        principal = UserPrincipal(
                            user_id=item["user_id"],
                            role=item["role"],
                            display_name=item.get("display_name", item["user_id"]),
                            expires_at=exp_dt,
                        )
                        self._tokens_by_hash[_hash_token(raw_tok)] = principal
                elif isinstance(parsed, dict):
                    for raw_tok, item in parsed.items():
                        exp = item.get("expires_at")
                        exp_dt = datetime.fromisoformat(exp) if exp else None
                        principal = UserPrincipal(
                            user_id=item["user_id"],
                            role=item["role"],
                            display_name=item.get("display_name", item["user_id"]),
                            expires_at=exp_dt,
                        )
                        self._tokens_by_hash[_hash_token(raw_tok)] = principal
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

        if matched_principal is None:
            raise AuthenticationError("Token không hợp lệ hoặc không tồn tại (401 UNAUTHORIZED).")

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
