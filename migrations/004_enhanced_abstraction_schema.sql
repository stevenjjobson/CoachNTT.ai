-- ===============================================
-- Enhanced Abstraction Schema Migration (004)
-- ===============================================
-- Additional tables and constraints for comprehensive abstraction enforcement
-- Builds on foundation from migrations 002 and 003
-- ===============================================

BEGIN;

-- ===============================================
-- Abstraction Templates Table
-- ===============================================
-- Reusable abstraction patterns for consistent conversion

CREATE TABLE IF NOT EXISTS safety.abstraction_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(100) NOT NULL UNIQUE,
    template_category VARCHAR(50) NOT NULL CHECK (template_category IN (
        'file_system', 'network', 'database', 'cloud_service', 
        'credentials', 'personal_data', 'code_reference', 'configuration'
    )),
    input_pattern TEXT NOT NULL,
    output_template TEXT NOT NULL CHECK (output_template ~ '<[a-zA-Z][a-zA-Z0-9_]*>'),
    example_input TEXT NOT NULL,
    example_output TEXT NOT NULL,
    validation_regex TEXT,
    priority INTEGER NOT NULL DEFAULT 100 CHECK (priority BETWEEN 1 AND 1000),
    is_active BOOLEAN NOT NULL DEFAULT true,
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    success_rate DECIMAL(3,2) DEFAULT 1.0 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL DEFAULT CURRENT_USER,
    
    -- Ensure template has placeholders
    CONSTRAINT template_has_placeholders CHECK (
        output_template ~ '<[a-zA-Z][a-zA-Z0-9_]*>' AND
        array_length(regexp_split_to_array(output_template, '<[a-zA-Z][a-zA-Z0-9_]*>'), 1) >= 2
    ),
    
    -- Ensure example demonstrates the pattern
    CONSTRAINT example_validates CHECK (
        example_output ~ '<[a-zA-Z][a-zA-Z0-9_]*>' AND
        NOT (example_output ~ example_input)
    )
);

-- ===============================================
-- Reference Mappings Table
-- ===============================================
-- Track all concrete to abstract conversions for consistency

CREATE TABLE IF NOT EXISTS safety.reference_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concrete_hash VARCHAR(64) NOT NULL, -- SHA-256 of concrete reference
    concrete_type VARCHAR(50) NOT NULL,
    abstracted_form TEXT NOT NULL CHECK (abstracted_form ~ '<[a-zA-Z][a-zA-Z0-9_]*>'),
    template_id UUID REFERENCES safety.abstraction_templates(id),
    first_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    use_count INTEGER NOT NULL DEFAULT 1 CHECK (use_count > 0),
    context_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    verification_score DECIMAL(3,2) CHECK (verification_score >= 0.0 AND verification_score <= 1.0),
    
    -- Unique mapping per concrete reference
    CONSTRAINT unique_concrete_mapping UNIQUE (concrete_hash, concrete_type),
    
    -- Abstracted form must be different from concrete
    CONSTRAINT proper_abstraction CHECK (
        length(abstracted_form) > 0 AND
        abstracted_form ~ '<[a-zA-Z][a-zA-Z0-9_]*>'
    )
);

-- ===============================================
-- Validation History Table
-- ===============================================
-- Complete history of all validation attempts for analysis

CREATE TABLE IF NOT EXISTS safety.validation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    content_hash VARCHAR(64) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content_length INTEGER NOT NULL CHECK (content_length >= 0),
    validation_result VARCHAR(20) NOT NULL CHECK (validation_result IN (
        'passed', 'failed', 'warning', 'quarantined', 'error'
    )),
    safety_score DECIMAL(3,2) CHECK (safety_score >= 0.0 AND safety_score <= 1.0),
    concrete_refs_found INTEGER NOT NULL DEFAULT 0 CHECK (concrete_refs_found >= 0),
    placeholders_found INTEGER NOT NULL DEFAULT 0 CHECK (placeholders_found >= 0),
    violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
    validator_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    client_context JSONB DEFAULT '{}'::jsonb,
    
    -- Performance tracking
    cpu_usage_percent DECIMAL(5,2) CHECK (cpu_usage_percent >= 0.0 AND cpu_usage_percent <= 100.0),
    memory_usage_mb INTEGER CHECK (memory_usage_mb >= 0),
    
    -- Indexing for analysis
    CONSTRAINT validation_timestamp_order CHECK (validation_timestamp <= NOW())
);

