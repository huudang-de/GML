# Credential Login, Internal IAM Database & Admin Control Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the client-side role switcher with real username/password authentication backed by PostgreSQL (`iam` schema), stateful SHA-256 session tokens with F5 cookie persistence, strict Admin/Business separation, admin-only monthly simulation execution, and full auditability.

**Architecture:** All identity state lives in a single PostgreSQL schema `iam` inside the primary `real` database (`data_warehouse`), shared across both `real` and `synth` profiles. `TokenAuthVerifier` preserves the `Authorization: Bearer <token>` contract by validating non-prod static/service tokens first and then checking hashed opaque session tokens in `iam.user_session`, while Streamlit renders a dedicated login/password-change gate before entering either the 4-tab Admin Panel (`quan_tri_he_thong`) or business dashboards.

**Tech Stack:** PostgreSQL (`iam` schema), `argon2-cffi 25.1.0`, `PyJWT`/`secrets` + `hmac`, FastAPI, Pydantic v2, Streamlit `1.55.0` (`st.context.cookies` + lightweight cookie helper), pytest.

**Spec:** [2026-11-18-v2-login-iam-admin-design.md](file:///D:/C%C3%B4ng%20vi%E1%BB%87c/1.%20D%E1%BB%B1%20%C3%A1n%20G%E1%BB%97%20Minh%20Long/7.%20AI-Business-Assistant/docs/superpowers/specs/2026-11-18-v2-login-iam-admin-design.md)

## Global Constraints

- **No self-escalation:** Interactive web UI removes the role dropdown completely and ignores `?role=` in URL query params once real login mode is active (`set_require_login_for_testing(False)` remains strictly an opt-in in-process `AppTest` testing hook matching `set_default_transport_for_testing`).
- **Zero raw secrets stored or logged:** Never store or log plaintext passwords, `password_hash`, or raw session `access_token` in PostgreSQL (`iam.user_session` stores `CHAR(64)` SHA-256 hex digest only), API responses, `iam.auth_event.detail`, or `app.audit_log`.
- **Single IAM source of truth:** `get_iam_engine()` always connects to the `real` (`data_warehouse`) DB regardless of active `profile`; `gml_ai_ro` gets **zero** privileges on `iam.*`.
- **Admin vs Business separation:** `quan_tri_he_thong` holds 0 AI views, sees ONLY the 4-tab Admin Panel (Users, Active Sessions, Monthly Simulation Runner, Auth Events), and cannot access financial KPIs/chat; business roles (`ceo`, `ke_toan_truong`, `quan_ly_kho`) receive `403 FORBIDDEN` on `/v1/admin/*` (including `/v1/admin/simulation/run`).
- **Profile gating:** Business accounts default to `allowed_profiles = ['real', 'synth']` (to view monthly forecast/simulation results alongside live data); any request targeting a profile outside `user.allowed_profiles` returns `403 PROFILE_FORBIDDEN`.
- **UI architectural boundary:** `v2/app/ui/**` MUST NEVER import `app.services`, `app.agents`, `app.knowledge`, or `db` (verified by `test_ui_does_not_import_server_layers`).
- **Backward compatibility:** Preserve existing Bearer token behavior for non-prod dev tokens (`app_env != "production"`) and `auth_tokens_json` so all 278 existing tests continue passing. Additive changes only in `v2/docs/openapi.json`. Restore `v2/eval/reports/t1_permissions.txt` via `git checkout --` after full `pytest` runs.

## Review Focus

1. **Timing-safe login enumeration:** Unknown `username` MUST execute a real dummy Argon2id check (`_DUMMY_PASSWORD_HASH`) and return the exact generic HTTP 401 `INVALID_CREDENTIALS` message (`"Tên đăng nhập hoặc mật khẩu không đúng."`) identical to wrong-password and disabled-account failures.
2. **Immediate revocation & self-lockout protection:** Disabling an account, changing its role, narrowing `allowed_profiles`, or clicking "Thu hồi phiên" MUST revoke matching rows in `iam.user_session` immediately so the very next API request fails with `401`. Admins cannot disable/demote themselves or leave zero active admins (`409` / `422`).
3. **`must_change_password` bypass & logout loophole:** A user with `must_change_password = True` MUST be blocked (`403 PASSWORD_CHANGE_REQUIRED`) on all business/admin endpoints (`/v1/kpi/*`, `/v1/overview`, `/v1/chat`, `/v1/admin/*`, etc.), while STILL allowed to call `/v1/auth/me`, `/v1/auth/change-password`, and `/v1/auth/logout`.
4. **F5 cookie hydration vs `401`/stale cookie loop:** If the `gml_session` cookie contains an expired or revoked token on page load/F5, `GET /v1/auth/me` returns `401` -> UI MUST clear the stale cookie + session state cleanly and show `"Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."` without infinite rerun loops, while preserving original Quick Ask params (`?dashboard=...&kpi=...&screen=...`) across login.
5. **Cross-profile chat & header leakage:** `POST /v1/chat` reads `payload.data_profile` directly (not `resolve_profile` query dependency), so it MUST enforce `allowed_profiles`; and `POST /v1/admin/simulation/run` MUST reject non-admin roles with `403 FORBIDDEN` and clear KPI cache after regenerating `gml_synth`.

---

### Task 1: IAM Schema Migration (`003_iam_users_sessions.sql`), `get_iam_engine`, and `iam_service.py`

**Files:**
- Create: `v2/db/migrations/003_iam_users_sessions.sql`, `v2/app/services/iam_service.py`
- Modify: `v2/db/apply_db.py:85-95`
- Test: `v2/tests/integration/test_iam_service_and_migration.py`

**Interfaces:**
- Consumes: `db/apply_db.py:get_app_engine`, `app/core/config.py:Settings`, `argon2.PasswordHasher`, `secrets`, `hashlib`, `hmac`.
- Produces in `v2/db/apply_db.py`:
  - `get_iam_engine(app_uri: str | None = None) -> Engine`: always connects to `settings.get_app_uri(profile="real")` (single source of truth on `data_warehouse`).
- Produces in `v2/app/services/iam_service.py`:
  - Exceptions: `class IamError(Exception)`, `class InvalidCredentialsError(IamError)`, `class AccountLockedError(IamError)` (carries `locked_until: datetime`), `class PasswordPolicyError(IamError)`, `class UserConflictError(IamError)`, `class UserNotFoundError(IamError)`, `class SelfLockoutError(IamError)`, `class LastAdminProtectedError(IamError)`.
  - Password helpers:
    - `hash_password(plain: str) -> str` (Argon2id via `PasswordHasher(memory_cost=19456, time_cost=2, parallelism=1)`)
    - `verify_password(plain: str, hashed: str) -> bool` (constant-time via Argon2 `verify`, never raises on mismatch)
    - `validate_password_strength(password: str, username: str | None = None, email: str | None = None) -> None` (10–128 UTF-8 chars, contains letter + digit, not containing `username`/`email` local-part or blocklist `{"minhlong", "gominhlong", "password", "1234567890", "qwerty12345"}`; raises `PasswordPolicyError`)
    - `generate_temp_password(length: int = 12) -> str`
    - `hash_session_token(raw_token: str) -> str` (SHA-256 hex)
  - Auth & Session lifecycle:
    - `authenticate_user(engine: Engine, username: str, password: str, client_ip: str | None = None) -> dict` (runs dummy Argon2 check when user missing; enforces lockout `5` failures -> `15` min `locked_until`; resets counter on success; writes `iam.auth_event`)
    - `create_session(engine: Engine, user_id: str, client_ip: str | None = None, user_agent: str | None = None, ttl_hours: int = 12) -> tuple[str, dict]` (returns `(raw_token, session_record)`, prunes expired sessions)
    - `verify_session_token(engine: Engine, raw_token: str, now: datetime | None = None, idle_hours: int = 2) -> dict | None` (checks `revoked_at IS NULL`, `expires_at > now`, `last_seen_at + 2h > now` else marks `revoked_reason='idle_timeout'`, `app_user.is_active = TRUE`; throttles `last_seen_at` UPDATE to `>= 60s` delta)
    - `revoke_session(engine: Engine, raw_token: str | None = None, session_id: int | None = None, reason: str = "user_logout", actor_user_id: str | None = None, client_ip: str | None = None) -> bool`
    - `change_user_password(engine: Engine, user_id: str, current_password: str, new_password: str, keep_session_id: int | None = None, client_ip: str | None = None) -> None`
  - Admin user & log operations:
    - `create_user(engine: Engine, username: str, display_name: str, role: str, allowed_profiles: list[str] | None = None, email: str | None = None, password: str | None = None, must_change_password: bool = True, actor_user_id: str | None = None, client_ip: str | None = None) -> tuple[dict, str]`
    - `get_user_by_id(engine: Engine, user_id: str) -> dict`
    - `list_users(engine: Engine, q: str | None = None, role: str | None = None, is_active: bool | None = None) -> list[dict]`
    - `update_user(engine: Engine, user_id: str, actor_user_id: str, display_name: str | None = None, email: str | None = None, role: str | None = None, allowed_profiles: list[str] | None = None, is_active: bool | None = None, client_ip: str | None = None) -> dict` (enforces non-self-disable/demote and non-last-admin; revokes sessions cleanly on disable/role/profile change; writes `iam.auth_event`)
    - `reset_password_by_admin(engine: Engine, user_id: str, actor_user_id: str, client_ip: str | None = None) -> str`
    - `unlock_user(engine: Engine, user_id: str, actor_user_id: str, client_ip: str | None = None) -> dict`
    - `revoke_user_sessions(engine: Engine, user_id: str, actor_user_id: str, reason: str = "admin_revoked", client_ip: str | None = None) -> int`
    - `list_active_sessions(engine: Engine, user_id: str | None = None) -> list[dict]`
    - `list_auth_events(engine: Engine, user_id: str | None = None, event_type: str | None = None, date_from: date | None = None, date_to: date | None = None, limit: int = 100) -> list[dict]`
    - `record_auth_event(engine: Engine, event_type: str, user_id: str | None = None, username_attempted: str | None = None, actor_user_id: str | None = None, detail: dict | None = None, client_ip: str | None = None) -> None`
    - `seed_default_demo_users(engine: Engine) -> list[dict]` (idempotently creates/ensures `demo.ceo`, `demo.ktt`, `demo.kho`, `demo.admin` preserving `usr_ceo`, `usr_ktt`, `usr_kho`, `usr_admin`)

- [ ] **Step 1: Write failing migration and IAM service tests (`v2/tests/integration/test_iam_service_and_migration.py`)**

```python
def test_migration_003_creates_iam_tables_and_blocks_ro_role():
    iam_eng = get_iam_engine()
    with iam_eng.connect() as conn:
        tbls = {
            r[0]
            for r in conn.execute(
                sa.text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'iam'")
            ).fetchall()
        }
        assert {"app_user", "user_session", "auth_event"} <= tbls
    ro_eng = get_ro_engine()
    with pytest.raises(sa.exc.ProgrammingError):
        with ro_eng.connect() as conn:
            conn.execute(sa.text("SELECT count(*) FROM iam.app_user"))

def test_password_policy_and_dummy_timing_defense(clean_iam_test_users):
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("short1")
    with pytest.raises(PasswordPolicyError):
        validate_password_strength("MinhLong2026!", username="nva.ceo")
    assert hash_password("SecurePass99").startswith("$argon2id$")

def test_lockout_after_5_failures_and_admin_unlock(iam_eng, clean_iam_test_users): ...
def test_session_idle_and_absolute_expiry_and_immediate_revoke(iam_eng, clean_iam_test_users): ...
def test_admin_cannot_self_disable_or_remove_last_admin(iam_eng, clean_iam_test_users): ...
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/integration/test_iam_service_and_migration.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.services.iam_service'`).

