"""Internal Identity and Access Management (IAM) service.

Implements OWASP & NIST SP 800-63B compliant authentication, Argon2id password
hashing with dummy timing defense, stateful SHA-256 session lifecycle, and
administrative user/session/audit management on the PostgreSQL `iam` schema.

Specifications:
- Design §5.2, §5.3
- Plan Task 1
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

VALID_ROLES: tuple[str, ...] = (
    "ceo",
    "ke_toan_truong",
    "quan_ly_kho",
    "quan_tri_he_thong",
)
VALID_PROFILES: tuple[str, ...] = ("real", "synth")
DEFAULT_ALLOWED_PROFILES: list[str] = ["real", "synth"]

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
SESSION_TTL_HOURS = 12
SESSION_IDLE_HOURS = 2
LAST_SEEN_THROTTLE_SECONDS = 60

_PASSWORD_BLOCKLIST: frozenset[str] = frozenset(
    {
        "minhlong",
        "gominhlong",
        "password",
        "1234567890",
        "qwerty12345",
    }
)

_FORBIDDEN_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "plain",
        "current_password",
        "new_password",
        "temporary_password",
        "password_hash",
        "token",
        "raw_token",
        "access_token",
        "token_hash",
    }
)

_SAFE_USER_COLUMNS = (
    "user_id, username, display_name, email, role, allowed_profiles, "
    "is_active, must_change_password, failed_login_count, locked_until, "
    "last_login_at, password_changed_at, created_by, created_at, updated_at"
)

_PASSWORD_HASHER = PasswordHasher(memory_cost=19456, time_cost=2, parallelism=1)
_DUMMY_PASSWORD_HASH: str = _PASSWORD_HASHER.hash("gml-dummy-timing-defense-2026")

_TEMP_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_TEMP_LOWER = "abcdefghijkmnopqrstuvwxyz"
_TEMP_DIGITS = "23456789"
_TEMP_SYMBOLS = "!@#$%&*"
_TEMP_ALL = _TEMP_UPPER + _TEMP_LOWER + _TEMP_DIGITS + _TEMP_SYMBOLS


class IamError(Exception):
    """Base exception for all IAM domain errors."""


class InvalidCredentialsError(IamError):
    """Raised when username/password is invalid or account is disabled."""


class AccountLockedError(IamError):
    """Raised when an account is temporarily locked after repeated failures."""

    def __init__(self, message: str, locked_until: datetime) -> None:
        super().__init__(message)
        self.locked_until = locked_until


class PasswordPolicyError(IamError):
    """Raised when a password violates NIST SP 800-63B policy rules."""


class UserConflictError(IamError):
    """Raised when creating a user with an already-existing username."""


class UserNotFoundError(IamError):
    """Raised when a target user_id does not exist."""


class SelfLockoutError(IamError):
    """Raised when an admin attempts to disable or demote their own account."""


class LastAdminProtectedError(IamError):
    """Raised when disabling or demoting the last active system admin."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def _validate_role(role: str) -> str:
    role_norm = (role or "").strip()
    if role_norm not in VALID_ROLES:
        raise IamError(f"Vai trò '{role}' không hợp lệ. Phải thuộc {VALID_ROLES}.")
    return role_norm


def _validate_profiles(allowed_profiles: list[str] | None) -> list[str]:
    if allowed_profiles is None:
        return list(DEFAULT_ALLOWED_PROFILES)
    deduped = list(dict.fromkeys(p.strip().lower() for p in allowed_profiles if p and p.strip()))
    if not deduped:
        raise IamError("Tài khoản phải được cấp ít nhất một nguồn dữ liệu ('real' hoặc 'synth').")
    for prof in deduped:
        if prof not in VALID_PROFILES:
            raise IamError(f"Nguồn dữ liệu '{prof}' không hợp lệ. Phải thuộc {VALID_PROFILES}.")
    return deduped


def _sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if detail is None:
        return None
    cleaned: dict[str, Any] = {}
    for k, v in detail.items():
        if str(k).strip().lower() in _FORBIDDEN_DETAIL_KEYS:
            continue
        if isinstance(v, dict):
            cleaned[k] = _sanitize_detail(v)
        else:
            cleaned[k] = v
    return cleaned


def _row_to_user_dict(row: Any) -> dict[str, Any]:
    mapping = row._mapping if hasattr(row, "_mapping") else row
    return {
        "user_id": mapping["user_id"],
        "username": mapping["username"],
        "display_name": mapping["display_name"],
        "email": mapping["email"],
        "role": mapping["role"],
        "allowed_profiles": list(mapping["allowed_profiles"] or []),
        "is_active": bool(mapping["is_active"]),
        "must_change_password": bool(mapping["must_change_password"]),
        "failed_login_count": int(mapping["failed_login_count"]),
        "locked_until": mapping["locked_until"],
        "last_login_at": mapping["last_login_at"],
        "password_changed_at": mapping["password_changed_at"],
        "created_by": mapping["created_by"],
        "created_at": mapping["created_at"],
        "updated_at": mapping["updated_at"],
    }


