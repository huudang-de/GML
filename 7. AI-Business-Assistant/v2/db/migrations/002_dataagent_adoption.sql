-- ==============================================================================
-- Migration: 002_dataagent_adoption.sql
-- Description: Extends app.alert_event and adds app.action_item and app.pinned_kpi.
-- Specification: Architecture Spec Amendment §5.1 / P1r Task 2
-- Roles: Owned by admin / gml_ai_app
-- ==============================================================================

-- 1. Extend app.alert_event with period, evidence, dedup_key, and escalated_at
ALTER TABLE app.alert_event ADD COLUMN IF NOT EXISTS period VARCHAR(7);
ALTER TABLE app.alert_event ADD COLUMN IF NOT EXISTS evidence JSONB;
ALTER TABLE app.alert_event ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(200);
ALTER TABLE app.alert_event ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_alert_event_dedup_key ON app.alert_event(dedup_key);

-- 2. Table: app.action_item (Operational actions linked to alerts or chat turns)
CREATE TABLE IF NOT EXISTS app.action_item (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    kpi_key VARCHAR(100) NOT NULL,
    level VARCHAR(20) NOT NULL CHECK (level IN ('canh_bao', 'nghiem_trong')),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('alert', 'chat')),
    source_ref VARCHAR(100) NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'done', 'dismissed')),
    due_date DATE,
    note TEXT,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_action_item_source_title UNIQUE (source_type, source_ref, title)
);

CREATE INDEX IF NOT EXISTS idx_action_item_role_status ON app.action_item(assigned_role, status);
CREATE INDEX IF NOT EXISTS idx_action_item_kpi_key ON app.action_item(kpi_key);

-- 3. Table: app.pinned_kpi (Personalized dashboard pinned KPI cards)
CREATE TABLE IF NOT EXISTS app.pinned_kpi (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    data_profile VARCHAR(10) NOT NULL CHECK (data_profile IN ('real', 'synth')),
    kpi_key VARCHAR(100) NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_pinned_kpi_user_profile_kpi UNIQUE (user_id, data_profile, kpi_key)
);

CREATE INDEX IF NOT EXISTS idx_pinned_kpi_user_profile ON app.pinned_kpi(user_id, data_profile);

-- Grant privileges to app role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO gml_ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO gml_ai_app;