-- ===============================================
-- Abstraction Cache Table
-- ===============================================
-- High-performance cache for validated abstractions

CREATE TABLE IF NOT EXISTS safety.abstraction_cache (
    cache_key VARCHAR(128) PRIMARY KEY, -- Composite key from content characteristics
    abstracted_content TEXT NOT NULL,
    safety_score DECIMAL(3,2) NOT NULL CHECK (safety_score >= 0.8),
    template_ids UUID[] NOT NULL DEFAULT '{}',
    validation_metadata JSONB NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0 CHECK (hit_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    is_valid BOOLEAN NOT NULL DEFAULT true,
    
    -- Cache must contain abstractions
    CONSTRAINT cache_has_abstractions CHECK (
        abstracted_content ~ '<[a-zA-Z][a-zA-Z0-9_]*>'
    ),
    
    -- Expiration must be future
    CONSTRAINT valid_expiration CHECK (expires_at > created_at)
);

-- ===============================================
-- Pattern Learning Table
-- ===============================================
-- Learn from rejected patterns to improve detection

CREATE TABLE IF NOT EXISTS safety.pattern_learning (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text TEXT NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    detection_count INTEGER NOT NULL DEFAULT 1 CHECK (detection_count > 0),
    false_positive_count INTEGER NOT NULL DEFAULT 0 CHECK (false_positive_count >= 0),
    true_positive_rate DECIMAL(3,2) DEFAULT 1.0 CHECK (true_positive_rate >= 0.0 AND true_positive_rate <= 1.0),
    suggested_regex TEXT,
    is_confirmed BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT false,
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    confirmed_by VARCHAR(100),
    confirmed_at TIMESTAMP WITH TIME ZONE,
    
    -- Learning metrics
    confidence_score DECIMAL(3,2) DEFAULT 0.5 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    
    -- Unique pattern per type
    CONSTRAINT unique_pattern_type UNIQUE (pattern_text, pattern_type)
);

-- ===============================================
-- Abstraction Rules Engine Table
-- ===============================================
-- Dynamic rules for complex abstraction scenarios

CREATE TABLE IF NOT EXISTS safety.abstraction_rules_engine (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN (
        'simple_replace', 'regex_replace', 'contextual', 'composite', 'custom_function'
    )),
    rule_definition JSONB NOT NULL,
    priority INTEGER NOT NULL DEFAULT 500 CHECK (priority BETWEEN 1 AND 1000),
    applies_to_types VARCHAR(50)[] NOT NULL DEFAULT '{}',
    preconditions JSONB DEFAULT '{}'::jsonb,
    postconditions JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    test_cases JSONB NOT NULL DEFAULT '[]'::jsonb,
    success_count INTEGER NOT NULL DEFAULT 0 CHECK (success_count >= 0),
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Rule must have valid definition
    CONSTRAINT valid_rule_definition CHECK (
        jsonb_typeof(rule_definition) = 'object' AND
        rule_definition ? 'action'
    ),
    
    -- Test cases required for activation
    CONSTRAINT test_cases_required CHECK (
        NOT is_active OR jsonb_array_length(test_cases) >= 3
    )
);

-- ===============================================
-- Quarantine Table
-- ===============================================
-- Temporary storage for content failing validation

CREATE TABLE IF NOT EXISTS safety.quarantine (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    source_table VARCHAR(100) NOT NULL,
    source_id UUID,
    quarantine_reason JSONB NOT NULL,
    safety_score DECIMAL(3,2) CHECK (safety_score >= 0.0 AND safety_score < 0.8),
    remediation_attempts INTEGER NOT NULL DEFAULT 0 CHECK (remediation_attempts >= 0),
    remediation_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (remediation_status IN (
        'pending', 'in_progress', 'resolved', 'rejected', 'expired'
    )),
    suggested_abstraction TEXT,
    quarantined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    
    -- Quarantine must have valid reason
    CONSTRAINT valid_quarantine_reason CHECK (
        jsonb_typeof(quarantine_reason) = 'object' AND
        quarantine_reason ? 'violations'
    )
);

