"""Integration tests for Migration 003 (IAM schema) and iam_service (Task 1).

Specifications:
- Spec §5.2, §5.3
- Plan Task 1
"""

from datetime import datetime, timedelta, timezone
import pytest
import sqlalchemy as sa

from app.core.config import get_settings
from db.apply_db import apply_all, get_admin_engine, get_iam_engine, get_ro_engine
from app.services import iam_service
from app.services.iam_service import (
    AccountLockedError,
    InvalidCredentialsError,
    LastAdminProtectedError,
    PasswordPolicyError,
    SelfLockoutError,
    UserConflictError,
    _DUMMY_PASSWORD_HASH,
    authenticate_user,
    change_user_password,
    create_session,
    create_user,
    generate_temp_password,
    get_user_by_id,
    hash_password,
    hash_session_token,
    list_active_sessions,
    list_auth_events,
    list_users,
    reset_password_by_admin,
    revoke_session,
    revoke_user_sessions,
    seed_default_demo_users,
    unlock_user,
    update_user,
    validate_password_strength,
    verify_password,
    verify_session_token,
)


TEST_USERNAMES = (
    "t1_user_a",
    "t1_user_b",
    "t1_admin_1",
    "t1_admin_2",
    "t1_locked",
    "t1_disabled",
    "demo.ceo",
    "demo.ktt",
    "demo.kho",
    "demo.admin",
)


@pytest.fixture
def iam_eng():
    return get_iam_engine()


@pytest.fixture
def clean_iam_test_users():
    """Remove test IAM users, sessions, and auth_events before and after tests."""
    def _clean():
        try:
            admin_eng = get_admin_engine(profile="real")
            with admin_eng.begin() as conn:
                conn.execute(
                    sa.text(
                        "DELETE FROM iam.user_session WHERE user_id IN ("
                        "  SELECT user_id FROM iam.app_user WHERE lower(username) = ANY(:names)"
                        ")"
                    ),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text(
                        "DELETE FROM iam.auth_event WHERE lower(coalesce(username_attempted, '')) = ANY(:names) "
                        "OR user_id IN (SELECT user_id FROM iam.app_user WHERE lower(username) = ANY(:names)) "
                        "OR user_id IN ('usr_ceo', 'usr_ktt', 'usr_kho', 'usr_admin')"
                    ),
                    {"names": list(TEST_USERNAMES)},
                )
                conn.execute(
                    sa.text("DELETE FROM iam.app_user WHERE lower(username) = ANY(:names)"),
                    {"names": list(TEST_USERNAMES)},
                )
        except Exception:
            pass

    _clean()
    yield
    _clean()


def test_migration_003_creates_iam_tables_and_blocks_ro_role(monkeypatch):
    settings = get_settings()
    apply_all(admin_uri=settings.get_admin_uri(profile="real"))
    apply_all(admin_uri=settings.get_admin_uri(profile="real"))  # idempotency check

    iam_eng = get_iam_engine()
    with iam_eng.connect() as conn:
        tbls = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'iam'")
            ).fetchall()
        }
        assert {"app_user", "user_session", "auth_event"} <= tbls

    # Even if DATA_PROFILE=synth, get_iam_engine() stays pinned to real (data_warehouse)
    monkeypatch.setenv("DATA_PROFILE", "synth")
    get_settings.cache_clear()
    try:
        synth_mode_iam_eng = get_iam_engine()
        assert synth_mode_iam_eng.url.database == "data_warehouse"
    finally:
        get_settings.cache_clear()

    # gml_ai_ro must have ZERO access to iam.*
    ro_eng = get_ro_engine(profile="real")
    for stmt in (
        "SELECT count(*) FROM iam.app_user",
        "SELECT count(*) FROM iam.user_session",
        "SELECT count(*) FROM iam.auth_event",
    ):
        with pytest.raises(sa.exc.ProgrammingError):
            with ro_eng.connect() as conn:
                conn.execute(sa.text(stmt))


