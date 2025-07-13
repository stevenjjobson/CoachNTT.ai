-- Migration: 001_safety_enforcement.sql
-- Purpose: Add validation triggers, row-level security, and enhanced safety constraints
-- Date: 2025-01-13
-- Description: Database-level enforcement of safety requirements
-- Prerequisites: 000_safety_foundation.sql must be applied first

-- Set search path
SET search_path TO safety, public;

-- =====================================================
-- VALIDATION HELPER FUNCTIONS
-- =====================================================

-- Function to check if content contains concrete references
CREATE OR REPLACE FUNCTION safety.contains_concrete_references(
    p_content TEXT,
    p_allowed_threshold FLOAT DEFAULT 0.0
) RETURNS BOOLEAN AS $$
DECLARE
    v_patterns TEXT[] := ARRAY[
        -- File paths
        '(/[a-zA-Z0-9_/.-]+)',
        '([A-Z]:\\[^<>:"|?*]+)',
        -- User identifiers
        '(user[_-]?id\s*[:=]\s*\d+)',
        -- IPs
        '(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
        -- URLs with specific domains
        '(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        -- Specific identifiers
        '(id\s*[:=]\s*[''"]?[a-zA-Z0-9-]+[''"]?)',
        -- Container names
        '([a-zA-Z0-9]+[-_]container[-_][a-zA-Z0-9]+)',
        -- API keys/tokens
        '(sk_[a-zA-Z0-9]{24,}|pk_[a-zA-Z0-9]{24,})',
        -- Email addresses
        '([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ];
    v_pattern TEXT;
    v_match_count INTEGER := 0;
BEGIN
    -- Check each pattern
    FOREACH v_pattern IN ARRAY v_patterns LOOP
        IF p_content ~* v_pattern THEN
            v_match_count := v_match_count + 1;
        END IF;
    END LOOP;
    
    -- Return true if we found more concrete references than allowed
    RETURN v_match_count > p_allowed_threshold;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to validate abstraction completeness
CREATE OR REPLACE FUNCTION safety.validate_abstraction_completeness(
    p_memory_id UUID
) RETURNS TABLE(is_valid BOOLEAN, error_message TEXT, safety_score FLOAT) AS $$
DECLARE
    v_concrete_count INTEGER;
    v_abstracted_count INTEGER;
    v_abstraction_score FLOAT;
    v_has_metrics BOOLEAN;
BEGIN
    -- Check if metrics exist
    SELECT EXISTS(
        SELECT 1 FROM safety.abstraction_metrics 
        WHERE memory_id = p_memory_id
    ) INTO v_has_metrics;
    
    IF NOT v_has_metrics THEN
        RETURN QUERY SELECT FALSE, 'No abstraction metrics found for memory', 0.0::FLOAT;
        RETURN;
    END IF;
    
    -- Get abstraction metrics
    SELECT 
        concrete_ref_count,
        abstracted_ref_count,
        abstraction_score
    INTO v_concrete_count, v_abstracted_count, v_abstraction_score
    FROM safety.abstraction_metrics
    WHERE memory_id = p_memory_id;
    
    -- Validate completeness
    IF v_concrete_count > 0 THEN
        RETURN QUERY SELECT FALSE, 
            format('Memory contains %s concrete references', v_concrete_count),
            v_abstraction_score;
    ELSIF v_abstraction_score < 0.8 THEN
        RETURN QUERY SELECT FALSE,
            format('Abstraction score %.2f is below minimum threshold 0.8', v_abstraction_score),
            v_abstraction_score;
    ELSE
        RETURN QUERY SELECT TRUE, NULL::TEXT, v_abstraction_score;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to check temporal safety
CREATE OR REPLACE FUNCTION safety.check_temporal_safety(
    p_memory_id UUID,
    p_max_age_hours INTEGER DEFAULT 24
) RETURNS TABLE(is_stale BOOLEAN, age_hours NUMERIC, last_validation TIMESTAMPTZ) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        EXTRACT(EPOCH FROM (NOW() - validated_at)) / 3600 > p_max_age_hours AS is_stale,
        ROUND(EXTRACT(EPOCH FROM (NOW() - validated_at)) / 3600, 2) AS age_hours,
        validated_at AS last_validation
    FROM safety.validation_log
    WHERE memory_id = p_memory_id
        AND validation_result = TRUE
    ORDER BY validated_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VALIDATION TRIGGERS
-- =====================================================

-- Trigger function to enforce abstraction before insert
CREATE OR REPLACE FUNCTION safety.enforce_abstraction_before_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_validation_result RECORD;
    v_audit_id UUID;
BEGIN
    -- Skip if we're inserting into safety schema tables (avoid recursion)
    IF TG_TABLE_SCHEMA = 'safety' THEN
        RETURN NEW;
    END IF;
    
    -- Check if the table has a memory_id column
    IF TG_OP = 'INSERT' AND 
       EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema = TG_TABLE_SCHEMA 
               AND table_name = TG_TABLE_NAME 
               AND column_name = 'memory_id') THEN
        
        -- Validate abstraction completeness
        SELECT * INTO v_validation_result
        FROM safety.validate_abstraction_completeness(NEW.memory_id);
        
        IF NOT v_validation_result.is_valid THEN
            -- Log the violation
            INSERT INTO safety.audit_log (
                event_type, event_source, memory_id, action, 
                details, safety_impact
            ) VALUES (
                'SAFETY_VIOLATION', 
                TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                NEW.memory_id,
                'INSERT_BLOCKED',
                jsonb_build_object(
                    'reason', v_validation_result.error_message,
                    'safety_score', v_validation_result.safety_score
                ),
                'high'
            ) RETURNING id INTO v_audit_id;
            
            -- Raise exception
            RAISE EXCEPTION 'Safety violation: % (Audit ID: %)', 
                v_validation_result.error_message, v_audit_id
                USING ERRCODE = 'SA001';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger function to validate reference safety