def _insert_auth_event(
    conn: Connection,
    *,
    event_type: str,
    user_id: str | None = None,
    username_attempted: str | None = None,
    actor_user_id: str | None = None,
    detail: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> None:
    safe_detail = _sanitize_detail(detail)
    detail_json = json.dumps(safe_detail, ensure_ascii=False, default=str) if safe_detail is not None else None
    conn.execute(
        sa.text(
            "INSERT INTO iam.auth_event "
            "(event_type, user_id, username_attempted, actor_user_id, detail, client_ip) "
            "VALUES (:event_type, :user_id, :username_attempted, :actor_user_id, "
            "CAST(:detail AS JSONB), :client_ip)"
        ),
        {
            "event_type": event_type[:40],
            "user_id": user_id,
            "username_attempted": username_attempted[:64] if username_attempted else None,
            "actor_user_id": actor_user_id,
            "detail": detail_json,
            "client_ip": client_ip[:64] if client_ip else None,
        },
    )


def record_auth_event(
    engine: Engine,
    event_type: str,
    user_id: str | None = None,
    username_attempted: str | None = None,
    actor_user_id: str | None = None,
    detail: dict[str, Any] | None = None,
    client_ip: str | None = None,
) -> None:
    """Persist a sanitized audit event into iam.auth_event."""
    with engine.begin() as conn:
        _insert_auth_event(
            conn,
            event_type=event_type,
            user_id=user_id,
            username_attempted=username_attempted,
            actor_user_id=actor_user_id,
            detail=detail,
            client_ip=client_ip,
        )


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2id (OWASP recommended parameters)."""
    if not isinstance(plain, str) or not plain:
        raise PasswordPolicyError("Mật khẩu không được để trống.")
    return _PASSWORD_HASHER.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2id hash without raising."""
    if not plain or not hashed:
        return False
    try:
        return bool(_PASSWORD_HASHER.verify(hashed, plain))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def validate_password_strength(
    password: str,
    username: str | None = None,
    email: str | None = None,
) -> None:
    """Enforce NIST SP 800-63B password policy and context blocklist."""
    if not isinstance(password, str):
        raise PasswordPolicyError("Mật khẩu không hợp lệ.")
    if len(password) < 10 or len(password) > 128:
        raise PasswordPolicyError("Mật khẩu phải có độ dài từ 10 đến 128 ký tự.")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        raise PasswordPolicyError("Mật khẩu phải chứa ít nhất 1 chữ cái và 1 chữ số.")

    lower_pw = password.lower()
    for forbidden in _PASSWORD_BLOCKLIST:
        if forbidden in lower_pw:
            raise PasswordPolicyError("Mật khẩu chứa cụm từ bị cấm hoặc quá phổ biến.")

    if username:
        uname = _normalize_username(username)
        if len(uname) >= 3 and uname in lower_pw:
            raise PasswordPolicyError("Mật khẩu không được chứa tên đăng nhập.")

    if email and "@" in email:
        local_part = email.strip().lower().split("@", 1)[0]
        if len(local_part) >= 3 and local_part in lower_pw:
            raise PasswordPolicyError("Mật khẩu không được chứa tên email.")


def generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically random temporary password satisfying policy."""
    target_len = max(int(length), 10)
    rng = secrets.SystemRandom()
    while True:
        chars = [
            secrets.choice(_TEMP_UPPER),
            secrets.choice(_TEMP_LOWER),
            secrets.choice(_TEMP_DIGITS),
            secrets.choice(_TEMP_SYMBOLS),
        ]
        chars.extend(secrets.choice(_TEMP_ALL) for _ in range(target_len - len(chars)))
        rng.shuffle(chars)
        candidate = "".join(chars)
        try:
            validate_password_strength(candidate)
            return candidate
        except PasswordPolicyError:
            continue


def hash_session_token(raw_token: str) -> str:
    """Compute hex SHA-256 digest of a raw bearer session token."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def authenticate_user(
    engine: Engine,
    username: str,
    password: str,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Authenticate credentials with timing-safe dummy verification and lockout."""
    uname = _normalize_username(username)
    generic_msg = "Tên đăng nhập hoặc mật khẩu không đúng."

    if not uname or not password:
        verify_password(password or "", _DUMMY_PASSWORD_HASH)
        record_auth_event(
            engine,
            event_type="login_failed",
            username_attempted=uname or None,
            detail={"reason": "empty_credentials"},
            client_ip=client_ip,
        )
        raise InvalidCredentialsError(generic_msg)

    pending_error: Exception | None = None
    result_user: dict[str, Any] | None = None

    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                f"SELECT {_SAFE_USER_COLUMNS}, password_hash "
                "FROM iam.app_user WHERE lower(username) = :uname"
            ),
            {"uname": uname},
        ).fetchone()

        if row is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            _insert_auth_event(
                conn,
                event_type="login_failed",
                username_attempted=uname,
                detail={"reason": "user_not_found"},
                client_ip=client_ip,
            )
            pending_error = InvalidCredentialsError(generic_msg)
        else:
            data = row._mapping
            user_id = data["user_id"]
            now = _utc_now()

            if not data["is_active"]:
                verify_password(password, data["password_hash"])
                _insert_auth_event(
                    conn,
                    event_type="login_failed",
                    user_id=user_id,
                    username_attempted=uname,
                    detail={"reason": "account_disabled"},
                    client_ip=client_ip,
                )
                pending_error = InvalidCredentialsError(generic_msg)
            else:
                locked_until = _ensure_utc(data["locked_until"]) if data["locked_until"] is not None else None
                if locked_until is not None and locked_until > now:
                    _insert_auth_event(
                        conn,
                        event_type="login_failed",
                        user_id=user_id,
                        username_attempted=uname,
                        detail={"reason": "account_locked", "locked_until": locked_until.isoformat()},
                        client_ip=client_ip,
                    )
                    pending_error = AccountLockedError(
                        "Tài khoản đang bị tạm khoá do đăng nhập sai nhiều lần.",
                        locked_until=locked_until,
                    )
                else:
                    password_ok = verify_password(password, data["password_hash"])
                    if not password_ok:
                        # Reset prior counter if an earlier temporary lockout already expired.
                        prior_count = (
                            0
                            if (locked_until is not None and locked_until <= now)
                            else int(data["failed_login_count"])
                        )
                        new_count = prior_count + 1
                        new_locked_until = (
                            now + timedelta(minutes=LOCKOUT_MINUTES)
                            if new_count >= MAX_FAILED_LOGINS
                            else None
                        )

                        conn.execute(
                            sa.text(
                                "UPDATE iam.app_user "
                                "SET failed_login_count = :cnt, locked_until = :lu, updated_at = :now "
                                "WHERE user_id = :uid"
                            ),
                            {"cnt": new_count, "lu": new_locked_until, "now": now, "uid": user_id},
                        )
                        _insert_auth_event(
                            conn,
                            event_type="login_failed",
                            user_id=user_id,
                            username_attempted=uname,
                            detail={"failed_login_count": new_count},
                            client_ip=client_ip,
                        )
                        if new_locked_until is not None:
                            _insert_auth_event(
                                conn,
                                event_type="account_locked",
                                user_id=user_id,
                                username_attempted=uname,
                                detail={
                                    "failed_login_count": new_count,
                                    "locked_until": new_locked_until.isoformat(),
                                },
                                client_ip=client_ip,
                            )
                        pending_error = InvalidCredentialsError(generic_msg)
                    else:
                        upgraded_hash = (
                            hash_password(password)
                            if _PASSWORD_HASHER.check_needs_rehash(data["password_hash"])
                            else None
                        )
                        if upgraded_hash is not None:
                            updated_row = conn.execute(
                                sa.text(
                                    "UPDATE iam.app_user "
                                    "SET failed_login_count = 0, locked_until = NULL, last_login_at = :now, "
                                    "    password_hash = :ph, updated_at = :now "
                                    "WHERE user_id = :uid "
                                    f"RETURNING {_SAFE_USER_COLUMNS}"
                                ),
                                {"now": now, "ph": upgraded_hash, "uid": user_id},
                            ).fetchone()
                        else:
                            updated_row = conn.execute(
                                sa.text(
                                    "UPDATE iam.app_user "
                                    "SET failed_login_count = 0, locked_until = NULL, last_login_at = :now, "
                                    "    updated_at = :now "
                                    "WHERE user_id = :uid "
                                    f"RETURNING {_SAFE_USER_COLUMNS}"
                                ),
                                {"now": now, "uid": user_id},
                            ).fetchone()

                        _insert_auth_event(
                            conn,
                            event_type="login_success",
                            user_id=user_id,
                            username_attempted=uname,
                            client_ip=client_ip,
                        )
                        result_user = _row_to_user_dict(updated_row)

    if pending_error is not None:
        raise pending_error
    assert result_user is not None
    return result_user


def create_session(
    engine: Engine,
    user_id: str,
    client_ip: str | None = None,
    user_agent: str | None = None,
    ttl_hours: int = SESSION_TTL_HOURS,
) -> tuple[str, dict[str, Any]]:
    """Create a stateful session returning (raw_token, session_record)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    now = _utc_now()
    expires_at = now + timedelta(hours=ttl_hours)

    with engine.begin() as conn:
        # Mark expired open sessions as revoked rather than DELETE (gml_ai_app has no DELETE grant).
        conn.execute(
            sa.text(
                "UPDATE iam.user_session "
                "SET revoked_at = :now, revoked_reason = 'session_expired' "
                "WHERE revoked_at IS NULL AND expires_at <= :now"
            ),
            {"now": now},
        )
        row = conn.execute(
            sa.text(
                "INSERT INTO iam.user_session "
                "(token_hash, user_id, created_at, expires_at, last_seen_at, client_ip, user_agent) "
                "VALUES (:th, :uid, :now, :exp, :now, :ip, :ua) "
                "RETURNING id, user_id, created_at, expires_at, last_seen_at, client_ip, user_agent"
            ),
            {
                "th": token_hash,
                "uid": user_id,
                "now": now,
                "exp": expires_at,
                "ip": client_ip[:64] if client_ip else None,
                "ua": user_agent[:300] if user_agent else None,
            },
        ).fetchone()

    m = row._mapping
    session_record = {
        "session_id": int(m["id"]),
        "id": int(m["id"]),
        "user_id": m["user_id"],
        "created_at": m["created_at"],
        "expires_at": m["expires_at"],
        "last_seen_at": m["last_seen_at"],
        "client_ip": m["client_ip"],
        "user_agent": m["user_agent"],
    }
    return raw_token, session_record


def verify_session_token(
    engine: Engine,
    raw_token: str,
    now: datetime | None = None,
    idle_hours: int = SESSION_IDLE_HOURS,
) -> dict[str, Any] | None:
    """Validate a raw bearer token against iam.user_session + iam.app_user."""
    if not raw_token or not raw_token.strip():
        return None

    cand_hash = hash_session_token(raw_token)
    current_time = _ensure_utc(now) if now is not None else _utc_now()

    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                "SELECT s.id AS session_id, s.token_hash, s.user_id, s.expires_at, "
                "       s.last_seen_at, s.revoked_at, "
                "       u.username, u.display_name, u.email, u.role, u.allowed_profiles, "
                "       u.is_active, u.must_change_password "
                "FROM iam.user_session s "
                "JOIN iam.app_user u ON u.user_id = s.user_id "
                "WHERE s.token_hash = :th"
            ),
            {"th": cand_hash},
        ).fetchone()

        if row is None:
            return None

        m = row._mapping
        if not hmac.compare_digest(cand_hash, str(m["token_hash"])):
            return None
        if m["revoked_at"] is not None or not bool(m["is_active"]):
            return None

        expires_at = _ensure_utc(m["expires_at"])
        last_seen_at = _ensure_utc(m["last_seen_at"])

        if expires_at <= current_time:
            conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = 'session_expired' "
                    "WHERE id = :sid AND revoked_at IS NULL"
                ),
                {"now": current_time, "sid": m["session_id"]},
            )
            _insert_auth_event(
                conn,
                event_type="session_expired",
                user_id=m["user_id"],
                detail={"session_id": int(m["session_id"]), "reason": "absolute_expiry"},
            )
            return None

        if last_seen_at + timedelta(hours=idle_hours) <= current_time:
            conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = 'idle_timeout' "
                    "WHERE id = :sid AND revoked_at IS NULL"
                ),
                {"now": current_time, "sid": m["session_id"]},
            )
            _insert_auth_event(
                conn,
                event_type="session_expired",
                user_id=m["user_id"],
                detail={"session_id": int(m["session_id"]), "reason": "idle_timeout"},
            )
            return None

        if (current_time - last_seen_at).total_seconds() >= LAST_SEEN_THROTTLE_SECONDS:
            conn.execute(
                sa.text("UPDATE iam.user_session SET last_seen_at = :now WHERE id = :sid"),
                {"now": current_time, "sid": m["session_id"]},
            )

        return {
            "user_id": m["user_id"],
            "username": m["username"],
            "display_name": m["display_name"],
            "email": m["email"],
            "role": m["role"],
            "allowed_profiles": list(m["allowed_profiles"] or []),
            "must_change_password": bool(m["must_change_password"]),
            "session_id": int(m["session_id"]),
            "expires_at": expires_at,
        }


