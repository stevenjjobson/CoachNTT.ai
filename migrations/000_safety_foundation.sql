-- Migration: 000_safety_foundation.sql
-- Purpose: Create safety-first database schema for Cognitive Coding Partner
-- Date: 2025-01-13
-- Description: Foundation tables for abstraction enforcement and safety validation

-- Ensure required extensions are installed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create safety schema for abstraction enforcement
CREATE SCHEMA IF NOT EXISTS safety;

-- Set search path to include safety schema
SET search_path TO safety, public;

-- =====================================================
-- ABSTRACTION PATTERNS CATALOG
-- =====================================================
CREATE TABLE safety.abstraction_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(50) NOT NULL CHECK (
        pattern_type IN (
            'file_path', 'container', 'variable', 'function', 
            'url', 'config', 'identifier', 'timestamp', 'token'
        )
    ),
    pattern_template TEXT NOT NULL,
    example_concrete TEXT,
    example_abstract TEXT,
    safety_level INTEGER NOT NULL CHECK (safety_level BETWEEN 1 AND 5),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for pattern lookups
CREATE INDEX idx_abstraction_patterns_type ON safety.abstraction_patterns(pattern_type);

-- =====================================================
-- MEMORY REFERENCE TRACKING
-- =====================================================
CREATE TABLE safety.memory_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    concrete_value TEXT,
    abstracted_value TEXT NOT NULL,
    is_valid BOOLEAN DEFAULT true,
    validation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    validation_message TEXT,
    detection_confidence FLOAT CHECK (detection_confidence BETWEEN 0 AND 1),
    context_snippet TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for reference queries
CREATE INDEX idx_memory_references_memory_id ON safety.memory_references(memory_id);
CREATE INDEX idx_memory_references_type ON safety.memory_references(reference_type);
CREATE INDEX idx_memory_references_validity ON safety.memory_references(is_valid) 
    WHERE is_valid = false;

-- =====================================================
-- ABSTRACTION QUALITY METRICS
-- =====================================================
CREATE TABLE safety.abstraction_metrics (
    memory_id UUID PRIMARY KEY,
    abstraction_score FLOAT NOT NULL CHECK (abstraction_score BETWEEN 0 AND 1),
    concrete_ref_count INTEGER DEFAULT 0,
    abstracted_ref_count INTEGER NOT NULL,
    safety_violations TEXT[],
    coverage_percentage FLOAT CHECK (coverage_percentage BETWEEN 0 AND 100),
    validation_errors JSONB DEFAULT '[]'::jsonb,
    validation_warnings JSONB DEFAULT '[]'::jsonb,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metrics_version VARCHAR(20) DEFAULT '1.0.0'
);

-- Create index for low-scoring abstractions
CREATE INDEX idx_abstraction_metrics_low_score ON safety.abstraction_metrics(abstraction_score) 
    WHERE abstraction_score < 0.8;

-- =====================================================
-- SAFETY VALIDATION LOG
-- =====================================================
CREATE TABLE safety.validation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID,
    validation_type VARCHAR(50) NOT NULL CHECK (
        validation_type IN (
            'input', 'storage', 'retrieval', 'abstraction', 
            'consistency', 'security', 'completeness'
        )
    ),
    validation_result BOOLEAN NOT NULL,
    safety_score FLOAT CHECK (safety_score BETWEEN 0 AND 1),
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validator_version VARCHAR(20)
);

-- Create indexes for validation queries
CREATE INDEX idx_validation_log_memory_id ON safety.validation_log(memory_id);
CREATE INDEX idx_validation_log_type ON safety.validation_log(validation_type);
CREATE INDEX idx_validation_log_failed ON safety.validation_log(validation_result) 
    WHERE validation_result = false;
CREATE INDEX idx_validation_log_timestamp ON safety.validation_log(validated_at DESC);

-- =====================================================
-- REFERENCE CONFLICT TRACKING
-- =====================================================
CREATE TABLE safety.reference_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL,
    reference_id UUID NOT NULL REFERENCES safety.memory_references(id),
    conflict_type VARCHAR(50) NOT NULL CHECK (
        conflict_type IN (
            'temporal_mismatch', 'missing_reference', 
            'type_change', 'pattern_deviation', 'stale_reference'
        )
    ),
    original_context TEXT,
    current_context TEXT,
    conflict_details JSONB NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolution_status VARCHAR(20) DEFAULT 'unresolved',
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Create indexes for conflict queries
CREATE INDEX idx_reference_conflicts_memory ON safety.reference_conflicts(memory_id);
CREATE INDEX idx_reference_conflicts_unresolved ON safety.reference_conflicts(resolution_status) 
    WHERE resolution_status = 'unresolved';