- [ ] **Step 3: Implement `003_iam_users_sessions.sql`, `get_iam_engine` in `db/apply_db.py`, and `app/services/iam_service.py`**
Run `apply_all(admin_uri=settings.get_admin_uri(profile="real"))` (or via pytest fixture) to verify migration `003` applies idempotently alongside `001` and `002`. Ensure `gml_ai_ro` gets `REVOKE ALL ON SCHEMA iam` explicitly and `gml_ai_app` gets `SELECT, INSERT, UPDATE` on all `iam.*` tables + `USAGE` on sequences.

- [ ] **Step 4: Run migration, IAM service, and regression tests**
Run: `pytest tests/integration/test_iam_service_and_migration.py tests/integration/test_db_migration_002_p1r.py -v`
Expected: PASS cleanly with zero warnings (restore `t1_permissions.txt` if touched).

- [ ] **Step 5: Commit**
```bash
git add v2/db/migrations/003_iam_users_sessions.sql v2/db/apply_db.py v2/app/services/iam_service.py v2/tests/integration/test_iam_service_and_migration.py
git commit -m "feat(v2-iam): add iam schema migration 003 and iam_service (Argon2id, NIST policy, stateful sessions)"
```

---

### Task 2: `TokenAuthVerifier` DB Session Lookup, Profile & Password-Change Gates, and `/v1/auth/*` Endpoints