def revoke_session(
    engine: Engine,
    raw_token: str | None = None,
    session_id: int | None = None,
    reason: str = "user_logout",
    actor_user_id: str | None = None,
    client_ip: str | None = None,
) -> bool:
    """Revoke a specific session by raw_token or session_id."""
    if raw_token is None and session_id is None:
        return False

    now = _utc_now()
    with engine.begin() as conn:
        if session_id is not None:
            row = conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = :reason, revoked_by = :actor "
                    "WHERE id = :sid AND revoked_at IS NULL "
                    "RETURNING id, user_id"
                ),
                {"now": now, "reason": reason[:50], "actor": actor_user_id, "sid": session_id},
            ).fetchone()
        else:
            token_hash = hash_session_token(raw_token or "")
            row = conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = :reason, revoked_by = :actor "
                    "WHERE token_hash = :th AND revoked_at IS NULL "
                    "RETURNING id, user_id"
                ),
                {"now": now, "reason": reason[:50], "actor": actor_user_id, "th": token_hash},
            ).fetchone()

        if row is None:
            return False

        m = row._mapping
        event_type = "logout" if reason == "user_logout" else "sessions_revoked"
        _insert_auth_event(
            conn,
            event_type=event_type,
            user_id=m["user_id"],
            actor_user_id=actor_user_id,
            detail={"session_id": int(m["id"]), "reason": reason},
            client_ip=client_ip,
        )
        return True


