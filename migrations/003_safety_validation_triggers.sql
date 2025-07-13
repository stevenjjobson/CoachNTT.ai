-- ===============================================
-- Safety Validation Triggers Migration (003)
-- ===============================================
-- Comprehensive trigger system for safety enforcement
-- PREVENTS any concrete references from entering the database
-- ===============================================

BEGIN;

-- ===============================================
-- Trigger Functions for Safety Validation
-- ===============================================

-- Function to detect concrete references in text
CREATE OR REPLACE FUNCTION safety.detect_concrete_references(content TEXT)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    violations JSONB := '[]'::jsonb;
    violation JSONB;
BEGIN
    -- File path detection
    IF content ~ '/(?:home|Users)/[a-zA-Z0-9_.-]+' THEN
        violation := jsonb_build_object(
            'type', 'file_path',
            'pattern', 'absolute_path',
            'severity', 'critical',
            'message', 'Absolute file path detected'
        );
        violations := violations || violation;
    END IF;
    
    -- Windows path detection
    IF content ~ '[A-Z]:\\[a-zA-Z0-9_\\.-]+' THEN
        violation := jsonb_build_object(
            'type', 'file_path',
            'pattern', 'windows_path', 
            'severity', 'critical',
            'message', 'Windows file path detected'
        );
        violations := violations || violation;
    END IF;
    
    -- IP address detection
    IF content ~ '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' THEN
        violation := jsonb_build_object(
            'type', 'network',
            'pattern', 'ip_address',
            'severity', 'high',
            'message', 'IP address detected'
        );
        violations := violations || violation;
    END IF;
    
    -- URL detection with specific hosts
    IF content ~ 'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' THEN
        violation := jsonb_build_object(
            'type', 'network',
            'pattern', 'concrete_url',
            'severity', 'high', 
            'message', 'Concrete URL detected'
        );
        violations := violations || violation;
    END IF;
    
    -- Credential patterns
    IF content ~* '(password|secret|token|key|api_key)\s*[:=]\s*["\'][^"\']+["\']' THEN
        violation := jsonb_build_object(
            'type', 'credential',
            'pattern', 'credential_value',
            'severity', 'critical',
            'message', 'Credential value detected'
        );
        violations := violations || violation;
    END IF;
    
    -- Database connection strings
    IF content ~* '(postgresql|mysql|mongodb)://[a-zA-Z0-9:@.-]+' THEN
        violation := jsonb_build_object(
            'type', 'database',
            'pattern', 'connection_string',
            'severity', 'critical',
            'message', 'Database connection string detected'
        );
        violations := violations || violation;
    END IF;
    
    -- Container/service names with specific identifiers
    IF content ~ '[a-zA-Z0-9_-]+_[0-9a-f]{8,}' THEN
        violation := jsonb_build_object(
            'type', 'container',
            'pattern', 'container_id',
            'severity', 'medium',
            'message', 'Container/service identifier detected'
        );
        violations := violations || violation;
    END IF;
    
    -- Personal email addresses
    IF content ~ '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' THEN
        violation := jsonb_build_object(
            'type', 'personal_data',
            'pattern', 'email_address',
            'severity', 'high',
            'message', 'Email address detected'
        );
        violations := violations || violation;
    END IF;
    
    RETURN violations;
END;
$$;

-- Function to calculate abstraction score
CREATE OR REPLACE FUNCTION safety.calculate_abstraction_score(
    content TEXT,
    concrete_refs JSONB DEFAULT '[]'::jsonb
)
RETURNS DECIMAL(3,2)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    total_length INTEGER;
    placeholder_count INTEGER;
    concrete_ref_count INTEGER;
    score DECIMAL(3,2);
BEGIN
    total_length := length(content);
    
    -- Count placeholders (positive score contribution)
    placeholder_count := array_length(
        regexp_split_to_array(content, '<[a-zA-Z][a-zA-Z0-9_]*>'), 1
    ) - 1;
    
    -- Count concrete references (negative score contribution)
    concrete_ref_count := jsonb_array_length(concrete_refs);
    
    -- Base score calculation
    IF total_length = 0 THEN
        RETURN 0.0;
    END IF;
    
    -- Score formula: base on placeholder ratio, penalize concrete refs
    score := LEAST(1.0, 
        (placeholder_count::DECIMAL * 0.3) + 
        (CASE WHEN concrete_ref_count = 0 THEN 0.7 ELSE GREATEST(0.0, 0.7 - (concrete_ref_count * 0.2)) END)
    );
    
    -- Minimum requirements
    IF concrete_ref_count > 0 THEN
        score := LEAST(score, 0.5); -- Cap at 0.5 if any concrete refs
    END IF;
    
    IF placeholder_count = 0 AND concrete_ref_count > 0 THEN
        score := 0.0; -- Zero score if no abstractions but has concrete refs
    END IF;
    
    RETURN GREATEST(0.0, score);