**Files:**
- Create: `v2/app/api/routers/auth.py`
- Modify: `v2/app/core/auth.py`, `v2/app/api/deps.py`, `v2/app/api/schemas.py`, `v2/app/api/routers/chat.py:54-65`, `v2/app/api/main.py:170-182`
- Test: `v2/tests/integration/test_api_auth_and_rbac.py`

**Interfaces:**
- Consumes: `iam_service.*`, `get_iam_engine`, `SlidingWindowRateLimiter`.
- Modifies in `v2/app/core/auth.py`:
  - `UserPrincipal` adds `username: str | None = None`, `allowed_profiles: list[str] = Field(default_factory=lambda: ["real", "synth"])`, `must_change_password: bool = False`, `session_id: int | None = None`.
  - `TokenAuthVerifier.__init__(self, settings: Settings, iam_engine: Engine | None = None)` and `verify_bearer_token(self, raw_token: str, now: datetime | None = None) -> UserPrincipal`: checks static tokens first (dev tokens in non-prod + `auth_tokens_json`), then queries `iam_service.verify_session_token(self.iam_engine, raw_token, now=now)` (gracefully handling `SQLAlchemyError` if DB unreachable).
- Modifies in `v2/app/api/deps.py`:
  - `get_login_rate_limiter() -> SlidingWindowRateLimiter` (10 req/60s per client IP) + `reset_login_rate_limiter()`.
  - `get_token_verifier`: passes `iam_engine=get_iam_engine()` unless disabled/overridden cleanly.
  - `get_current_user(request: Request, ...)`: raises `403 PASSWORD_CHANGE_REQUIRED` when `principal.must_change_password` is `True` AND `not request.url.path.startswith("/v1/auth")`.
  - `resolve_profile(profile: str | None, settings: Settings, user: UserPrincipal | None = None) -> str`: raises `403 PROFILE_FORBIDDEN` if `user is not None` and `target_profile not in (user.allowed_profiles or ["real"])`. Update all routers (`actions.py`, `alerts.py`, `kpi.py`, `overview.py`, `pins.py`) to pass `user=user`, and enforce the same check on `payload.data_profile` in `v2/app/api/routers/chat.py`.