def change_user_password(
    engine: Engine,
    user_id: str,
    current_password: str,
    new_password: str,
    keep_session_id: int | None = None,
    client_ip: str | None = None,
) -> None:
    """Verify current password, enforce policy on new password, and revoke other sessions."""
    now = _utc_now()
    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                "SELECT user_id, username, email, password_hash "
                "FROM iam.app_user WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchone()
        if row is None:
            raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")

        m = row._mapping
        if not verify_password(current_password, m["password_hash"]):
            raise InvalidCredentialsError("Mật khẩu hiện tại không đúng.")

        validate_password_strength(new_password, username=m["username"], email=m["email"])
        new_hash = hash_password(new_password)

        conn.execute(
            sa.text(
                "UPDATE iam.app_user "
                "SET password_hash = :ph, must_change_password = FALSE, "
                "    password_changed_at = :now, updated_at = :now "
                "WHERE user_id = :uid"
            ),
            {"ph": new_hash, "now": now, "uid": user_id},
        )

        if keep_session_id is not None:
            conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = 'password_changed' "
                    "WHERE user_id = :uid AND revoked_at IS NULL AND id != :keep_sid"
                ),
                {"now": now, "uid": user_id, "keep_sid": keep_session_id},
            )
        else:
            conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = 'password_changed' "
                    "WHERE user_id = :uid AND revoked_at IS NULL"
                ),
                {"now": now, "uid": user_id},
            )

        _insert_auth_event(
            conn,
            event_type="password_changed",
            user_id=user_id,
            detail={"kept_session_id": keep_session_id},
            client_ip=client_ip,
        )


