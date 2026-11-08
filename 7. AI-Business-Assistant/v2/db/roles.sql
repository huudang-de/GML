-- ==============================================================================
-- GML AI Business Assistant v2.0 — Database Security Roles & Schemas
-- Specification: Spec §3.1, §5 T1
-- ==============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gml_ai_ro') THEN
    CREATE ROLE gml_ai_ro LOGIN PASSWORD 'ro_secret' NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gml_ai_app') THEN
    CREATE ROLE gml_ai_app LOGIN PASSWORD 'app_secret' NOINHERIT;
  END IF;
END $$;

-- Enforce read-only transaction and strict 15-second execution timeout on AI read role
ALTER ROLE gml_ai_ro SET statement_timeout = '15s';
ALTER ROLE gml_ai_ro SET default_transaction_read_only = on;

-- Schema ai_views: gml_ai_ro has SELECT access only
CREATE SCHEMA IF NOT EXISTS ai_views;
GRANT USAGE ON SCHEMA ai_views TO gml_ai_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA ai_views TO gml_ai_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai_views GRANT SELECT ON TABLES TO gml_ai_ro;

-- Schema silver / synthetic: Block gml_ai_ro completely (Layer 1 Defense)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'silver') THEN
    EXECUTE 'REVOKE ALL ON SCHEMA silver FROM gml_ai_ro';
    EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA silver FROM gml_ai_ro';
  END IF;
  IF EXISTS (SELECT FROM information_schema.schemata WHERE schema_name = 'synthetic') THEN
    EXECUTE 'REVOKE ALL ON SCHEMA synthetic FROM gml_ai_ro';
    EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA synthetic FROM gml_ai_ro';
  END IF;
END $$;

-- Prevent writing in public schema
REVOKE CREATE ON SCHEMA public FROM gml_ai_ro;

-- Schema app: Operational tables for gml_ai_app (chat turns, audit logs, alerts, feedback, heartbeat)
CREATE SCHEMA IF NOT EXISTS app;
GRANT USAGE, CREATE ON SCHEMA app TO gml_ai_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO gml_ai_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO gml_ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO gml_ai_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO gml_ai_app;

-- Block gml_ai_ro from modifying app schema
REVOKE ALL ON SCHEMA app FROM gml_ai_ro;
REVOKE ALL ON ALL TABLES IN SCHEMA app FROM gml_ai_ro;