def test_password_policy_and_dummy_timing_defense(iam_eng, clean_iam_test_users, monkeypatch):
    # Length < 10 or > 128 rejected
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("short1")
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("a1" * 65)

    # Must contain letter AND digit
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("OnlyLettersHere")
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("123456789012")

    # Blocklist terms (case-insensitive)
    for bad in ("MinhLong2026!", "GoMinhLong99", "MyPassword12", "1234567890ab", "Qwerty12345z"):
        with pytest.raises(PasswordPolicyError):
            validate_password_strength(bad)

    # Username & email local-part rejected
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("My_nva.ceo_99", username="nva.ceo")
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("TranThiB2026", email="tranthib@gominhlong.vn")

    # Valid passphrase with spaces accepted
    validate_password_strength("GoWood Safe Pass 2026", username="nva.ceo")

    hashed = hash_password("SecurePass99")
    assert hashed.startswith("$argon2id$")
    assert verify_password("SecurePass99", hashed) is True
    assert verify_password("WrongPass99", hashed) is False

    # Temp password satisfies policy
    temp_pw = generate_temp_password()
    assert len(temp_pw) == 12
    validate_password_strength(temp_pw)

    # Token hash is 64-char SHA-256 hex
    th = hash_session_token("raw-secret-token")
    assert len(th) == 64

    # Dummy timing defense: verify_password is ALWAYS called with _DUMMY_PASSWORD_HASH when user missing
    calls: list[tuple[str, str]] = []
    orig_verify = iam_service.verify_password

    def spy_verify(plain: str, h: str) -> bool:
        calls.append((plain, h))
        return orig_verify(plain, h)

    monkeypatch.setattr(iam_service, "verify_password", spy_verify)
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(iam_eng, "nonexistent_user_xyz", "SomePass1234", client_ip="127.0.0.1")
    assert len(calls) == 1
    assert calls[0][1] == _DUMMY_PASSWORD_HASH

    # Disabled account still checks password and returns generic InvalidCredentialsError
    user_disabled, pw = create_user(
        iam_eng,
        username="t1_disabled",
        display_name="Disabled User",
        role="quan_ly_kho",
        password="ValidUser99!",
        must_change_password=False,
    )
    with get_admin_engine(profile="real").begin() as conn:
        conn.execute(
            sa.text("UPDATE iam.app_user SET is_active = FALSE WHERE user_id = :uid"),
            {"uid": user_disabled["user_id"]},
        )
    calls.clear()
    with pytest.raises(InvalidCredentialsError):
        authenticate_user(iam_eng, "t1_disabled", pw, client_ip="127.0.0.1")
    assert len(calls) == 1


def test_lockout_after_5_failures_and_admin_unlock(iam_eng, clean_iam_test_users):
    user, pw = create_user(
        iam_eng,
        username="t1_locked",
        display_name="Locked Test",
        role="ke_toan_truong",
        password="StrongPass88!",
        must_change_password=False,
    )
    admin, _ = create_user(
        iam_eng,
        username="t1_admin_1",
        display_name="Admin One",
        role="quan_tri_he_thong",
        password="AdminStrong88!",
        must_change_password=False,
    )

    for _ in range(5):
        with pytest.raises(InvalidCredentialsError):
            authenticate_user(iam_eng, "t1_locked", "WrongPassword99", client_ip="10.0.0.5")

    # 6th attempt even with right password raises AccountLockedError with locked_until
    with pytest.raises(AccountLockedError) as exc_info:
        authenticate_user(iam_eng, "t1_locked", pw, client_ip="10.0.0.5")
    assert exc_info.value.locked_until > datetime.now(timezone.utc)

    # account_locked event recorded
    events = list_auth_events(iam_eng, user_id=user["user_id"], event_type="account_locked")
    assert len(events) >= 1

    # Admin unlocks user -> login succeeds and resets failed_login_count
    unlocked = unlock_user(iam_eng, user["user_id"], actor_user_id=admin["user_id"], client_ip="10.0.0.1")
    assert unlocked["failed_login_count"] == 0
    assert unlocked["locked_until"] is None

    authed = authenticate_user(iam_eng, "T1_LOCKED", pw, client_ip="10.0.0.5")
    assert authed["user_id"] == user["user_id"]
    assert "password_hash" not in authed
    assert authed["failed_login_count"] == 0