- Produces in `v2/app/api/schemas.py` & `v2/app/api/routers/auth.py`:
  - `LoginRequest(username: str, password: str)`, `AuthenticatedUserInfo(user_id: str, username: str | None, display_name: str, email: str | None = None, role: str, allowed_profiles: list[str], must_change_password: bool = False)`, `LoginResponse(access_token: str, token_type: str = "bearer", expires_at: str, user: AuthenticatedUserInfo)`, `ChangePasswordRequest(current_password: str, new_password: str)`, `ChangePasswordResponse(status: str, message: str)`.
  - `POST /v1/auth/login` -> `200 LoginResponse` (`401 INVALID_CREDENTIALS`, `423 ACCOUNT_LOCKED`, `429 RATE_LIMITED`)
  - `POST /v1/auth/logout` -> `200 {"status": "ok"}` (revokes `user.session_id` or bearer token, writes `app.audit_log`)
  - `GET /v1/auth/me` -> `200 AuthenticatedUserInfo`
  - `POST /v1/auth/change-password` -> `200 ChangePasswordResponse` (`422 PASSWORD_POLICY_ERROR`, `401 INVALID_CREDENTIALS` on wrong `current_password`)

- [ ] **Step 1: Write failing tests in `v2/tests/integration/test_api_auth_and_rbac.py`**