def create_user(
    engine: Engine,
    username: str,
    display_name: str,
    role: str,
    allowed_profiles: list[str] | None = None,
    email: str | None = None,
    password: str | None = None,
    must_change_password: bool = True,
    actor_user_id: str | None = None,
    client_ip: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Create a new internal IAM user and return (user_dict, plaintext_password)."""
    uname = _normalize_username(username)
    if not uname:
        raise IamError("Tên đăng nhập không được để trống.")
    dname = (display_name or "").strip()
    if not dname:
        raise IamError("Họ tên hiển thị không được để trống.")
    role_norm = _validate_role(role)
    profiles = _validate_profiles(allowed_profiles)
    email_norm = email.strip() if email and email.strip() else None

    if password is not None:
        validate_password_strength(password, username=uname, email=email_norm)
        plain_pw = password
    else:
        plain_pw = generate_temp_password(12)

    pw_hash = hash_password(plain_pw)
    user_id = f"u_{secrets.token_hex(4)}"

    try:
        with engine.begin() as conn:
            existing = conn.execute(
                sa.text("SELECT 1 FROM iam.app_user WHERE lower(username) = :uname"),
                {"uname": uname},
            ).scalar()
            if existing:
                raise UserConflictError(f"Tên đăng nhập '{uname}' đã tồn tại.")

            row = conn.execute(
                sa.text(
                    "INSERT INTO iam.app_user "
                    "(user_id, username, display_name, email, password_hash, role, "
                    " allowed_profiles, must_change_password, created_by) "
                    "VALUES (:uid, :uname, :dname, :email, :ph, :role, "
                    "        :profiles, :must_change, :created_by) "
                    f"RETURNING {_SAFE_USER_COLUMNS}"
                ),
                {
                    "uid": user_id,
                    "uname": uname,
                    "dname": dname,
                    "email": email_norm,
                    "ph": pw_hash,
                    "role": role_norm,
                    "profiles": profiles,
                    "must_change": bool(must_change_password),
                    "created_by": actor_user_id,
                },
            ).fetchone()

            _insert_auth_event(
                conn,
                event_type="user_created",
                user_id=user_id,
                actor_user_id=actor_user_id,
                detail={"username": uname, "role": role_norm, "allowed_profiles": profiles},
                client_ip=client_ip,
            )
            return _row_to_user_dict(row), plain_pw
    except IntegrityError as exc:
        raise UserConflictError(f"Tên đăng nhập '{uname}' đã tồn tại.") from exc


def get_user_by_id(engine: Engine, user_id: str) -> dict[str, Any]:
    """Fetch a single IAM user without password_hash."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(f"SELECT {_SAFE_USER_COLUMNS} FROM iam.app_user WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
    if row is None:
        raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")
    return _row_to_user_dict(row)


def list_users(
    engine: Engine,
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> list[dict[str, Any]]:
    """List IAM users filtered by search term, role, and active status."""
    clauses = ["1=1"]
    params: dict[str, Any] = {}

    if q and q.strip():
        clauses.append(
            "(username ILIKE :q OR display_name ILIKE :q OR COALESCE(email, '') ILIKE :q)"
        )
        params["q"] = f"%{q.strip()}%"
    if role and role.strip():
        clauses.append("role = :role")
        params["role"] = role.strip()
    if is_active is not None:
        clauses.append("is_active = :is_active")
        params["is_active"] = bool(is_active)

    where_sql = " AND ".join(clauses)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                f"SELECT {_SAFE_USER_COLUMNS} FROM iam.app_user "
                f"WHERE {where_sql} ORDER BY created_at ASC, username ASC"
            ),
            params,
        ).fetchall()
    return [_row_to_user_dict(r) for r in rows]