def test_session_idle_and_absolute_expiry_and_immediate_revoke(iam_eng, clean_iam_test_users):
    user, pw = create_user(
        iam_eng,
        username="t1_user_a",
        display_name="User A",
        role="ceo",
        password="UserAStrong99!",
        must_change_password=True,
    )
    raw_tok, sess = create_session(
        iam_eng,
        user_id=user["user_id"],
        client_ip="10.1.1.1",
        user_agent="pytest-agent",
        ttl_hours=12,
    )
    assert "token" not in sess and "token_hash" not in sess
    base_time = sess["created_at"]

    # Immediate check (<60s) valid and does not break
    principal = verify_session_token(iam_eng, raw_tok, now=base_time + timedelta(seconds=30))
    assert principal is not None
    assert principal["user_id"] == user["user_id"]
    assert principal["role"] == "ceo"
    assert principal["must_change_password"] is True

    # After 2 minutes (>= 60s), last_seen_at is updated
    t_seen = base_time + timedelta(minutes=2)
    principal2 = verify_session_token(iam_eng, raw_tok, now=t_seen)
    assert principal2 is not None
    active = list_active_sessions(iam_eng, user_id=user["user_id"])
    assert len(active) == 1
    assert abs((active[0]["last_seen_at"] - t_seen).total_seconds()) < 2

    # Idle timeout after 2h01m since last_seen_at
    assert verify_session_token(iam_eng, raw_tok, now=t_seen + timedelta(hours=2, minutes=1)) is None
    idle_events = list_auth_events(iam_eng, user_id=user["user_id"], event_type="session_expired")
    assert len(idle_events) >= 1

    # Unrevoked session with last_seen_at > 2h ago must be excluded from list_active_sessions
    _, idle_sess = create_session(iam_eng, user_id=user["user_id"], ttl_hours=12)
    with get_admin_engine(profile="real").begin() as conn:
        conn.execute(
            sa.text("UPDATE iam.user_session SET last_seen_at = :old WHERE id = :sid"),
            {"old": datetime.now(timezone.utc) - timedelta(hours=2, minutes=5), "sid": idle_sess["session_id"]},
        )
    active_ids = {s["session_id"] for s in list_active_sessions(iam_eng, user_id=user["user_id"])}
    assert idle_sess["session_id"] not in active_ids

    # Absolute expiry (12h) even if last_seen_at kept fresh via periodic activity
    raw_tok2, sess2 = create_session(iam_eng, user_id=user["user_id"], ttl_hours=12)
    t2_base = sess2["created_at"]
    for h in range(1, 12):
        assert verify_session_token(iam_eng, raw_tok2, now=t2_base + timedelta(hours=h, minutes=30)) is not None
    assert verify_session_token(iam_eng, raw_tok2, now=t2_base + timedelta(hours=12, minutes=1)) is None

    # Change password keeps current session and revokes other open sessions
    raw_keep, sess_keep = create_session(iam_eng, user_id=user["user_id"])
    raw_other, _ = create_session(iam_eng, user_id=user["user_id"])
    change_user_password(
        iam_eng,
        user_id=user["user_id"],
        current_password=pw,
        new_password="UserANewPass99!",
        keep_session_id=sess_keep["session_id"],
    )
    assert verify_session_token(iam_eng, raw_keep) is not None
    assert verify_session_token(iam_eng, raw_other) is None
    updated_user = get_user_by_id(iam_eng, user["user_id"])
    assert updated_user["must_change_password"] is False

    # Immediate logout revocation
    assert revoke_session(iam_eng, raw_token=raw_keep, reason="user_logout") is True
    assert verify_session_token(iam_eng, raw_keep) is None