```python
def test_login_logout_me_and_immediate_revocation(client, iam_user_factory):
    # login -> 200 Bearer token; /v1/auth/me -> 200; /v1/auth/logout -> 200; /v1/auth/me again -> 401
    ...

def test_must_change_password_blocks_business_routes_until_changed(client, temp_user):
    # /v1/overview -> 403 PASSWORD_CHANGE_REQUIRED; /v1/auth/change-password -> 200; /v1/overview -> 200
    ...

def test_profile_forbidden_on_get_and_chat_when_user_lacks_synth(client, real_only_ktt_user):
    assert client.get("/v1/overview?profile=synth", headers=hdr).status_code == 403
    assert client.post("/v1/chat", json={"query": "Dư nợ?", "data_profile": "synth"}, headers=hdr).status_code == 403

def test_kho_real_session_cannot_access_finance_kpi_or_admin(client, kho_user): ...
def test_login_rate_limit_10_per_minute_per_ip(client): ...
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/integration/test_api_auth_and_rbac.py -v`
Expected: FAIL (`404 Not Found` on `/v1/auth/login`).

- [ ] **Step 3: Implement `auth.py`, `deps.py`, `schemas.py`, `routers/auth.py`, `routers/chat.py`, `main.py`, and pass `user=user` to `resolve_profile` calls**
Also ensure `get_app_uri` vs `get_iam_engine` never stores raw passwords/tokens in `audit_log` or `auth_event`.

- [ ] **Step 4: Run new auth tests + existing P4/P4r API contracts**
Run: `pytest tests/integration/test_api_auth_and_rbac.py tests/unit/test_api_core_and_resources_t5.py tests/integration/test_api_contract_p4r.py tests/integration/test_api_contract_t5.py -k "not tc_t5_08_openapi_snapshot" -v`
Expected: PASS cleanly.

- [ ] **Step 5: Commit**
```bash
git add v2/app/core/auth.py v2/app/api/deps.py v2/app/api/schemas.py v2/app/api/routers/auth.py v2/app/api/routers/chat.py v2/app/api/routers/actions.py v2/app/api/routers/alerts.py v2/app/api/routers/kpi.py v2/app/api/routers/overview.py v2/app/api/routers/pins.py v2/app/api/main.py v2/tests/integration/test_api_auth_and_rbac.py
git commit -m "feat(v2-iam): add stateful DB session auth, /v1/auth endpoints, profile & password gates"
```

---

### Task 3: `/v1/admin/*` Router (Users, Sessions, Auth Audit, Monthly Simulation Runner) & CLI Bootstrap Scripts

**Files:**
- Create: `v2/app/api/routers/admin.py`, `v2/scripts/create_admin.py`, `v2/scripts/seed_demo_users.py`
- Modify: `v2/app/api/schemas.py`, `v2/app/api/main.py`
- Test: `v2/tests/integration/test_api_admin_and_simulation.py`