def update_user(
    engine: Engine,
    user_id: str,
    actor_user_id: str,
    display_name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    allowed_profiles: list[str] | None = None,
    is_active: bool | None = None,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Update user fields, enforce self-lockout & last-admin guards, and revoke sessions."""
    now = _utc_now()
    new_role = _validate_role(role) if role is not None else None
    new_profiles = _validate_profiles(allowed_profiles) if allowed_profiles is not None else None

    with engine.begin() as conn:
        row = conn.execute(
            sa.text(f"SELECT {_SAFE_USER_COLUMNS} FROM iam.app_user WHERE user_id = :uid FOR UPDATE"),
            {"uid": user_id},
        ).fetchone()
        if row is None:
            raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")

        cur = _row_to_user_dict(row)

        if user_id == actor_user_id:
            if is_active is False:
                raise SelfLockoutError("Không thể tự vô hiệu hoá tài khoản của chính mình.")
            if new_role is not None and new_role != cur["role"] and new_role != "quan_tri_he_thong":
                raise SelfLockoutError("Không thể tự hạ vai trò quản trị của chính mình.")

        leaves_admin_pool = (
            cur["role"] == "quan_tri_he_thong"
            and cur["is_active"]
            and (
                is_active is False
                or (new_role is not None and new_role != "quan_tri_he_thong")
            )
        )
        if leaves_admin_pool:
            other_admins = conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM iam.app_user "
                    "WHERE role = 'quan_tri_he_thong' AND is_active = TRUE AND user_id != :uid"
                ),
                {"uid": user_id},
            ).scalar()
            if int(other_admins or 0) == 0:
                raise LastAdminProtectedError(
                    "Hệ thống phải luôn có ít nhất một Quản trị hệ thống đang hoạt động."
                )

        final_display_name = display_name.strip() if display_name is not None else cur["display_name"]
        if not final_display_name:
            raise IamError("Họ tên hiển thị không được để trống.")
        final_email = (email.strip() or None) if email is not None else cur["email"]
        final_role = new_role if new_role is not None else cur["role"]
        final_profiles = new_profiles if new_profiles is not None else cur["allowed_profiles"]
        final_is_active = bool(is_active) if is_active is not None else cur["is_active"]

        updated_row = conn.execute(
            sa.text(
                "UPDATE iam.app_user "
                "SET display_name = :dname, email = :email, role = :role, "
                "    allowed_profiles = :profiles, is_active = :active, updated_at = :now "
                "WHERE user_id = :uid "
                f"RETURNING {_SAFE_USER_COLUMNS}"
            ),
            {
                "dname": final_display_name,
                "email": final_email,
                "role": final_role,
                "profiles": final_profiles,
                "active": final_is_active,
                "now": now,
                "uid": user_id,
            },
        ).fetchone()

        disabling = cur["is_active"] and not final_is_active
        enabling = not cur["is_active"] and final_is_active
        role_changed = final_role != cur["role"]
        old_prof_set = set(cur["allowed_profiles"])
        new_prof_set = set(final_profiles)
        profiles_shrunk = not old_prof_set.issubset(new_prof_set)
        profiles_changed = new_prof_set != old_prof_set

        revoke_reason: str | None = None
        if disabling:
            revoke_reason = "account_disabled"
        elif role_changed:
            revoke_reason = "role_changed"
        elif profiles_shrunk:
            revoke_reason = "profiles_changed"

        if revoke_reason is not None:
            conn.execute(
                sa.text(
                    "UPDATE iam.user_session "
                    "SET revoked_at = :now, revoked_reason = :reason, revoked_by = :actor "
                    "WHERE user_id = :uid AND revoked_at IS NULL"
                ),
                {"now": now, "reason": revoke_reason, "actor": actor_user_id, "uid": user_id},
            )

        emitted_specific = False
        if disabling:
            _insert_auth_event(
                conn,
                event_type="user_disabled",
                user_id=user_id,
                actor_user_id=actor_user_id,
                client_ip=client_ip,
            )
            emitted_specific = True
        elif enabling:
            _insert_auth_event(
                conn,
                event_type="user_enabled",
                user_id=user_id,
                actor_user_id=actor_user_id,
                client_ip=client_ip,
            )
            emitted_specific = True

        if role_changed:
            _insert_auth_event(
                conn,
                event_type="role_changed",
                user_id=user_id,
                actor_user_id=actor_user_id,
                detail={"old_role": cur["role"], "new_role": final_role},
                client_ip=client_ip,
            )
            emitted_specific = True

        if profiles_changed:
            _insert_auth_event(
                conn,
                event_type="profiles_changed",
                user_id=user_id,
                actor_user_id=actor_user_id,
                detail={"old_profiles": cur["allowed_profiles"], "new_profiles": final_profiles},
                client_ip=client_ip,
            )
            emitted_specific = True

        if not emitted_specific:
            _insert_auth_event(
                conn,
                event_type="user_updated",
                user_id=user_id,
                actor_user_id=actor_user_id,
                detail={"display_name": final_display_name, "email": final_email},
                client_ip=client_ip,
            )

        return _row_to_user_dict(updated_row)


def reset_password_by_admin(
    engine: Engine,
    user_id: str,
    actor_user_id: str,
    client_ip: str | None = None,
) -> str:
    """Reset a user's password to a 12-char temporary password and revoke sessions."""
    temp_pw = generate_temp_password(12)
    new_hash = hash_password(temp_pw)
    now = _utc_now()

    with engine.begin() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM iam.app_user WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        if not exists:
            raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")

        conn.execute(
            sa.text(
                "UPDATE iam.app_user "
                "SET password_hash = :ph, must_change_password = TRUE, "
                "    failed_login_count = 0, locked_until = NULL, "
                "    password_changed_at = :now, updated_at = :now "
                "WHERE user_id = :uid"
            ),
            {"ph": new_hash, "now": now, "uid": user_id},
        )
        conn.execute(
            sa.text(
                "UPDATE iam.user_session "
                "SET revoked_at = :now, revoked_reason = 'password_reset', revoked_by = :actor "
                "WHERE user_id = :uid AND revoked_at IS NULL"
            ),
            {"now": now, "actor": actor_user_id, "uid": user_id},
        )
        _insert_auth_event(
            conn,
            event_type="password_reset_by_admin",
            user_id=user_id,
            actor_user_id=actor_user_id,
            client_ip=client_ip,
        )

    return temp_pw


def unlock_user(
    engine: Engine,
    user_id: str,
    actor_user_id: str,
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Clear lockout state for a user after failed login attempts."""
    now = _utc_now()
    with engine.begin() as conn:
        row = conn.execute(
            sa.text(
                "UPDATE iam.app_user "
                "SET failed_login_count = 0, locked_until = NULL, updated_at = :now "
                "WHERE user_id = :uid "
                f"RETURNING {_SAFE_USER_COLUMNS}"
            ),
            {"now": now, "uid": user_id},
        ).fetchone()
        if row is None:
            raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")

        _insert_auth_event(
            conn,
            event_type="user_updated",
            user_id=user_id,
            actor_user_id=actor_user_id,
            detail={"action": "unlock"},
            client_ip=client_ip,
        )
        return _row_to_user_dict(row)


def revoke_user_sessions(
    engine: Engine,
    user_id: str,
    actor_user_id: str,
    reason: str = "admin_revoked",
    client_ip: str | None = None,
) -> int:
    """Immediately revoke all open sessions belonging to user_id."""
    now = _utc_now()
    with engine.begin() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM iam.app_user WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        if not exists:
            raise UserNotFoundError(f"Không tìm thấy người dùng '{user_id}'.")

        res = conn.execute(
            sa.text(
                "UPDATE iam.user_session "
                "SET revoked_at = :now, revoked_reason = :reason, revoked_by = :actor "
                "WHERE user_id = :uid AND revoked_at IS NULL"
            ),
            {"now": now, "reason": reason[:50], "actor": actor_user_id, "uid": user_id},
        )
        revoked_count = int(res.rowcount or 0)
        _insert_auth_event(
            conn,
            event_type="sessions_revoked",
            user_id=user_id,
            actor_user_id=actor_user_id,
            detail={"revoked_count": revoked_count, "reason": reason},
            client_ip=client_ip,
        )
        return revoked_count


def list_active_sessions(
    engine: Engine,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """List all currently active (non-revoked, non-expired) sessions."""
    now = _utc_now()
    clauses = ["s.revoked_at IS NULL", "s.expires_at > :now"]
    params: dict[str, Any] = {"now": now}
    if user_id:
        clauses.append("s.user_id = :uid")
        params["uid"] = user_id

    where_sql = " AND ".join(clauses)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT s.id AS session_id, s.user_id, u.username, u.display_name, u.role, "
                "       s.created_at, s.expires_at, s.last_seen_at, s.client_ip, s.user_agent "
                "FROM iam.user_session s "
                "JOIN iam.app_user u ON u.user_id = s.user_id "
                f"WHERE {where_sql} "
                "ORDER BY s.last_seen_at DESC, s.id DESC"
            ),
            params,
        ).fetchall()

    return [
        {
            "session_id": int(r._mapping["session_id"]),
            "user_id": r._mapping["user_id"],
            "username": r._mapping["username"],
            "display_name": r._mapping["display_name"],
            "role": r._mapping["role"],
            "created_at": r._mapping["created_at"],
            "expires_at": r._mapping["expires_at"],
            "last_seen_at": r._mapping["last_seen_at"],
            "client_ip": r._mapping["client_ip"],
            "user_agent": r._mapping["user_agent"],
        }
        for r in rows
    ]


def list_auth_events(
    engine: Engine,
    user_id: str | None = None,
    event_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List authentication & admin events filtered by user, type, and date range."""
    clauses = ["1=1"]
    params: dict[str, Any] = {"limit": max(1, min(int(limit), 1000))}

    if user_id and user_id.strip():
        clauses.append("(user_id = :uid OR actor_user_id = :uid)")
        params["uid"] = user_id.strip()
    if event_type and event_type.strip():
        clauses.append("event_type = :event_type")
        params["event_type"] = event_type.strip()
    if date_from is not None:
        clauses.append("created_at >= :date_from")
        params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
    if date_to is not None:
        next_day = date_to + timedelta(days=1)
        clauses.append("created_at < :date_to_excl")
        params["date_to_excl"] = datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)

    where_sql = " AND ".join(clauses)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT id, event_type, user_id, username_attempted, actor_user_id, "
                "       detail, client_ip, created_at "
                f"FROM iam.auth_event WHERE {where_sql} "
                "ORDER BY created_at DESC, id DESC LIMIT :limit"
            ),
            params,
        ).fetchall()

    return [
        {
            "id": int(r._mapping["id"]),
            "event_type": r._mapping["event_type"],
            "user_id": r._mapping["user_id"],
            "username_attempted": r._mapping["username_attempted"],
            "actor_user_id": r._mapping["actor_user_id"],
            "detail": r._mapping["detail"],
            "client_ip": r._mapping["client_ip"],
            "created_at": r._mapping["created_at"],
        }
        for r in rows
    ]


