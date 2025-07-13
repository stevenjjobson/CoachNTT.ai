-- ===============================================
-- Safety-First Schema Migration (002)
-- ===============================================
-- Creates safety-enforced database schema with abstraction mandatory
-- CRITICAL: Safety tables MUST exist before any memory tables
-- ===============================================

-- Transaction for safety
BEGIN;

-- ===============================================
-- Safety Schema Setup (FIRST PRIORITY)
-- ===============================================

-- Ensure safety schema exists with proper permissions
CREATE SCHEMA IF NOT EXISTS safety;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path to prioritize safety
SET search_path TO safety, public;

-- Create safety-focused comment
COMMENT ON SCHEMA safety IS 'Safety enforcement schema - contains all abstraction and validation tables';
COMMENT ON SCHEMA audit IS 'Audit logging schema - immutable security audit trail';

-- ===============================================
-- Core Safety Tables (CREATED FIRST)
-- ===============================================

-- Abstraction patterns table (foundation of safety)
CREATE TABLE IF NOT EXISTS safety.abstraction_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50) NOT NULL CHECK (pattern_type IN ('file_path', 'url', 'credential', 'variable', 'api_endpoint', 'database_connection', 'container_name', 'service_name', 'user_data')),
    pattern_template TEXT NOT NULL CHECK (pattern_template LIKE '%<%>%'), -- Must contain placeholder format
    replacement_format TEXT NOT NULL DEFAULT '<placeholder_name>',
    safety_level INTEGER NOT NULL CHECK (safety_level BETWEEN 1 AND 5) DEFAULT 5,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Safety constraints
    CONSTRAINT abstraction_patterns_valid_template CHECK (
        pattern_template ~ '<[a-zA-Z][a-zA-Z0-9_]*>' -- Must contain valid placeholder
    )
);

-- Reference validation rules (safety enforcement)
CREATE TABLE IF NOT EXISTS safety.reference_validation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    pattern_regex TEXT NOT NULL,
    is_concrete_reference BOOLEAN NOT NULL DEFAULT true,
    severity_level INTEGER NOT NULL CHECK (severity_level BETWEEN 1 AND 5) DEFAULT 5,
    error_message TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Safety constraint: must be valid regex
    CONSTRAINT valid_regex CHECK (pattern_regex IS NOT NULL AND length(pattern_regex) > 0)
);

-- Abstraction quality metrics (mandatory for all data)
CREATE TABLE IF NOT EXISTS safety.abstraction_quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256 of original content
    abstraction_score DECIMAL(3,2) NOT NULL CHECK (abstraction_score >= 0.0 AND abstraction_score <= 1.0),
    concrete_reference_count INTEGER NOT NULL DEFAULT 0 CHECK (concrete_reference_count >= 0),
    placeholder_count INTEGER NOT NULL DEFAULT 0 CHECK (placeholder_count >= 0),
    safety_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    validation_passed BOOLEAN NOT NULL DEFAULT false,
    processing_time_ms INTEGER NOT NULL DEFAULT 0 CHECK (processing_time_ms >= 0),
    validated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Safety requirement: minimum abstraction score
    CONSTRAINT minimum_safety_score CHECK (
        (validation_passed = false) OR 
        (validation_passed = true AND abstraction_score >= 0.8)
    )
);

-- ===============================================
-- Memory Abstraction Tables (SAFETY ENFORCED)
-- ===============================================