def test_admin_cannot_self_disable_or_remove_last_admin(iam_eng, clean_iam_test_users):
    admin1, _ = create_user(
        iam_eng,
        username="t1_admin_1",
        display_name="Admin 1",
        role="quan_tri_he_thong",
        password="AdminOne99!",
        must_change_password=False,
    )
    admin2, _ = create_user(
        iam_eng,
        username="t1_admin_2",
        display_name="Admin 2",
        role="quan_tri_he_thong",
        password="AdminTwo99!",
        must_change_password=False,
    )

    # Duplicate username conflict
    with pytest.raises(UserConflictError):
        create_user(
            iam_eng,
            username="T1_ADMIN_1",
            display_name="Dup",
            role="ceo",
            password="DupUserPass99!",
        )

    # Admin cannot self-disable or self-demote
    with pytest.raises(SelfLockoutError):
        update_user(iam_eng, admin1["user_id"], actor_user_id=admin1["user_id"], is_active=False)
    with pytest.raises(SelfLockoutError):
        update_user(iam_eng, admin1["user_id"], actor_user_id=admin1["user_id"], role="ceo")

    # Admin1 can disable Admin2 (leaving Admin1 as active admin)
    raw_a2_tok, _ = create_session(iam_eng, admin2["user_id"])
    disabled_a2 = update_user(iam_eng, admin2["user_id"], actor_user_id=admin1["user_id"], is_active=False)
    assert disabled_a2["is_active"] is False
    # Session of disabled user is revoked immediately
    assert verify_session_token(iam_eng, raw_a2_tok) is None

    # Now Admin1 is the ONLY active admin — Admin2 (or another actor) cannot disable or demote Admin1
    with pytest.raises(LastAdminProtectedError):
        update_user(iam_eng, admin1["user_id"], actor_user_id=admin2["user_id"], is_active=False)
    with pytest.raises(LastAdminProtectedError):
        update_user(iam_eng, admin1["user_id"], actor_user_id=admin2["user_id"], role="ceo")

    # Role change and profile shrink revoke active sessions immediately
    user_b, _ = create_user(
        iam_eng,
        username="t1_user_b",
        display_name="User B",
        role="ke_toan_truong",
        allowed_profiles=["real", "synth"],
        password="UserBStrong99!",
        must_change_password=False,
    )
    tok_b1, _ = create_session(iam_eng, user_b["user_id"])
    update_user(iam_eng, user_b["user_id"], actor_user_id=admin1["user_id"], allowed_profiles=["real"])
    assert verify_session_token(iam_eng, tok_b1) is None

    tok_b2, _ = create_session(iam_eng, user_b["user_id"])
    update_user(iam_eng, user_b["user_id"], actor_user_id=admin1["user_id"], role="quan_ly_kho")
    assert verify_session_token(iam_eng, tok_b2) is None

    # Admin reset password sets must_change_password=True and revokes sessions
    tok_b3, _ = create_session(iam_eng, user_b["user_id"])
    new_temp = reset_password_by_admin(iam_eng, user_b["user_id"], actor_user_id=admin1["user_id"])
    assert len(new_temp) >= 10
    assert verify_session_token(iam_eng, tok_b3) is None
    assert get_user_by_id(iam_eng, user_b["user_id"])["must_change_password"] is True

    # Revoke all user sessions helper
    create_session(iam_eng, user_b["user_id"])
    create_session(iam_eng, user_b["user_id"])
    revoked_cnt = revoke_user_sessions(iam_eng, user_b["user_id"], actor_user_id=admin1["user_id"])
    assert revoked_cnt == 2

    # list_users never exposes password_hash
    users = list_users(iam_eng, q="t1_user_b")
    assert len(users) == 1
    assert "password_hash" not in users[0]


def test_seed_default_demo_users_idempotent(iam_eng, clean_iam_test_users):
    seeded1 = seed_default_demo_users(iam_eng)
    seeded2 = seed_default_demo_users(iam_eng)
    assert len(seeded1) == 4
    assert len(seeded2) == 4
    by_id = {u["user_id"]: u for u in seeded2}
    assert set(by_id.keys()) == {"usr_ceo", "usr_ktt", "usr_kho", "usr_admin"}
    assert by_id["usr_ceo"]["username"] == "demo.ceo"
    assert by_id["usr_ktt"]["username"] == "demo.ktt"
    assert by_id["usr_kho"]["username"] == "demo.kho"
    assert by_id["usr_admin"]["username"] == "demo.admin"
