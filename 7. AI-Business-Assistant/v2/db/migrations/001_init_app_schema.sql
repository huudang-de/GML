-- ==============================================================================
-- Migration: 001_init_app_schema.sql
-- Description: Creates operational schema 'app' and 5 core tracking tables.
-- Specification: Spec §5 T1, §5 T5, §5 T7
-- Roles: Owned by admin / gml_ai_app
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS app;

-- 1. Table: app.chat_turn (Conversation turns & multi-turn memory)
CREATE TABLE IF NOT EXISTS app.chat_turn (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    query TEXT NOT NULL,
    standalone_query TEXT,
    intent VARCHAR(50),
    kpi_keys TEXT[],
    sql_query TEXT,
    answer JSONB,
    confidence DOUBLE PRECISION,
    request_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_turn_session_id ON app.chat_turn(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_turn_request_id ON app.chat_turn(request_id);
CREATE INDEX IF NOT EXISTS idx_chat_turn_created_at ON app.chat_turn(created_at);

-- 2. Table: app.audit_log (Security & query audit trail)
CREATE TABLE IF NOT EXISTS app.audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    query TEXT,
    sql_executed TEXT,
    views_accessed TEXT[],
    request_id VARCHAR(100),
    execution_time_ms DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_request_id ON app.audit_log(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON app.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON app.audit_log(created_at);

-- 3. Table: app.alert_event (Financial thresholds and anomaly alerts)
CREATE TABLE IF NOT EXISTS app.alert_event (
    id BIGSERIAL PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL,
    kpi_key VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_event_kpi_key ON app.alert_event(kpi_key);
CREATE INDEX IF NOT EXISTS idx_alert_event_severity ON app.alert_event(severity);
CREATE INDEX IF NOT EXISTS idx_alert_event_created_at ON app.alert_event(created_at);

-- 4. Table: app.feedback (User thumbs up / down & qualitative remarks)
CREATE TABLE IF NOT EXISTS app.feedback (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(100),
    user_id VARCHAR(100),
    rating VARCHAR(20) NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_request_id ON app.feedback(request_id);

-- 5. Table: app.job_heartbeat (Scheduled workers & background tasks monitoring)
CREATE TABLE IF NOT EXISTS app.job_heartbeat (
    id BIGSERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT,
    duration_ms DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_heartbeat_job_name ON app.job_heartbeat(job_name);
CREATE INDEX IF NOT EXISTS idx_job_heartbeat_created_at ON app.job_heartbeat(created_at);

-- Grant privileges to app role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO gml_ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO gml_ai_app;