**Interfaces:**
- Consumes: `iam_service.*`, `db/synthetic/generate.py:generate_synthetic_warehouse`, `get_kpi_cache`, `get_app_engine`, `write_audit_log`.
- Produces in `v2/app/api/schemas.py` & `v2/app/api/routers/admin.py` (all routes guarded by `require_admin_user` -> `user.role == "quan_tri_he_thong"` else `403 FORBIDDEN` + 1 audit row):
  - `GET /v1/admin/users?q=&role=&is_active=` -> `AdminUserListResponse(users: list[AdminUserItem], total: int)`
  - `POST /v1/admin/users` -> `201 AdminUserCreateResponse(user: AdminUserItem, temporary_password: str)`
  - `PATCH /v1/admin/users/{user_id}` -> `200 AdminUserItem` (`409 SELF_LOCKOUT` / `LAST_ADMIN_PROTECTED`)
  - `POST /v1/admin/users/{user_id}/reset-password` -> `200 AdminResetPasswordResponse(user_id: str, temporary_password: str)`
  - `POST /v1/admin/users/{user_id}/unlock` -> `200 AdminUserItem`
  - `POST /v1/admin/users/{user_id}/revoke-sessions` -> `200 {"user_id": ..., "revoked_count": n}`
  - `GET /v1/admin/sessions?user_id=` -> `AdminSessionListResponse(sessions: list[AdminSessionItem], total: int)`
  - `DELETE /v1/admin/sessions/{session_id}` -> `200 {"revoked": True}`
  - `GET /v1/admin/auth-events?user_id=&event_type=&date_from=&date_to=&limit=` -> `AuthEventListResponse(events: list[AuthEventItem], total: int)`
  - `GET /v1/admin/simulation/status` -> `SimulationStatusResponse(last_run_at: str | None, last_status: str | None, last_message: str | None, checksum_file_exists: bool)` (reads `app.job_heartbeat WHERE job_name = 'monthly_simulation'` on `real`/`synth` and `v2/db/synthetic/CHECKSUM.txt`)
  - `POST /v1/admin/simulation/run` -> `SimulationRunResponse(status: str, tables_generated: int, duration_ms: float, run_at: str, message: str)` (executes `generate_synthetic_warehouse(seed=payload.seed)`, clears `get_kpi_cache`, records `app.job_heartbeat` `job_name='monthly_simulation'` and `iam.auth_event` `event_type='simulation_triggered'`)
- Produces CLI scripts:
  - `v2/scripts/create_admin.py` (`--username`, `--display-name`, `--email`, idempotent check)
  - `v2/scripts/seed_demo_users.py` (refuses to run if `settings.app_env == "production"`, creates `demo.ceo`, `demo.ktt`, `demo.kho`, `demo.admin` preserving `usr_ceo`, `usr_ktt`, `usr_kho`, `usr_admin`).

- [ ] **Step 1: Write failing tests in `v2/tests/integration/test_api_admin_and_simulation.py`**

```python
def test_non_admin_cannot_call_any_admin_or_simulation_endpoint(all_non_admin_clients):
    # ceo, ktt, kho all get 403 FORBIDDEN on GET /v1/admin/users and POST /v1/admin/simulation/run
    ...

def test_admin_create_update_reset_unlock_and_instant_revoke(client_admin, client_raw): ...
def test_admin_simulation_run_updates_heartbeat_clears_cache_and_writes_event(monkeypatch, client_admin): ...
def test_no_password_hash_or_raw_token_leaked_in_admin_or_audit_logs(client_admin): ...
def test_seed_demo_users_refuses_production_env(monkeypatch): ...
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/integration/test_api_admin_and_simulation.py -v`
Expected: FAIL (`404 Not Found` on `/v1/admin/users`).

- [ ] **Step 3: Implement `v2/app/api/routers/admin.py`, `schemas.py`, `main.py`, `scripts/create_admin.py`, `scripts/seed_demo_users.py`**

- [ ] **Step 4: Run tests to verify pass**
Run: `pytest tests/integration/test_api_admin_and_simulation.py tests/integration/test_api_auth_and_rbac.py -v`
Expected: PASS cleanly.

- [ ] **Step 5: Commit**
```bash
git add v2/app/api/routers/admin.py v2/app/api/schemas.py v2/app/api/main.py v2/scripts/create_admin.py v2/scripts/seed_demo_users.py v2/tests/integration/test_api_admin_and_simulation.py
git commit -m "feat(v2-iam): add /v1/admin user/session/simulation APIs and bootstrap scripts"
```

---

### Task 4: Streamlit Login Page, F5 Cookie Persistence, Role-Locked Sidebar & 4-Tab Admin Panel

**Files:**
- Create: `v2/app/ui/components/login_view.py`, `v2/app/ui/components/admin_view.py`
- Modify: `v2/app/ui/api_client.py`, `v2/app/ui/components/__init__.py`, `v2/app/ui/streamlit_app.py`
- Test: `v2/tests/unit/test_ui_auth_and_admin.py`

