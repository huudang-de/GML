-- ==============================================================================
-- Migration: 003_iam_users_sessions.sql
-- Description: Creates internal IAM schema 'iam' with app_user, user_session,
--              and auth_event tables for credential auth & RBAC.
-- Specification: 2026-11-18-v2-login-iam-admin-design.md §5.2
-- Roles: gml_ai_app gets SELECT/INSERT/UPDATE; gml_ai_ro is explicitly blocked.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS iam;

-- 1. Table: iam.app_user (Internal user accounts)
CREATE TABLE IF NOT EXISTS iam.app_user (
    user_id              VARCHAR(100) PRIMARY KEY,
    username             VARCHAR(64)  NOT NULL,
    display_name         VARCHAR(200) NOT NULL,
    email                VARCHAR(200),
    password_hash        TEXT         NOT NULL,
    role                 VARCHAR(50)  NOT NULL CHECK (role IN ('ceo', 'ke_toan_truong', 'quan_ly_kho', 'quan_tri_he_thong')),
    allowed_profiles     TEXT[]       NOT NULL DEFAULT ARRAY['real', 'synth'],
    is_active            BOOLEAN      NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN      NOT NULL DEFAULT TRUE,
    failed_login_count   INT          NOT NULL DEFAULT 0,
    locked_until         TIMESTAMPTZ,
    last_login_at        TIMESTAMPTZ,
    password_changed_at  TIMESTAMPTZ,
    created_by           VARCHAR(100),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_user_username ON iam.app_user (lower(username));

-- 2. Table: iam.user_session (Stateful sessions; SHA-256 hex token digest only)
CREATE TABLE IF NOT EXISTS iam.user_session (
    id             BIGSERIAL PRIMARY KEY,
    token_hash     CHAR(64)     NOT NULL UNIQUE,
    user_id        VARCHAR(100) NOT NULL REFERENCES iam.app_user(user_id),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at     TIMESTAMPTZ  NOT NULL,
    last_seen_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    revoked_at     TIMESTAMPTZ,
    revoked_reason VARCHAR(50),
    revoked_by     VARCHAR(100),
    client_ip      VARCHAR(64),
    user_agent     VARCHAR(300)
);

CREATE INDEX IF NOT EXISTS idx_user_session_user ON iam.user_session (user_id) WHERE revoked_at IS NULL;

-- 3. Table: iam.auth_event (Append-only authentication and admin audit log)
CREATE TABLE IF NOT EXISTS iam.auth_event (
    id                 BIGSERIAL PRIMARY KEY,
    event_type         VARCHAR(40)  NOT NULL,
    user_id            VARCHAR(100),
    username_attempted VARCHAR(64),
    actor_user_id      VARCHAR(100),
    detail             JSONB,
    client_ip          VARCHAR(64),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_event_created ON iam.auth_event (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_auth_event_user ON iam.auth_event (user_id);

-- Grant least-privilege access to gml_ai_app (no DELETE on iam tables)
GRANT USAGE ON SCHEMA iam TO gml_ai_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA iam TO gml_ai_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA iam TO gml_ai_app;

-- Explicitly isolate gml_ai_ro from all iam objects
REVOKE ALL ON SCHEMA iam FROM gml_ai_ro;
REVOKE ALL ON ALL TABLES IN SCHEMA iam FROM gml_ai_ro;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA iam FROM gml_ai_ro;