END;
$$;

-- Function to validate abstraction quality
CREATE OR REPLACE FUNCTION safety.validate_abstraction_quality(
    content TEXT,
    min_score DECIMAL(3,2) DEFAULT 0.8
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    result JSONB;
    violations JSONB;
    score DECIMAL(3,2);
    has_placeholders BOOLEAN;
BEGIN
    -- Detect concrete references
    violations := safety.detect_concrete_references(content);
    
    -- Calculate abstraction score
    score := safety.calculate_abstraction_score(content, violations);
    
    -- Check for placeholders
    has_placeholders := content ~ '<[a-zA-Z][a-zA-Z0-9_]*>';
    
    -- Build result
    result := jsonb_build_object(
        'score', score,
        'violations', violations,
        'has_placeholders', has_placeholders,
        'meets_minimum', score >= min_score,
        'violation_count', jsonb_array_length(violations),
        'validated_at', EXTRACT(EPOCH FROM NOW())
    );
    
    RETURN result;
END;
$$;

-- ===============================================
-- Trigger Function for Memory Abstractions
-- ===============================================

CREATE OR REPLACE FUNCTION safety.validate_memory_abstraction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    validation_result JSONB;
    content_to_validate TEXT;
    quality_record_id UUID;
    content_hash VARCHAR(64);
BEGIN
    -- Combine all text content for validation
    content_to_validate := COALESCE(NEW.abstracted_content::text, '') || ' ' || 
                          COALESCE(NEW.abstracted_prompt, '') || ' ' ||
                          COALESCE(NEW.abstracted_response, '');
    
    -- Generate content hash
    content_hash := encode(sha256(content_to_validate::bytea), 'hex');
    
    -- Validate abstraction quality
    validation_result := safety.validate_abstraction_quality(content_to_validate, 0.8);
    
    -- Check if validation passes minimum requirements
    IF NOT (validation_result->>'meets_minimum')::boolean THEN
        RAISE EXCEPTION 'Safety validation failed: Abstraction score %.2f below minimum 0.80. Violations: %',
            (validation_result->>'score')::decimal,
            validation_result->'violations';
    END IF;
    
    -- Ensure safety score matches calculated score
    NEW.safety_score := (validation_result->>'score')::decimal;
    
    -- Set validation status
    NEW.validation_status := CASE 
        WHEN (validation_result->>'violation_count')::integer = 0 THEN 'validated'
        WHEN (validation_result->>'score')::decimal >= 0.8 THEN 'validated'
        ELSE 'rejected'
    END;
    
    -- Create or update quality metrics record
    INSERT INTO safety.abstraction_quality_metrics (
        content_hash,
        abstraction_score,
        concrete_reference_count,
        placeholder_count,
        safety_violations,
        validation_passed,
        processing_time_ms
    ) VALUES (
        content_hash,
        (validation_result->>'score')::decimal,
        (validation_result->>'violation_count')::integer,
        (SELECT count(*) FROM regexp_split_to_table(content_to_validate, '<[a-zA-Z][a-zA-Z0-9_]*>')),
        validation_result->'violations',
        (validation_result->>'meets_minimum')::boolean,
        EXTRACT(MILLISECONDS FROM (NOW() - NEW.created_at))::integer
    ) ON CONFLICT (content_hash) DO UPDATE SET
        validation_passed = EXCLUDED.validation_passed,
        validated_at = NOW()
    RETURNING id INTO quality_record_id;
    
    -- Link to quality metrics
    NEW.quality_metrics_id := quality_record_id;
    
    -- Update timestamps
    NEW.updated_at := NOW();
    
    -- Log validation event
    INSERT INTO audit.safety_validations (
        memory_id,
        validation_type,
        input_content_hash,
        abstraction_score,
        concrete_refs_found,
        validation_result,
        violation_details,
        processing_time_ms
    ) VALUES (
        NEW.memory_id,
        'memory_abstraction',
        content_hash,
        (validation_result->>'score')::decimal,
        (validation_result->>'violation_count')::integer,
        CASE WHEN (validation_result->>'meets_minimum')::boolean THEN 'passed' ELSE 'failed' END,
        validation_result->'violations',
        EXTRACT(MILLISECONDS FROM (NOW() - NEW.created_at))::integer
    );
    
    RETURN NEW;
END;
$$;

-- ===============================================
-- Trigger Function for Cognitive Memory
-- ===============================================

CREATE OR REPLACE FUNCTION safety.validate_cognitive_memory()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    abstraction_record RECORD;
BEGIN
    -- Verify abstraction exists and is valid
    SELECT ma.safety_score, ma.validation_status 
    INTO abstraction_record
    FROM safety.memory_abstractions ma 
    WHERE ma.memory_id = NEW.abstraction_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invalid abstraction reference: abstraction_id % does not exist', NEW.abstraction_id;
    END IF;
    
    IF abstraction_record.validation_status != 'validated' THEN
        RAISE EXCEPTION 'Cannot reference unvalidated abstraction: status is %', abstraction_record.validation_status;
    END IF;
    
    IF abstraction_record.safety_score < 0.8 THEN
        RAISE EXCEPTION 'Cannot reference low-safety abstraction: score %.2f below minimum 0.80', abstraction_record.safety_score;
    END IF;
    
    -- Validate metadata doesn't contain concrete references
    IF NEW.metadata::text ~ '/(?:home|Users)/[a-zA-Z0-9_.-]+' OR
       NEW.metadata::text ~ '[A-Z]:\\[a-zA-Z0-9_\\.-]+' OR
       NEW.metadata::text ~ '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' THEN
        RAISE EXCEPTION 'Metadata contains concrete references';
    END IF;
    
    -- Set validation flag
    NEW.is_validated := true;
    NEW.updated_at := NOW();
    
    -- Update access tracking
    IF TG_OP = 'UPDATE' THEN
        NEW.access_count := OLD.access_count + 1;
        NEW.last_accessed := NOW();
    END IF;
    
    -- Log security event
    INSERT INTO audit.security_events (
        event_type,
        event_details,
        session_id,
        severity
    ) VALUES (
        'memory_validation',
        jsonb_build_object(
            'memory_id', NEW.id,
            'abstraction_id', NEW.abstraction_id,
            'safety_score', abstraction_record.safety_score,
            'operation', TG_OP
        ),
        NEW.session_id,
        'INFO'
    );
    
    RETURN NEW;
END;
$$;

-- ===============================================
-- Update Timestamp Trigger Function
-- ===============================================

CREATE OR REPLACE FUNCTION safety.update_modified_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

-- ===============================================
-- Audit Trail Trigger Function
-- ===============================================

CREATE OR REPLACE FUNCTION audit.log_table_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    operation_details JSONB;
BEGIN
    -- Build operation details
    operation_details := jsonb_build_object(
        'table_name', TG_TABLE_NAME,
        'schema_name', TG_TABLE_SCHEMA,
        'operation', TG_OP,
        'timestamp', NOW()
    );
    
    -- Add row data based on operation
    CASE TG_OP
        WHEN 'INSERT' THEN
            operation_details := operation_details || jsonb_build_object('new_row', to_jsonb(NEW));
        WHEN 'UPDATE' THEN
            operation_details := operation_details || jsonb_build_object(
                'old_row', to_jsonb(OLD),
                'new_row', to_jsonb(NEW)
            );
        WHEN 'DELETE' THEN
            operation_details := operation_details || jsonb_build_object('old_row', to_jsonb(OLD));
    END CASE;
    
    -- Log to audit table
    INSERT INTO audit.security_events (
        event_type,
        event_details,
        severity
    ) VALUES (
        'table_modification',
        operation_details,
        CASE 
            WHEN TG_TABLE_SCHEMA = 'safety' THEN 'WARNING'
            WHEN TG_TABLE_NAME = 'cognitive_memory' THEN 'INFO'
            ELSE 'DEBUG'
        END
    );
    
    -- Return appropriate record
    CASE TG_OP
        WHEN 'DELETE' THEN RETURN OLD;
        ELSE RETURN NEW;
    END CASE;
END;
$$;

-- ===============================================
-- Create Triggers on Safety Tables
-- ===============================================

-- Memory abstractions validation (CRITICAL)
DROP TRIGGER IF EXISTS trigger_validate_memory_abstraction ON safety.memory_abstractions;
CREATE TRIGGER trigger_validate_memory_abstraction
    BEFORE INSERT OR UPDATE ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.validate_memory_abstraction();

-- Cognitive memory validation (CRITICAL)
DROP TRIGGER IF EXISTS trigger_validate_cognitive_memory ON public.cognitive_memory;
CREATE TRIGGER trigger_validate_cognitive_memory
    BEFORE INSERT OR UPDATE ON public.cognitive_memory
    FOR EACH ROW EXECUTE FUNCTION safety.validate_cognitive_memory();

-- ===============================================
-- Update Timestamp Triggers
-- ===============================================

-- Safety tables
DROP TRIGGER IF EXISTS trigger_update_abstraction_patterns_timestamp ON safety.abstraction_patterns;
CREATE TRIGGER trigger_update_abstraction_patterns_timestamp
    BEFORE UPDATE ON safety.abstraction_patterns
    FOR EACH ROW EXECUTE FUNCTION safety.update_modified_column();

DROP TRIGGER IF EXISTS trigger_update_memory_abstractions_timestamp ON safety.memory_abstractions;
CREATE TRIGGER trigger_update_memory_abstractions_timestamp
    BEFORE UPDATE ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.update_modified_column();

-- Main memory table
DROP TRIGGER IF EXISTS trigger_update_cognitive_memory_timestamp ON public.cognitive_memory;
CREATE TRIGGER trigger_update_cognitive_memory_timestamp
    BEFORE UPDATE ON public.cognitive_memory
    FOR EACH ROW EXECUTE FUNCTION safety.update_modified_column();

-- ===============================================
-- Audit Trail Triggers
-- ===============================================

-- Audit all changes to safety tables
DROP TRIGGER IF EXISTS trigger_audit_memory_abstractions ON safety.memory_abstractions;
CREATE TRIGGER trigger_audit_memory_abstractions
    AFTER INSERT OR UPDATE OR DELETE ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION audit.log_table_changes();

DROP TRIGGER IF EXISTS trigger_audit_cognitive_memory ON public.cognitive_memory;
CREATE TRIGGER trigger_audit_cognitive_memory
    AFTER INSERT OR UPDATE OR DELETE ON public.cognitive_memory
    FOR EACH ROW EXECUTE FUNCTION audit.log_table_changes();

-- ===============================================
-- Prevent Direct Manipulation of Audit Tables
-- ===============================================

CREATE OR REPLACE FUNCTION audit.prevent_audit_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit tables are immutable. Operation % not allowed on %.%', 
            TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END;
$$;

-- Protect audit tables
DROP TRIGGER IF EXISTS trigger_protect_security_events ON audit.security_events;
CREATE TRIGGER trigger_protect_security_events
    BEFORE UPDATE OR DELETE ON audit.security_events
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_audit_modification();

DROP TRIGGER IF EXISTS trigger_protect_safety_validations ON audit.safety_validations;
CREATE TRIGGER trigger_protect_safety_validations
    BEFORE UPDATE OR DELETE ON audit.safety_validations
    FOR EACH ROW EXECUTE FUNCTION audit.prevent_audit_modification();

-- ===============================================
-- Performance Monitoring Triggers
-- ===============================================

CREATE OR REPLACE FUNCTION safety.monitor_performance()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    processing_time INTEGER;
BEGIN
    processing_time := EXTRACT(MILLISECONDS FROM (NOW() - NEW.created_at))::integer;
    
    -- Log slow operations
    IF processing_time > 1000 THEN  -- > 1 second
        INSERT INTO audit.security_events (
            event_type,
            event_details,
            severity
        ) VALUES (
            'slow_operation',
            jsonb_build_object(
                'table_name', TG_TABLE_NAME,
                'processing_time_ms', processing_time,
                'operation', TG_OP
            ),
            'WARNING'
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Monitor safety validation performance
DROP TRIGGER IF EXISTS trigger_monitor_abstraction_performance ON safety.memory_abstractions;
CREATE TRIGGER trigger_monitor_abstraction_performance
    AFTER INSERT ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.monitor_performance();

-- ===============================================
-- Verification and Comments
-- ===============================================

COMMENT ON FUNCTION safety.detect_concrete_references(TEXT) IS 'Detects various types of concrete references in text content';
COMMENT ON FUNCTION safety.calculate_abstraction_score(TEXT, JSONB) IS 'Calculates abstraction quality score (0.0-1.0)';
COMMENT ON FUNCTION safety.validate_abstraction_quality(TEXT, DECIMAL) IS 'Comprehensive abstraction validation with scoring';
COMMENT ON FUNCTION safety.validate_memory_abstraction() IS 'CRITICAL: Validates all memory abstractions before storage';
COMMENT ON FUNCTION safety.validate_cognitive_memory() IS 'CRITICAL: Validates cognitive memory references';

-- Test trigger installation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE trigger_name = 'trigger_validate_memory_abstraction'
        AND event_object_table = 'memory_abstractions'
    ) THEN
        RAISE EXCEPTION 'Critical safety trigger not installed: memory_abstraction_validation';
    END IF;
    
    RAISE NOTICE 'All safety validation triggers installed successfully';
END $$;

COMMIT;