CREATE OR REPLACE FUNCTION safety.validate_reference_safety()
RETURNS TRIGGER AS $$
DECLARE
    v_contains_concrete BOOLEAN;
BEGIN
    -- Check if concrete_value contains actual concrete references
    IF NEW.concrete_value IS NOT NULL THEN
        v_contains_concrete := safety.contains_concrete_references(NEW.concrete_value);
        
        -- Ensure abstracted_value is provided when concrete exists
        IF v_contains_concrete AND (NEW.abstracted_value IS NULL OR NEW.abstracted_value = '') THEN
            RAISE EXCEPTION 'Concrete reference detected without abstraction'
                USING ERRCODE = 'SA002';
        END IF;
        
        -- Ensure abstracted value doesn't contain concrete references
        IF safety.contains_concrete_references(NEW.abstracted_value) THEN
            RAISE EXCEPTION 'Abstracted value contains concrete references'
                USING ERRCODE = 'SA003';
        END IF;
    END IF;
    
    -- Set validation fields
    NEW.validation_timestamp := NOW();
    NEW.is_valid := NOT v_contains_concrete OR NEW.abstracted_value IS NOT NULL;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger function to prevent concrete exposure
CREATE OR REPLACE FUNCTION safety.prevent_concrete_exposure()
RETURNS TRIGGER AS $$
DECLARE
    v_column_name TEXT;
    v_column_value TEXT;
    v_contains_concrete BOOLEAN;
BEGIN
    -- Check text columns for concrete references
    FOR v_column_name IN 
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = TG_TABLE_SCHEMA 
        AND table_name = TG_TABLE_NAME
        AND data_type IN ('text', 'character varying')
    LOOP
        -- Get column value dynamically
        EXECUTE format('SELECT $1.%I::TEXT', v_column_name) 
        INTO v_column_value USING NEW;
        
        -- Skip if null or certain safe columns
        CONTINUE WHEN v_column_value IS NULL 
            OR v_column_name IN ('id', 'abstracted_value', 'pattern_template');
        
        -- Check for concrete references
        IF safety.contains_concrete_references(v_column_value) THEN
            -- Log attempt
            INSERT INTO safety.validation_log (
                memory_id, validation_type, validation_result,
                error_count, errors
            ) VALUES (
                CASE WHEN TG_TABLE_NAME = 'memory_references' THEN NEW.memory_id ELSE NULL END,
                'concrete_exposure',
                FALSE,
                1,
                jsonb_build_array(jsonb_build_object(
                    'column', v_column_name,
                    'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                    'message', 'Concrete reference detected in ' || v_column_name
                ))
            );
            
            RAISE EXCEPTION 'Concrete reference detected in column % without abstraction', v_column_name
                USING ERRCODE = 'SA004';
        END IF;
    END LOOP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger function for comprehensive audit logging
CREATE OR REPLACE FUNCTION safety.comprehensive_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB := NULL;
    v_new_data JSONB := NULL;
    v_changed_fields JSONB := NULL;
    v_safety_impact TEXT;
