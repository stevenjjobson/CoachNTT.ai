-- ===============================================
-- Fix Missing Dependencies
-- ===============================================
-- Fixes issues identified during Phase 1 testing:
-- 1. Missing ccp_admin role
-- 2. Missing audit schema
-- 3. Audit trigger memory_id field error
-- ===============================================

BEGIN;

-- ===============================================
-- Create Missing Role
-- ===============================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ccp_admin') THEN
        CREATE ROLE ccp_admin WITH LOGIN PASSWORD 'change_in_production';
        GRANT CONNECT ON DATABASE test_db TO ccp_admin;
        COMMENT ON ROLE ccp_admin IS 'Administrative role for CCP system management';
    END IF;
END
$$;

-- ===============================================
-- Create Audit Schema
-- ===============================================
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS 'Audit trail and security event logging';

-- Grant permissions
GRANT USAGE ON SCHEMA audit TO ccp_admin;
GRANT CREATE ON SCHEMA audit TO ccp_admin;

-- ===============================================
-- Fix Audit Log Table (Move to audit schema)
-- ===============================================
-- Check if audit_log exists in safety schema and move it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'safety' AND table_name = 'audit_log'
    ) THEN
        -- Move table to audit schema
        ALTER TABLE safety.audit_log SET SCHEMA audit;
    END IF;
END
$$;

-- Create audit_log table if it doesn't exist
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    event_source VARCHAR(255) NOT NULL,
    memory_id UUID,
    action VARCHAR(50),
    details JSONB,
    safety_impact VARCHAR(20),
    user_name VARCHAR(255) DEFAULT current_user,
    session_id VARCHAR(255),
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit.audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_memory_id ON audit.audit_log(memory_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit.audit_log(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_safety_impact ON audit.audit_log(safety_impact);

-- ===============================================
-- Fix Audit Trigger Function
-- ===============================================
CREATE OR REPLACE FUNCTION safety.comprehensive_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_changed_fields JSONB;
    v_safety_impact VARCHAR(20);
    v_memory_id UUID;
BEGIN
    -- Convert records to JSONB
    IF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
    ELSE -- UPDATE
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
    END IF;
    
    -- Determine safety impact
    v_safety_impact := CASE
        WHEN TG_TABLE_NAME IN ('abstraction_patterns', 'validation_log', 'memory_references') THEN 'HIGH'
        WHEN TG_TABLE_NAME IN ('abstraction_metrics', 'reference_conflicts') THEN 'MEDIUM'
        ELSE 'LOW'
    END;
    
    -- Extract memory_id based on table structure
    v_memory_id := NULL;
    IF TG_OP != 'DELETE' THEN
        -- Check if the table has a memory_id column
        IF v_new_data ? 'memory_id' THEN
            v_memory_id := (v_new_data->>'memory_id')::UUID;
        ELSIF v_new_data ? 'id' AND TG_TABLE_NAME = 'cognitive_memory' THEN
            v_memory_id := (v_new_data->>'id')::UUID;
        END IF;
    ELSIF TG_OP = 'DELETE' AND v_old_data IS NOT NULL THEN
        IF v_old_data ? 'memory_id' THEN
            v_memory_id := (v_old_data->>'memory_id')::UUID;
        ELSIF v_old_data ? 'id' AND TG_TABLE_NAME = 'cognitive_memory' THEN
            v_memory_id := (v_old_data->>'id')::UUID;
        END IF;
    END IF;
    
    -- Identify changed fields for updates
    IF TG_OP = 'UPDATE' THEN
        SELECT jsonb_object_agg(key, value) INTO v_changed_fields
        FROM (
            SELECT key, v_new_data->key as value
            FROM jsonb_object_keys(v_new_data) AS key
            WHERE v_new_data->key IS DISTINCT FROM v_old_data->key
        ) changes;
    END IF;
    
    -- Insert audit record
    INSERT INTO audit.audit_log (
        event_type,
        event_source,
        memory_id,
        action,
        details,
        safety_impact
    ) VALUES (
        'DATA_CHANGE',
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        v_memory_id,
        TG_OP,
        jsonb_build_object(
            'old_data', v_old_data,
            'new_data', v_new_data,
            'changed_fields', v_changed_fields,
            'user', current_user,
            'timestamp', NOW()
        ),
        v_safety_impact
    );
    
    -- Return appropriate value
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ===============================================
-- Grant Permissions
-- ===============================================
-- Grant permissions to test_user (current user)
GRANT USAGE ON SCHEMA safety TO test_user;
GRANT USAGE ON SCHEMA audit TO test_user;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA safety TO test_user;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO test_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA safety TO test_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA audit TO test_user;

-- ===============================================
-- Verify Fixes
-- ===============================================
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Check role exists
    SELECT COUNT(*) INTO v_count FROM pg_roles WHERE rolname = 'ccp_admin';
    IF v_count > 0 THEN
        RAISE NOTICE 'SUCCESS: ccp_admin role exists';
    END IF;
    
    -- Check audit schema exists
    SELECT COUNT(*) INTO v_count FROM information_schema.schemata WHERE schema_name = 'audit';
    IF v_count > 0 THEN
        RAISE NOTICE 'SUCCESS: audit schema exists';
    END IF;
    
    -- Check audit_log table exists
    SELECT COUNT(*) INTO v_count FROM information_schema.tables 
    WHERE table_schema = 'audit' AND table_name = 'audit_log';
    IF v_count > 0 THEN
        RAISE NOTICE 'SUCCESS: audit.audit_log table exists';
    END IF;
END
$$;

COMMIT;