_DEFAULT_DEMO_ACCOUNTS: tuple[dict[str, Any], ...] = (
    {
        "user_id": "usr_ceo",
        "username": "demo.ceo",
        "display_name": "Nguyễn Văn A (CEO)",
        "email": "ceo@gominhlong.local",
        "role": "ceo",
        "allowed_profiles": ["real", "synth"],
    },
    {
        "user_id": "usr_ktt",
        "username": "demo.ktt",
        "display_name": "Trần Thị B (Kế toán trưởng)",
        "email": "ktt@gominhlong.local",
        "role": "ke_toan_truong",
        "allowed_profiles": ["real", "synth"],
    },
    {
        "user_id": "usr_kho",
        "username": "demo.kho",
        "display_name": "Lê Văn C (Quản lý kho)",
        "email": "kho@gominhlong.local",
        "role": "quan_ly_kho",
        "allowed_profiles": ["real", "synth"],
    },
    {
        "user_id": "usr_admin",
        "username": "demo.admin",
        "display_name": "Quản trị hệ thống",
        "email": "admin@gominhlong.local",
        "role": "quan_tri_he_thong",
        "allowed_profiles": ["real", "synth"],
    },
)


def seed_default_demo_users(
    engine: Engine,
    demo_password: str = "DemoPass@2026",
) -> list[dict[str, Any]]:
    """Idempotently ensure the 4 dev demo accounts exist with legacy user_ids."""
    validate_password_strength(demo_password)
    pw_hash = hash_password(demo_password)
    now = _utc_now()

    with engine.begin() as conn:
        for spec in _DEFAULT_DEMO_ACCOUNTS:
            existing = conn.execute(
                sa.text(
                    "SELECT user_id FROM iam.app_user "
                    "WHERE user_id = :uid OR lower(username) = :uname"
                ),
                {"uid": spec["user_id"], "uname": spec["username"]},
            ).fetchone()
            if existing is None:
                conn.execute(
                    sa.text(
                        "INSERT INTO iam.app_user "
                        "(user_id, username, display_name, email, password_hash, role, "
                        " allowed_profiles, is_active, must_change_password, password_changed_at) "
                        "VALUES (:uid, :uname, :dname, :email, :ph, :role, "
                        "        :profiles, TRUE, FALSE, :now)"
                    ),
                    {
                        "uid": spec["user_id"],
                        "uname": spec["username"],
                        "dname": spec["display_name"],
                        "email": spec["email"],
                        "ph": pw_hash,
                        "role": spec["role"],
                        "profiles": spec["allowed_profiles"],
                        "now": now,
                    },
                )

        rows = conn.execute(
            sa.text(
                f"SELECT {_SAFE_USER_COLUMNS} FROM iam.app_user "
                "WHERE user_id IN ('usr_ceo', 'usr_ktt', 'usr_kho', 'usr_admin') "
                "ORDER BY user_id ASC"
            )
        ).fetchall()
    return [_row_to_user_dict(r) for r in rows]