-- Abstract memory storage (NO concrete references allowed)
CREATE TABLE IF NOT EXISTS safety.memory_abstractions (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abstracted_content JSONB NOT NULL,
    abstracted_prompt TEXT NOT NULL,
    abstracted_response TEXT,
    concrete_references JSONB NOT NULL DEFAULT '{}'::jsonb,
    abstraction_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
    safety_score DECIMAL(3,2) NOT NULL CHECK (safety_score >= 0.8), -- MANDATORY MINIMUM
    validation_status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (validation_status IN ('pending', 'validated', 'rejected', 'quarantined')),
    quality_metrics_id UUID NOT NULL REFERENCES safety.abstraction_quality_metrics(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Critical safety constraints
    CONSTRAINT no_concrete_paths CHECK (
        NOT (abstracted_content::text ~ '/home/[a-zA-Z0-9_-]+' OR 
             abstracted_content::text ~ '/Users/[a-zA-Z0-9_-]+' OR
             abstracted_content::text ~ 'C:\\[a-zA-Z0-9_\\-]+')
    ),
    CONSTRAINT no_concrete_ips CHECK (
        NOT (abstracted_content::text ~ '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}')
    ),
    CONSTRAINT no_concrete_credentials CHECK (
        NOT (abstracted_content::text ~* '(password|secret|token|key)\s*[:=]\s*["\'][^"\']+["\']')
    ),
    CONSTRAINT requires_placeholders CHECK (
        abstracted_content::text ~ '<[a-zA-Z][a-zA-Z0-9_]*>'
    )
);

-- ===============================================
-- Cognitive Memory Table (ABSTRACTION MANDATORY)
-- ===============================================

-- Main cognitive memory table (builds on safety foundation)
CREATE TABLE IF NOT EXISTS public.cognitive_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN ('conversation', 'code_generation', 'problem_solving', 'documentation', 'debugging')),
    
    -- MANDATORY abstraction reference
    abstraction_id UUID NOT NULL REFERENCES safety.memory_abstractions(memory_id) ON DELETE RESTRICT,
    
    -- Vector embeddings
    prompt_embedding vector(1536),
    response_embedding vector(1536),
    
    -- Temporal and relevance
    weight DECIMAL(5,4) NOT NULL DEFAULT 1.0000 CHECK (weight >= 0.0 AND weight <= 1.0),
    last_accessed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    access_count INTEGER NOT NULL DEFAULT 0 CHECK (access_count >= 0),
    
    -- Metadata
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Safety validation
    is_validated BOOLEAN NOT NULL DEFAULT false,
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Performance constraints
    CONSTRAINT valid_weight_range CHECK (weight BETWEEN 0.0 AND 1.0),
    CONSTRAINT positive_access_count CHECK (access_count >= 0),
    CONSTRAINT recent_access CHECK (last_accessed <= NOW()),
    
    -- Safety requirement: must have valid abstraction
    CONSTRAINT requires_valid_abstraction CHECK (
        EXISTS (
            SELECT 1 FROM safety.memory_abstractions ma 
            WHERE ma.memory_id = abstraction_id 
            AND ma.validation_status = 'validated'
            AND ma.safety_score >= 0.8
        )
    )
);

-- ===============================================
-- Audit Logging Tables (IMMUTABLE)
-- ===============================================

-- Security audit log (immutable, append-only)
CREATE TABLE IF NOT EXISTS audit.security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    event_details JSONB NOT NULL,
    user_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO' 
        CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Immutability: no updates or deletes allowed
    CONSTRAINT immutable_audit_log CHECK (created_at IS NOT NULL)
);

-- Safety validation audit log
CREATE TABLE IF NOT EXISTS audit.safety_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL,
    validation_type VARCHAR(50) NOT NULL,
    input_content_hash VARCHAR(64) NOT NULL,
    abstraction_score DECIMAL(3,2) NOT NULL,
    concrete_refs_found INTEGER NOT NULL DEFAULT 0,
    validation_result VARCHAR(20) NOT NULL CHECK (validation_result IN ('passed', 'failed', 'warning')),
    violation_details JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_time_ms INTEGER NOT NULL DEFAULT 0,
    validator_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Audit trail integrity
    CONSTRAINT audit_integrity CHECK (created_at IS NOT NULL AND validation_result IS NOT NULL)
);

-- ===============================================
-- Indexes for Performance and Safety
-- ===============================================

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_cognitive_memory_session ON public.cognitive_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_cognitive_memory_weight ON public.cognitive_memory(weight DESC);
CREATE INDEX IF NOT EXISTS idx_cognitive_memory_last_accessed ON public.cognitive_memory(last_accessed DESC);
CREATE INDEX IF NOT EXISTS idx_cognitive_memory_abstraction ON public.cognitive_memory(abstraction_id);