**Interfaces:**
- Consumes: `theme.py` (Minh Long Crimson + `Simplifica`, `Be Vietnam Pro`, `get_logo_base64`, `format_vi_datetime`), `st.context.cookies`.
- Produces in `v2/app/ui/api_client.py`:
  - Test hook mirroring `set_default_transport_for_testing`: `set_require_login_for_testing(enabled: bool) -> None` and `get_require_login_for_testing() -> bool` (default `False` ONLY when `_DEFAULT_TEST_TRANSPORT` is injected unless toggled `True` in auth UI tests; real running Streamlit app has `_DEFAULT_TEST_TRANSPORT is None` so real login is **always enforced**!).
  - New `HttpApiClient` methods: `login(username, password)`, `logout()`, `get_me()`, `change_password(current_password, new_password)`, `admin_list_users(...)`, `admin_create_user(...)`, `admin_update_user(...)`, `admin_reset_password(...)`, `admin_unlock_user(...)`, `admin_revoke_user_sessions(...)`, `admin_list_sessions(...)`, `admin_revoke_session(...)`, `admin_list_auth_events(...)`, `admin_get_simulation_status()`, `admin_run_simulation(seed=42)`.
- Produces in `v2/app/ui/components/login_view.py`:
  - `COOKIE_NAME = "gml_session"`
  - `set_session_cookie(token: str, max_age: int = 43200) -> None` / `clear_session_cookie() -> None` (lightweight JS snippet writing `window.parent.document.cookie` with `path=/; SameSite=Lax`, guarded cleanly under `AppTest`!).
  - `render_login_view(api_base_url: str, pending_query_params: dict | None = None) -> None`
  - `render_change_password_view(api_client: HttpApiClient, user: dict, forced: bool = False) -> None`
- Produces in `v2/app/ui/components/admin_view.py`:
  - `render_admin_panel(api_client: HttpApiClient, current_user: dict) -> None` with 4 screens/tabs: **👥 Người dùng**, **🔐 Phiên đăng nhập**, **⚙️ Dữ liệu Mô phỏng & Dự báo (`synth`)**, **📜 Nhật ký Truy cập**.
- Modifies `v2/app/ui/streamlit_app.py`:
  - Removes the sidebar role dropdown completely.
  - When `_DEFAULT_TEST_TRANSPORT is None` OR `get_require_login_for_testing()` is `True`:
    - Check `st.session_state.get("auth_token")` -> if missing, check `st.context.cookies.get("gml_session")` -> call `GET /v1/auth/me` to restore F5 session cleanly (if `401`, clear cookie + show `"Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."`).
    - If not logged in -> render `render_login_view` and `st.stop()` (ignoring `?role=` query param, preserving `?dashboard`, `?kpi`, `?screen`, `?profile` in `session_state` to resume after login!).
    - If `user.get("must_change_password")` -> render forced password-change form and `st.stop()`.
    - If `user["role"] == "quan_tri_he_thong"` -> render Admin sidebar + `render_admin_panel` ONLY (no KPI overview/chat/alerts).
    - Otherwise -> lock `role = user["role"]`, render read-only user identity card (`👤 {display_name}`, role badge), profile selector ONLY if `len(allowed_profiles) > 1` (fallback notice if single profile, ignoring disallowed `?profile=`), `🔑 Đổi mật khẩu`, `↩ Đăng xuất`, and the 5 business screens (`overview` passes `role=role`).
    - Handle `401` `ApiClientError` cleanly by clearing session + cookie + rerunning to login screen!

- [ ] **Step 1: Write failing tests in `v2/tests/unit/test_ui_auth_and_admin.py`**