BEGIN
    -- Prepare data based on operation
    CASE TG_OP
        WHEN 'INSERT' THEN
            v_new_data := to_jsonb(NEW);
            v_safety_impact := 'low';
        WHEN 'UPDATE' THEN
            v_old_data := to_jsonb(OLD);
            v_new_data := to_jsonb(NEW);
            -- Calculate changed fields
            SELECT jsonb_object_agg(key, value) INTO v_changed_fields
            FROM jsonb_each(v_new_data)
            WHERE value IS DISTINCT FROM (v_old_data->key);
            -- Higher impact for safety-related changes
            IF v_changed_fields ? ANY(ARRAY['abstraction_score', 'safety_score', 'is_valid']) THEN
                v_safety_impact := 'medium';
            ELSE
                v_safety_impact := 'low';
            END IF;
        WHEN 'DELETE' THEN
            v_old_data := to_jsonb(OLD);
            v_safety_impact := 'medium';
    END CASE;
    
    -- Insert audit record
    INSERT INTO safety.audit_log (
        event_type,
        event_source,
        memory_id,
        action,
        details,
        safety_impact
    ) VALUES (
        'DATA_CHANGE',
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        CASE 
            WHEN TG_TABLE_NAME IN ('memory_references', 'abstraction_metrics') 
            THEN COALESCE(NEW.memory_id, OLD.memory_id)
            ELSE NULL 
        END,
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
$$ LANGUAGE plpgsql;

-- =====================================================
-- APPLY TRIGGERS TO TABLES
-- =====================================================

-- Apply validation trigger to memory_references
CREATE TRIGGER trg_validate_reference_safety
    BEFORE INSERT OR UPDATE ON safety.memory_references
    FOR EACH ROW
    EXECUTE FUNCTION safety.validate_reference_safety();

-- Apply audit triggers to all safety tables
CREATE TRIGGER trg_audit_abstraction_patterns
    AFTER INSERT OR UPDATE OR DELETE ON safety.abstraction_patterns
    FOR EACH ROW
    EXECUTE FUNCTION safety.comprehensive_audit_trail();

CREATE TRIGGER trg_audit_memory_references
    AFTER INSERT OR UPDATE OR DELETE ON safety.memory_references
    FOR EACH ROW
    EXECUTE FUNCTION safety.comprehensive_audit_trail();

CREATE TRIGGER trg_audit_abstraction_metrics
    AFTER INSERT OR UPDATE OR DELETE ON safety.abstraction_metrics
    FOR EACH ROW
    EXECUTE FUNCTION safety.comprehensive_audit_trail();

CREATE TRIGGER trg_audit_validation_log
    AFTER INSERT OR UPDATE OR DELETE ON safety.validation_log
    FOR EACH ROW
    EXECUTE FUNCTION safety.comprehensive_audit_trail();

CREATE TRIGGER trg_audit_reference_conflicts
    AFTER INSERT OR UPDATE OR DELETE ON safety.reference_conflicts
    FOR EACH ROW
    EXECUTE FUNCTION safety.comprehensive_audit_trail();

-- =====================================================
-- ADVANCED CHECK CONSTRAINTS
-- =====================================================

-- Add constraint to ensure abstraction metrics meet safety threshold
ALTER TABLE safety.abstraction_metrics
    ADD CONSTRAINT chk_minimum_abstraction_score 
    CHECK (abstraction_score >= 0.8 OR safety_violations IS NOT NULL);

-- Add constraint to ensure validation log consistency
ALTER TABLE safety.validation_log
    ADD CONSTRAINT chk_validation_consistency
    CHECK (
        (validation_result = TRUE AND error_count = 0) OR
        (validation_result = FALSE AND error_count > 0)
    );

-- Add constraint to ensure reference conflicts have valid severity
ALTER TABLE safety.reference_conflicts
    ADD CONSTRAINT chk_conflict_severity_required
    CHECK (severity IS NOT NULL);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all safety tables
ALTER TABLE safety.abstraction_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.memory_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.abstraction_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.validation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.reference_conflicts ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.audit_log ENABLE ROW LEVEL SECURITY;

-- Policy: Read-only access to failed validations
CREATE POLICY readonly_failed_validations ON safety.validation_log
    FOR SELECT
    USING (validation_result = FALSE);

-- Policy: Prevent updates to validated abstractions
CREATE POLICY no_update_validated_abstractions ON safety.memory_references
    FOR UPDATE
    USING (is_valid = TRUE)
    WITH CHECK (FALSE);

-- Policy: Restrict deletion of audit records
CREATE POLICY no_delete_audit ON safety.audit_log
    FOR DELETE
    USING (FALSE);

-- Policy: Control access based on safety scores
CREATE POLICY safety_score_access ON safety.abstraction_metrics
    FOR ALL
    USING (abstraction_score >= 0.8 OR current_user = 'ccp_admin');

-- Policy: Allow all operations for admin role (for development)
CREATE POLICY admin_full_access_patterns ON safety.abstraction_patterns
    FOR ALL
    TO ccp_admin
    USING (TRUE);

CREATE POLICY admin_full_access_references ON safety.memory_references
    FOR ALL
    TO ccp_admin
    USING (TRUE);

CREATE POLICY admin_full_access_metrics ON safety.abstraction_metrics
    FOR ALL
    TO ccp_admin
    USING (TRUE);

CREATE POLICY admin_full_access_validation ON safety.validation_log
    FOR ALL
    TO ccp_admin
    USING (TRUE);

CREATE POLICY admin_full_access_conflicts ON safety.reference_conflicts
    FOR ALL
    TO ccp_admin
    USING (TRUE);

CREATE POLICY admin_full_access_audit ON safety.audit_log
    FOR ALL
    TO ccp_admin
    USING (TRUE);

-- =====================================================
-- TEMPORAL SAFETY FUNCTIONS
-- =====================================================

-- Function to identify stale references
CREATE OR REPLACE FUNCTION safety.identify_stale_references(
    p_max_age_days INTEGER DEFAULT 30
) RETURNS TABLE(
    memory_id UUID,
    reference_id UUID,
    reference_type VARCHAR(50),
    age_days NUMERIC,
    last_validated TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mr.memory_id,
        mr.id AS reference_id,
        mr.reference_type,
        ROUND(EXTRACT(EPOCH FROM (NOW() - mr.validation_timestamp)) / 86400, 2) AS age_days,
        mr.validation_timestamp AS last_validated
    FROM safety.memory_references mr
    WHERE mr.validation_timestamp < NOW() - (p_max_age_days || ' days')::INTERVAL
        AND mr.is_valid = TRUE
    ORDER BY mr.validation_timestamp ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to detect reference drift
CREATE OR REPLACE FUNCTION safety.detect_reference_drift(
    p_memory_id UUID
) RETURNS TABLE(
    reference_type VARCHAR(50),
    original_pattern TEXT,
    current_pattern TEXT,
    drift_detected BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH current_patterns AS (
        SELECT DISTINCT
            ap.pattern_type,
            ap.pattern_template
        FROM safety.memory_references mr
        JOIN safety.abstraction_patterns ap ON ap.pattern_type = mr.reference_type
        WHERE mr.memory_id = p_memory_id
            AND mr.is_valid = TRUE
    ),
    historical_patterns AS (
        SELECT DISTINCT
            vl.metadata->>'pattern_type' AS pattern_type,
            vl.metadata->>'pattern_template' AS pattern_template
        FROM safety.validation_log vl
        WHERE vl.memory_id = p_memory_id
            AND vl.validation_type = 'abstraction'
            AND vl.validation_result = TRUE
            AND vl.validated_at < NOW() - INTERVAL '7 days'
    )
    SELECT 
        COALESCE(cp.pattern_type, hp.pattern_type) AS reference_type,
        hp.pattern_template AS original_pattern,
        cp.pattern_template AS current_pattern,
        cp.pattern_template IS DISTINCT FROM hp.pattern_template AS drift_detected
    FROM current_patterns cp
    FULL OUTER JOIN historical_patterns hp 
        ON cp.pattern_type = hp.pattern_type
    WHERE cp.pattern_template IS DISTINCT FROM hp.pattern_template;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SAFETY VIOLATION VIEWS
-- =====================================================

-- View for safety violations summary
CREATE OR REPLACE VIEW safety.violations_summary AS
SELECT 
    DATE_TRUNC('hour', validated_at) AS hour,
    validation_type,
    COUNT(*) FILTER (WHERE validation_result = FALSE) AS failed_count,
    COUNT(*) AS total_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE validation_result = FALSE) / NULLIF(COUNT(*), 0), 
        2
    ) AS failure_rate,
    AVG(safety_score) FILTER (WHERE safety_score IS NOT NULL) AS avg_safety_score
FROM safety.validation_log
WHERE validated_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', validated_at), validation_type
ORDER BY hour DESC, failed_count DESC;

-- View for unresolved conflicts
CREATE OR REPLACE VIEW safety.unresolved_conflicts AS
SELECT 
    rc.memory_id,
    rc.conflict_type,
    rc.severity,
    rc.detected_at,
    EXTRACT(EPOCH FROM (NOW() - rc.detected_at)) / 3600 AS hours_unresolved,
    mr.reference_type,
    mr.abstracted_value
FROM safety.reference_conflicts rc
JOIN safety.memory_references mr ON mr.id = rc.reference_id
WHERE rc.resolution_status = 'unresolved'
ORDER BY 
    CASE rc.severity 
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    rc.detected_at ASC;

-- =====================================================
-- TESTING HELPERS
-- =====================================================

-- Function to test safety constraints
CREATE OR REPLACE FUNCTION safety.test_safety_constraints()
RETURNS TABLE(
    test_name TEXT,
    test_passed BOOLEAN,
    error_message TEXT
) AS $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_error_message TEXT;
BEGIN
    -- Test 1: Cannot insert memory reference with concrete value and no abstraction
    BEGIN
        INSERT INTO safety.memory_references (
            memory_id, reference_type, concrete_value, abstracted_value
        ) VALUES (
            v_test_memory_id, 'file_path', '/home/user/secret.txt', NULL
        );
        RETURN QUERY SELECT 'reject_concrete_without_abstraction', FALSE, 'Test should have failed';
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'reject_concrete_without_abstraction', TRUE, NULL;
    END;
    
    -- Test 2: Cannot insert abstracted value containing concrete references
    BEGIN
        INSERT INTO safety.memory_references (
            memory_id, reference_type, concrete_value, abstracted_value
        ) VALUES (
            v_test_memory_id, 'file_path', '/home/user/file.txt', '/home/user/abstracted.txt'
        );
        RETURN QUERY SELECT 'reject_concrete_in_abstraction', FALSE, 'Test should have failed';
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'reject_concrete_in_abstraction', TRUE, NULL;
    END;
    
    -- Test 3: Can insert properly abstracted reference
    BEGIN
        INSERT INTO safety.memory_references (
            memory_id, reference_type, concrete_value, abstracted_value
        ) VALUES (
            v_test_memory_id, 'file_path', '/home/user/file.txt', '<user_home>/file.txt'
        );
        RETURN QUERY SELECT 'accept_proper_abstraction', TRUE, NULL;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_error_message = MESSAGE_TEXT;
        RETURN QUERY SELECT 'accept_proper_abstraction', FALSE, v_error_message;
    END;
    
    -- Clean up test data
    DELETE FROM safety.memory_references WHERE memory_id = v_test_memory_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- GRANTS FOR APPLICATION ROLE
-- =====================================================

-- Create application role if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ccp_app') THEN
        CREATE ROLE ccp_app;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ccp_admin') THEN
        CREATE ROLE ccp_admin;
    END IF;
END$$;

-- Grant usage on schema
GRANT USAGE ON SCHEMA safety TO ccp_app, ccp_admin;

-- Grant appropriate permissions to app role
GRANT SELECT, INSERT ON safety.memory_references TO ccp_app;
GRANT SELECT ON safety.abstraction_patterns TO ccp_app;
GRANT SELECT, INSERT, UPDATE ON safety.abstraction_metrics TO ccp_app;
GRANT SELECT, INSERT ON safety.validation_log TO ccp_app;
GRANT SELECT, INSERT, UPDATE ON safety.reference_conflicts TO ccp_app;
GRANT INSERT ON safety.audit_log TO ccp_app;

-- Grant all permissions to admin role
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA safety TO ccp_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA safety TO ccp_admin;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA safety TO ccp_admin;

-- =====================================================
-- MIGRATION COMPLETION
-- =====================================================

-- Log migration completion
INSERT INTO safety.audit_log (
    event_type,
    event_source,
    action,
    details,
    safety_impact
) VALUES (
    'MIGRATION',
    '001_safety_enforcement.sql',
    'COMPLETED',
    jsonb_build_object(
        'description', 'Added validation triggers, RLS policies, and safety constraints',
        'triggers_added', 6,
        'policies_added', 12,
        'constraints_added', 3,
        'functions_added', 8,
        'timestamp', NOW()
    ),
    'high'
);

-- Add comment
COMMENT ON SCHEMA safety IS 'Safety-first schema with comprehensive validation triggers and RLS policies (v1.1)';