-- =====================================================
-- SAFETY AUDIT TRAIL
-- =====================================================
CREATE TABLE safety.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    event_source VARCHAR(100) NOT NULL,
    memory_id UUID,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_impact VARCHAR(20) CHECK (safety_impact IN ('none', 'low', 'medium', 'high')),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for audit queries
CREATE INDEX idx_audit_log_event_type ON safety.audit_log(event_type);
CREATE INDEX idx_audit_log_memory_id ON safety.audit_log(memory_id);
CREATE INDEX idx_audit_log_timestamp ON safety.audit_log(created_at DESC);
CREATE INDEX idx_audit_log_safety_impact ON safety.audit_log(safety_impact) 
    WHERE safety_impact IN ('medium', 'high');

-- =====================================================
-- ABSTRACTION PATTERNS - SEED DATA
-- =====================================================
INSERT INTO safety.abstraction_patterns (pattern_type, pattern_template, example_concrete, example_abstract, safety_level, description) VALUES
    ('file_path', '<project_root>/{path}', '/home/user/project/src/main.py', '<project_root>/src/main.py', 5, 'Project file paths'),
    ('file_path', '<user_home>/{path}', '/home/john/documents/file.txt', '<user_home>/documents/file.txt', 5, 'User home directory paths'),
    ('file_path', '<temp_dir>/{file}', '/tmp/cache_abc123.tmp', '<temp_dir>/cache_*.tmp', 4, 'Temporary file paths'),
    ('identifier', '<user_id>', '12345', '<user_id>', 5, 'User identifiers'),
    ('identifier', '<{type}_id>', 'order_id = 98765', 'order_id = <order_id>', 5, 'Typed identifiers'),
    ('url', '<api_base_url>/{path}', 'https://api.example.com/v1/users/123', '<api_base_url>/users/<user_id>', 5, 'API endpoints'),
    ('container', '<{service}_container>', 'myapp-web-prod-v1.2.3', '<web_container>', 4, 'Container names'),
    ('token', '<api_key>', 'sk_live_abcd1234...', '<api_key>', 5, 'API keys and tokens'),
    ('config', '<{setting}_value>', 'DEBUG=true', 'DEBUG=<debug_flag>', 3, 'Configuration values');

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to check if a memory has complete abstraction
CREATE OR REPLACE FUNCTION safety.is_fully_abstracted(p_memory_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_concrete_count INTEGER;
    v_abstracted_count INTEGER;
BEGIN
    SELECT 
        concrete_ref_count,
        abstracted_ref_count
    INTO v_concrete_count, v_abstracted_count
    FROM safety.abstraction_metrics
    WHERE memory_id = p_memory_id;
    
    RETURN v_concrete_count = 0 AND v_abstracted_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate safety score
CREATE OR REPLACE FUNCTION safety.calculate_safety_score(
    p_memory_id UUID,
    p_abstraction_coverage FLOAT,
    p_error_count INTEGER,
    p_warning_count INTEGER
)
RETURNS FLOAT AS $$
DECLARE
    v_score FLOAT;
BEGIN
    -- Base score from coverage
    v_score := p_abstraction_coverage * 0.5;
    
    -- Penalty for errors
    v_score := v_score - (p_error_count * 0.1);
    
    -- Smaller penalty for warnings
    v_score := v_score - (p_warning_count * 0.02);
    
    -- Add points for full abstraction
    IF p_abstraction_coverage = 1.0 THEN
        v_score := v_score + 0.3;
    END IF;
    
    -- Ensure score is between 0 and 1
    RETURN GREATEST(0, LEAST(1, v_score));
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION safety.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_abstraction_patterns_timestamp
    BEFORE UPDATE ON safety.abstraction_patterns
    FOR EACH ROW
    EXECUTE FUNCTION safety.update_updated_at();

-- =====================================================
-- PERMISSIONS (for production use)
-- =====================================================
-- GRANT USAGE ON SCHEMA safety TO ccp_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA safety TO ccp_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA safety TO ccp_app;

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON SCHEMA safety IS 'Safety-first schema for abstraction enforcement and validation';
COMMENT ON TABLE safety.abstraction_patterns IS 'Catalog of abstraction patterns for different reference types';
COMMENT ON TABLE safety.memory_references IS 'Tracks all references found in memories and their abstractions';
COMMENT ON TABLE safety.abstraction_metrics IS 'Quality metrics for memory abstractions';
COMMENT ON TABLE safety.validation_log IS 'Log of all validation operations performed';
COMMENT ON TABLE safety.reference_conflicts IS 'Tracks conflicts between stored and current references';
COMMENT ON TABLE safety.audit_log IS 'Comprehensive audit trail for safety-related operations';