```python
def test_unauthenticated_user_sees_login_form_only_and_no_role_selector(auth_app_test):
    at = auth_app_test(query_params={"role": "ceo"})
    at.run(timeout=35)
    assert not at.exception
    assert not any(s.key == "role_selector" for s in at.selectbox)
    assert any("Đăng nhập" in b.label for b in at.button)

def test_login_sets_session_and_locks_ktt_role_ignoring_query_role(auth_app_test, demo_ktt): ...
def test_f5_reload_restores_session_from_cookie_and_clears_expired_cookie(auth_app_test): ...
def test_forced_password_change_screen_blocks_main_app_until_changed(auth_app_test, temp_user): ...
def test_admin_login_renders_4_tab_admin_panel_without_business_screens(auth_app_test, demo_admin): ...
def test_ui_layer_still_has_zero_server_imports(): ...
```

- [ ] **Step 2: Run test to verify failure**
Run: `pytest tests/unit/test_ui_auth_and_admin.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.ui.components.login_view'`).

- [ ] **Step 3: Implement `login_view.py`, `admin_view.py`, `api_client.py`, `__init__.py`, and `streamlit_app.py`**

- [ ] **Step 4: Run ALL UI tests (`auth` + `p4r` + `t6`)**
Run: `pytest tests/unit/test_ui_auth_and_admin.py tests/unit/test_ui_streamlit_p4r.py tests/unit/test_ui_streamlit_t6.py -v`
Expected: ALL PASS cleanly.

- [ ] **Step 5: Commit**
```bash
git add v2/app/ui/api_client.py v2/app/ui/components/__init__.py v2/app/ui/components/login_view.py v2/app/ui/components/admin_view.py v2/app/ui/streamlit_app.py v2/tests/unit/test_ui_auth_and_admin.py
git commit -m "feat(v2-iam): add Streamlit login gate, F5 cookie persistence, role-locked sidebar & 4-tab Admin Panel"
```

---

### Task 5: OpenAPI Snapshot Refresh, EV-13..EV-16 Evidence (`08_login.png`, `09_admin_panel.png`) & Full Regression Suite

**Files:**
- Modify: `v2/scripts/capture_ui_screenshots.py`, `v2/tests/integration/test_api_contract_p4r.py`
- Regenerate: `v2/docs/openapi.json`, `v2/eval/reports/api_contract.txt`, `v2/eval/reports/audit_log_sample.json`, `v2/eval/reports/ui_screens/*`

**Steps:**
- [ ] **Step 1: Add `/v1/auth/*` and `/v1/admin/*` routes to `NEW_ENDPOINTS` M-13 and M-14 checks in `v2/tests/integration/test_api_contract_p4r.py`**
Run: `pytest tests/integration/test_api_contract_p4r.py -k "m13 or m14" -v` -> Expected FAIL until OpenAPI regenerated.

- [ ] **Step 2: Regenerate `v2/docs/openapi.json` cleanly**
Verify zero removed paths/schemas/fields against previous `docs/openapi.json` (strictly additive `/v1/auth/*` and `/v1/admin/*`).

- [ ] **Step 3: Update `v2/scripts/capture_ui_screenshots.py` for real-login screenshot seeding & add `08_login.png` and `09_admin_panel.png`**
Ensure demo accounts (`demo.ceo`, `demo.admin`) authenticate cleanly during headless Edge CDP capture (logging in on `08_login.png`, seeding `gml_session` or logging in via UI for `01..07`, and logging in as `demo.admin` for `09_admin_panel.png`), regenerate all screenshots, and visually inspect PNGs via `read_file`.

- [ ] **Step 4: Refresh EV-14 (`eval/reports/api_contract.txt`) & EV-15 (`eval/reports/audit_log_sample.json`) and run full `pytest -q`**
Run: `pytest -q` (without manual shell `GOOGLE_API_KEY` override) -> Expected: 100% PASS across all existing + new IAM/Admin tests.
Restore `v2/eval/reports/t1_permissions.txt` via `git checkout -- v2/eval/reports/t1_permissions.txt`.

- [ ] **Step 5: Commit**
```bash
git add v2/scripts/capture_ui_screenshots.py v2/tests/integration/test_api_contract_p4r.py v2/docs/openapi.json v2/eval/reports/api_contract.txt v2/eval/reports/audit_log_sample.json v2/eval/reports/ui_screens/
git commit -m "chore(v2-iam): update OpenAPI snapshot and EV-13..EV-16 evidence with login & admin screens"
```