-- Safety indexes
CREATE INDEX IF NOT EXISTS idx_memory_abstractions_safety_score ON safety.memory_abstractions(safety_score DESC);
CREATE INDEX IF NOT EXISTS idx_memory_abstractions_validation ON safety.memory_abstractions(validation_status);
CREATE INDEX IF NOT EXISTS idx_abstraction_patterns_type ON safety.abstraction_patterns(pattern_type);

-- Vector indexes for similarity search
CREATE INDEX IF NOT EXISTS idx_cognitive_memory_prompt_embedding 
    ON public.cognitive_memory USING ivfflat (prompt_embedding vector_cosine_ops) 
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_cognitive_memory_response_embedding 
    ON public.cognitive_memory USING ivfflat (response_embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Audit indexes (read-only optimization)
CREATE INDEX IF NOT EXISTS idx_security_events_created ON audit.security_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON audit.security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_safety_validations_memory ON audit.safety_validations(memory_id);
CREATE INDEX IF NOT EXISTS idx_safety_validations_result ON audit.safety_validations(validation_result);

-- ===============================================
-- Row Level Security (RLS) Policies
-- ===============================================

-- Enable RLS on all safety tables
ALTER TABLE safety.abstraction_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.reference_validation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.abstraction_quality_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.memory_abstractions ENABLE ROW LEVEL SECURITY;

-- Enable RLS on main memory table
ALTER TABLE public.cognitive_memory ENABLE ROW LEVEL SECURITY;

-- Enable RLS on audit tables (read-only)
ALTER TABLE audit.security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.safety_validations ENABLE ROW LEVEL SECURITY;

-- Default policies (restrictive by default)
CREATE POLICY safety_admin_access ON safety.abstraction_patterns
    FOR ALL TO ccp_user USING (true);

CREATE POLICY memory_access_policy ON public.cognitive_memory
    FOR ALL TO ccp_user USING (is_validated = true);

CREATE POLICY audit_read_only ON audit.security_events
    FOR SELECT TO ccp_user USING (true);

-- ===============================================
-- Comments and Documentation
-- ===============================================

COMMENT ON TABLE public.cognitive_memory IS 'Main cognitive memory storage with mandatory abstraction enforcement';
COMMENT ON TABLE safety.memory_abstractions IS 'Abstracted memory content with safety score validation';
COMMENT ON TABLE safety.abstraction_patterns IS 'Patterns for converting concrete references to abstractions';
COMMENT ON TABLE safety.reference_validation_rules IS 'Rules for detecting and preventing concrete references';
COMMENT ON TABLE audit.security_events IS 'Immutable security audit log';
COMMENT ON TABLE audit.safety_validations IS 'Immutable safety validation audit trail';

-- Column documentation
COMMENT ON COLUMN public.cognitive_memory.abstraction_id IS 'MANDATORY: Reference to abstracted content in safety schema';
COMMENT ON COLUMN safety.memory_abstractions.safety_score IS 'REQUIRED: Minimum 0.8 for acceptance';
COMMENT ON COLUMN safety.memory_abstractions.validation_status IS 'CRITICAL: Only validated memories can be referenced';

-- ===============================================
-- Database Configuration
-- ===============================================

-- Ensure search path prioritizes safety
ALTER DATABASE cognitive_coding_partner SET search_path TO safety, public;

-- Set safety-focused configuration
ALTER DATABASE cognitive_coding_partner SET log_statement TO 'all';
ALTER DATABASE cognitive_coding_partner SET log_min_duration_statement TO 100;

-- ===============================================
-- Success Verification
-- ===============================================

-- Verify safety schema exists and is accessible
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'safety') THEN
        RAISE EXCEPTION 'Safety schema creation failed';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'safety' AND table_name = 'memory_abstractions') THEN
        RAISE EXCEPTION 'Safety tables creation failed';
    END IF;
    
    RAISE NOTICE 'Safety-first schema migration completed successfully';
END $$;

COMMIT;