-- ===============================================
-- Indexes for Performance
-- ===============================================

-- Template lookup optimization
CREATE INDEX IF NOT EXISTS idx_abstraction_templates_category 
    ON safety.abstraction_templates(template_category) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_abstraction_templates_priority 
    ON safety.abstraction_templates(priority DESC) WHERE is_active = true;

-- Reference mapping optimization
CREATE INDEX IF NOT EXISTS idx_reference_mappings_concrete 
    ON safety.reference_mappings(concrete_hash);
CREATE INDEX IF NOT EXISTS idx_reference_mappings_type 
    ON safety.reference_mappings(concrete_type);
CREATE INDEX IF NOT EXISTS idx_reference_mappings_last_used 
    ON safety.reference_mappings(last_used DESC);

-- Validation history analysis
CREATE INDEX IF NOT EXISTS idx_validation_history_timestamp 
    ON safety.validation_history(validation_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_validation_history_result 
    ON safety.validation_history(validation_result);
CREATE INDEX IF NOT EXISTS idx_validation_history_hash 
    ON safety.validation_history(content_hash);

-- Cache performance
CREATE INDEX IF NOT EXISTS idx_abstraction_cache_expires 
    ON safety.abstraction_cache(expires_at) WHERE is_valid = true;
CREATE INDEX IF NOT EXISTS idx_abstraction_cache_accessed 
    ON safety.abstraction_cache(last_accessed DESC) WHERE is_valid = true;

-- Pattern learning
CREATE INDEX IF NOT EXISTS idx_pattern_learning_confidence 
    ON safety.pattern_learning(confidence_score DESC) WHERE is_active = false;
CREATE INDEX IF NOT EXISTS idx_pattern_learning_type 
    ON safety.pattern_learning(pattern_type) WHERE is_confirmed = true;

-- Rules engine
CREATE INDEX IF NOT EXISTS idx_rules_engine_priority 
    ON safety.abstraction_rules_engine(priority DESC) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_rules_engine_type 
    ON safety.abstraction_rules_engine(rule_type) WHERE is_active = true;

-- Quarantine management
CREATE INDEX IF NOT EXISTS idx_quarantine_status 
    ON safety.quarantine(remediation_status) WHERE remediation_status != 'resolved';
CREATE INDEX IF NOT EXISTS idx_quarantine_expires 
    ON safety.quarantine(expires_at) WHERE remediation_status = 'pending';

-- ===============================================
-- Update Triggers for New Tables
-- ===============================================

-- Update timestamp triggers
CREATE TRIGGER trigger_update_abstraction_templates_timestamp
    BEFORE UPDATE ON safety.abstraction_templates
    FOR EACH ROW EXECUTE FUNCTION safety.update_modified_column();

CREATE TRIGGER trigger_update_rules_engine_timestamp
    BEFORE UPDATE ON safety.abstraction_rules_engine
    FOR EACH ROW EXECUTE FUNCTION safety.update_modified_column();

-- Cache management trigger
CREATE OR REPLACE FUNCTION safety.update_cache_access()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.last_accessed := NOW();
    NEW.hit_count := OLD.hit_count + 1;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_update_cache_access
    BEFORE UPDATE ON safety.abstraction_cache
    FOR EACH ROW 
    WHEN (OLD.abstracted_content = NEW.abstracted_content)
    EXECUTE FUNCTION safety.update_cache_access();

-- Reference mapping usage tracking
CREATE OR REPLACE FUNCTION safety.track_mapping_usage()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.abstracted_form = NEW.abstracted_form THEN
        NEW.last_used := NOW();
        NEW.use_count := OLD.use_count + 1;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_track_mapping_usage
    BEFORE UPDATE ON safety.reference_mappings
    FOR EACH ROW EXECUTE FUNCTION safety.track_mapping_usage();

-- ===============================================
-- Row Level Security Policies
-- ===============================================

-- Enable RLS on new tables
ALTER TABLE safety.abstraction_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.reference_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.validation_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.abstraction_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.pattern_learning ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.abstraction_rules_engine ENABLE ROW LEVEL SECURITY;
ALTER TABLE safety.quarantine ENABLE ROW LEVEL SECURITY;

-- Create default policies
CREATE POLICY template_access ON safety.abstraction_templates
    FOR ALL TO ccp_user USING (true);

CREATE POLICY mapping_access ON safety.reference_mappings
    FOR ALL TO ccp_user USING (true);

CREATE POLICY history_read_only ON safety.validation_history
    FOR SELECT TO ccp_user USING (true);

CREATE POLICY cache_access ON safety.abstraction_cache
    FOR ALL TO ccp_user USING (is_valid = true);

CREATE POLICY learning_admin ON safety.pattern_learning
    FOR ALL TO ccp_user USING (true);

CREATE POLICY rules_admin ON safety.abstraction_rules_engine
    FOR ALL TO ccp_user USING (true);

CREATE POLICY quarantine_admin ON safety.quarantine
    FOR ALL TO ccp_user USING (true);

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON TABLE safety.abstraction_templates IS 'Reusable templates for consistent abstraction patterns';
COMMENT ON TABLE safety.reference_mappings IS 'Tracks all concrete to abstract conversions for consistency';
COMMENT ON TABLE safety.validation_history IS 'Complete audit trail of all validation attempts';
COMMENT ON TABLE safety.abstraction_cache IS 'High-performance cache for validated abstractions';
COMMENT ON TABLE safety.pattern_learning IS 'Machine learning data for improving pattern detection';
COMMENT ON TABLE safety.abstraction_rules_engine IS 'Dynamic rules for complex abstraction scenarios';
COMMENT ON TABLE safety.quarantine IS 'Temporary storage for content failing safety validation';

-- ===============================================
-- Initial Data: Core Abstraction Templates
-- ===============================================

INSERT INTO safety.abstraction_templates (
    template_name, template_category, input_pattern, output_template,
    example_input, example_output, validation_regex, priority
) VALUES
    -- File system patterns
    ('unix_home_path', 'file_system', '/home/[username]/*', '<user_home>/<path>', 
     '/home/john/documents/file.txt', '<user_home>/documents/file.txt',
     '^/home/[a-zA-Z0-9_-]+/', 900),
    
    ('windows_user_path', 'file_system', 'C:\Users\[username]\*', '<user_dir>\<path>',
     'C:\Users\Alice\Desktop\project', '<user_dir>\Desktop\project',
     '^[A-Z]:\\Users\\[a-zA-Z0-9_-]+\\', 900),
    
    -- Network patterns
    ('ip_address', 'network', '[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}', '<ip_address>',
     '192.168.1.100', '<ip_address>',
     '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', 950),
    
    ('api_endpoint', 'network', 'https://[domain]/api/[endpoint]', '<api_base>/<endpoint>',
     'https://api.example.com/v1/users', '<api_base>/v1/users',
     '^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/', 850),
    
    -- Database patterns
    ('postgres_conn', 'database', 'postgresql://[user]:[pass]@[host]:[port]/[db]', 
     'postgresql://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>',
     'postgresql://admin:secret@localhost:5432/myapp',
     'postgresql://<db_user>:<db_pass>@<db_host>:<db_port>/<db_name>',
     '^postgresql://.*:.*@.*:\d+/.*$', 950),
    
    -- Credential patterns
    ('api_key', 'credentials', '[a-zA-Z0-9_-]{32,}', '<api_key>',
     'sk_test_4eC39HqLyjWDarjtT1zdp7dc', '<api_key>',
     '^[a-zA-Z0-9_-]{32,}$', 1000)
ON CONFLICT (template_name) DO NOTHING;

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    -- Count new tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'safety'
    AND table_name IN (
        'abstraction_templates', 'reference_mappings', 'validation_history',
        'abstraction_cache', 'pattern_learning', 'abstraction_rules_engine', 'quarantine'
    );
    
    IF table_count != 7 THEN
        RAISE EXCEPTION 'Enhanced abstraction schema creation incomplete: expected 7 tables, found %', table_count;
    END IF;
    
    RAISE NOTICE 'Enhanced abstraction schema created successfully with % new tables', table_count;
END $$;

COMMIT;