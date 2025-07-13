-- Database initialization script for Cognitive Coding Partner
-- This runs automatically when the Docker container is first created

-- Run the safety foundation migration
\i /migrations/000_safety_foundation.sql

-- Run the safety enforcement migration
\i /migrations/001_safety_enforcement.sql

-- Create application user if not exists (for future use)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'ccp_app') THEN
        CREATE USER ccp_app WITH PASSWORD 'ccp_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA safety TO ccp_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA safety TO ccp_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA safety TO ccp_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA safety TO ccp_app;

-- Create main application schema
CREATE SCHEMA IF NOT EXISTS ccp;
GRANT ALL ON SCHEMA ccp TO ccp_app;

-- Verify extensions are installed
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
        RAISE EXCEPTION 'uuid-ossp extension is required but not installed';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension is required but not installed';
    END IF;
END
$$;

-- Log successful initialization
INSERT INTO safety.audit_log (
    event_type, 
    event_source, 
    action, 
    details,
    safety_impact
) VALUES (
    'system_init',
    'database_setup',
    'initialize_safety_schema',
    jsonb_build_object(
        'version', '1.0.0',
        'migrations', ARRAY['000_safety_foundation', '001_safety_enforcement'],
        'timestamp', now()
    ),
    'none'
);

-- Display initialization status
SELECT 'Safety schema initialized successfully' AS status;
SELECT COUNT(*) AS pattern_count FROM safety.abstraction_patterns;
SELECT tablename FROM pg_tables WHERE schemaname = 'safety' ORDER BY tablename;