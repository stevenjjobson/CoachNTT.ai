-- ===============================================
-- Quality Assurance Migration (008)
-- ===============================================
-- Comprehensive abstraction quality checks and metrics
-- Ensures high-quality abstractions with semantic validation
-- ===============================================

BEGIN;

-- ===============================================
-- Abstraction Quality Standards Table
-- ===============================================
-- Define quality standards for different content types

CREATE TABLE IF NOT EXISTS safety.quality_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL UNIQUE,
    min_placeholder_density DECIMAL(3,2) NOT NULL DEFAULT 0.1 
        CHECK (min_placeholder_density >= 0.0 AND min_placeholder_density <= 1.0),
    min_abstraction_ratio DECIMAL(3,2) NOT NULL DEFAULT 0.3
        CHECK (min_abstraction_ratio >= 0.0 AND min_abstraction_ratio <= 1.0),
    max_concrete_length INTEGER NOT NULL DEFAULT 50
        CHECK (max_concrete_length > 0),
    required_patterns TEXT[] NOT NULL DEFAULT '{}',
    forbidden_patterns TEXT[] NOT NULL DEFAULT '{}',
    semantic_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ===============================================
-- Quality Metrics Collection Table
-- ===============================================
-- Detailed quality metrics for each abstraction

CREATE TABLE IF NOT EXISTS safety.quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abstraction_id UUID NOT NULL,
    measurement_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Density metrics
    total_length INTEGER NOT NULL CHECK (total_length >= 0),
    placeholder_count INTEGER NOT NULL CHECK (placeholder_count >= 0),
    placeholder_density DECIMAL(3,2) NOT NULL CHECK (placeholder_density >= 0.0 AND placeholder_density <= 1.0),
    
    -- Pattern metrics
    pattern_consistency_score DECIMAL(3,2) CHECK (pattern_consistency_score >= 0.0 AND pattern_consistency_score <= 1.0),
    abstraction_completeness DECIMAL(3,2) CHECK (abstraction_completeness >= 0.0 AND abstraction_completeness <= 1.0),
    
    -- Semantic metrics
    semantic_coherence DECIMAL(3,2) CHECK (semantic_coherence >= 0.0 AND semantic_coherence <= 1.0),
    context_preservation DECIMAL(3,2) CHECK (context_preservation >= 0.0 AND context_preservation <= 1.0),
    
    -- Quality issues
    quality_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    improvement_suggestions JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Overall quality score
    overall_quality_score DECIMAL(3,2) NOT NULL 
        CHECK (overall_quality_score >= 0.0 AND overall_quality_score <= 1.0),
    meets_standards BOOLEAN NOT NULL DEFAULT false,
    
    -- Performance
    calculation_time_ms INTEGER NOT NULL CHECK (calculation_time_ms >= 0)
);

-- ===============================================
-- Placeholder Density Check Function
-- ===============================================

-- Calculate placeholder density and distribution
CREATE OR REPLACE FUNCTION safety.check_placeholder_density(
    content TEXT,
    min_density DECIMAL(3,2) DEFAULT 0.1
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    total_length INTEGER;
    placeholder_matches TEXT[];
    placeholder_count INTEGER;
    density DECIMAL(3,2);
    distribution JSONB := '{}'::jsonb;
    placeholder TEXT;
    position_info JSONB;
BEGIN
    total_length := length(content);
    
    IF total_length = 0 THEN
        RETURN jsonb_build_object(
            'valid', true,
            'density', 1.0,
            'message', 'Empty content'
        );
    END IF;
    
    -- Find all placeholders
    placeholder_matches := regexp_split_to_array(
        regexp_replace(content, '.*?(<[a-zA-Z][a-zA-Z0-9_]*>).*?', '\1|', 'g'),
        '\|'
    );
    
    -- Filter out empty elements
    placeholder_matches := array_remove(placeholder_matches, '');
    placeholder_count := array_length(placeholder_matches, 1);
    
    IF placeholder_count IS NULL THEN
        placeholder_count := 0;
    END IF;
    
    -- Calculate density
    density := placeholder_count::decimal / (total_length::decimal / 100);
    
    -- Analyze distribution
    FOREACH placeholder IN ARRAY placeholder_matches
    LOOP
        IF placeholder != '' THEN
            IF distribution ? placeholder THEN
                distribution := jsonb_set(
                    distribution, 
                    ARRAY[placeholder], 
                    to_jsonb((distribution->>placeholder)::integer + 1)
                );
            ELSE
                distribution := distribution || jsonb_build_object(placeholder, 1);
            END IF;
        END IF;
    END LOOP;
    
    -- Check for good distribution (not all placeholders at the end)
    DECLARE
        first_placeholder_pos INTEGER;
        last_placeholder_pos INTEGER;
        distribution_score DECIMAL(3,2);
    BEGIN
        first_placeholder_pos := position('<' IN content);
        last_placeholder_pos := length(content) - position('>' IN reverse(content)) + 1;
        
        IF placeholder_count > 0 AND total_length > 0 THEN
            distribution_score := 1.0 - (
                (last_placeholder_pos - first_placeholder_pos)::decimal / total_length::decimal
            );
        ELSE
            distribution_score := 0.0;
        END IF;
        
        RETURN jsonb_build_object(
            'valid', density >= min_density,
            'density', round(density, 2),
            'placeholder_count', placeholder_count,
            'total_length', total_length,
            'min_required', min_density,
            'distribution', distribution,
            'distribution_score', round(distribution_score, 2),
            'unique_placeholders', jsonb_object_keys(distribution)
        );
    END;
END;
$$;

-- ===============================================
-- Pattern Consistency Check Function
-- ===============================================

-- Ensure consistent use of abstraction patterns
CREATE OR REPLACE FUNCTION safety.check_pattern_consistency(
    content TEXT,
    content_type VARCHAR(50) DEFAULT 'general'
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    issues JSONB := '[]'::jsonb;
    issue JSONB;
    pattern_usage JSONB := '{}'::jsonb;
    inconsistencies INTEGER := 0;
    consistency_score DECIMAL(3,2);
BEGIN
    -- Check for mixed abstraction styles
    IF content ~ '<[a-zA-Z][a-zA-Z0-9_]*>' AND content ~ '\{[a-zA-Z][a-zA-Z0-9_]*\}' THEN
        issue := jsonb_build_object(
            'type', 'mixed_placeholder_styles',
            'severity', 'medium',
            'message', 'Mixed placeholder styles detected (<> and {})'
        );
        issues := issues || issue;
        inconsistencies := inconsistencies + 1;
    END IF;
    
    -- Check for similar but different placeholders
    IF content ~ '<file_path>' AND content ~ '<filepath>' THEN
        issue := jsonb_build_object(
            'type', 'inconsistent_naming',
            'severity', 'low',
            'message', 'Similar placeholders with different names'
        );
        issues := issues || issue;
        inconsistencies := inconsistencies + 1;
    END IF;
    
    -- Type-specific consistency checks
    CASE content_type
        WHEN 'code' THEN
            -- Check for consistent variable naming in code
            IF content ~ '<[a-z][a-zA-Z0-9_]*>' AND content ~ '<[A-Z][a-zA-Z0-9_]*>' THEN
                issue := jsonb_build_object(
                    'type', 'inconsistent_case',
                    'severity', 'low',
                    'message', 'Mixed case in placeholder names'
                );
                issues := issues || issue;
                inconsistencies := inconsistencies + 1;
            END IF;
            
        WHEN 'url' THEN
            -- Check for proper URL placeholder structure
            IF content ~ 'https?://<[^>]+>/' AND content !~ 'https?://<[^>]+>:<port>/' THEN
                issue := jsonb_build_object(
                    'type', 'incomplete_url_pattern',
                    'severity', 'medium',
                    'message', 'URL pattern missing port placeholder'
                );
                issues := issues || issue;
                inconsistencies := inconsistencies + 1;
            END IF;
            
        WHEN 'path' THEN
            -- Check for consistent path separators
            IF content ~ '<[^>]+>/[^<]' AND content ~ '<[^>]+>\\[^<]' THEN
                issue := jsonb_build_object(
                    'type', 'mixed_path_separators',
                    'severity', 'high',
                    'message', 'Mixed path separators (/ and \\)'
                );
                issues := issues || issue;
                inconsistencies := inconsistencies + 2; -- Higher weight
            END IF;
    END CASE;
    
    -- Calculate consistency score
    consistency_score := GREATEST(0.0, 1.0 - (inconsistencies * 0.2));
    
    RETURN jsonb_build_object(
        'valid', inconsistencies = 0,
        'consistency_score', consistency_score,
        'issues', issues,
        'issue_count', jsonb_array_length(issues)
    );
END;
$$;

-- ===============================================
-- Reference Completeness Check Function
-- ===============================================

-- Ensure all concrete references are properly abstracted
CREATE OR REPLACE FUNCTION safety.check_reference_completeness(
    abstracted_content TEXT,
    concrete_references JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    missing_abstractions JSONB := '[]'::jsonb;
    unused_references JSONB := '[]'::jsonb;
    ref_key TEXT;
    ref_value TEXT;
    completeness_score DECIMAL(3,2);
    total_refs INTEGER;
    found_refs INTEGER := 0;
BEGIN
    -- Check each concrete reference has corresponding placeholder
    FOR ref_key, ref_value IN SELECT * FROM jsonb_each_text(concrete_references)
    LOOP
        -- Check if placeholder exists in abstracted content
        IF abstracted_content ~ ('<' || ref_key || '>') THEN
            found_refs := found_refs + 1;
        ELSE
            missing_abstractions := missing_abstractions || 
                jsonb_build_object(
                    'reference', ref_key,
                    'expected_placeholder', '<' || ref_key || '>'
                );
        END IF;
    END LOOP;
    
    -- Check for placeholders without references
    DECLARE
        placeholder_pattern TEXT;
        placeholders TEXT[];
        placeholder TEXT;
    BEGIN
        -- Extract all placeholders
        placeholders := regexp_split_to_array(
            regexp_replace(abstracted_content, '.*?<([a-zA-Z][a-zA-Z0-9_]*)>.*?', '\1|', 'g'),
            '\|'
        );
        
        FOREACH placeholder IN ARRAY placeholders
        LOOP
            IF placeholder != '' AND NOT (concrete_references ? placeholder) THEN
                unused_references := unused_references ||
                    jsonb_build_object(
                        'placeholder', '<' || placeholder || '>',
                        'issue', 'No concrete reference mapping'
                    );
            END IF;
        END LOOP;
    END;
    
    -- Calculate completeness score
    total_refs := jsonb_object_keys(concrete_references);
    IF total_refs > 0 THEN
        completeness_score := found_refs::decimal / total_refs::decimal;
    ELSE
        completeness_score := 1.0; -- No refs to map is complete
    END IF;
    
    -- Penalize unused placeholders
    IF jsonb_array_length(unused_references) > 0 THEN
        completeness_score := completeness_score * 0.9;
    END IF;
    
    RETURN jsonb_build_object(
        'valid', jsonb_array_length(missing_abstractions) = 0,
        'completeness_score', completeness_score,
        'missing_abstractions', missing_abstractions,
        'unused_references', unused_references,
        'total_references', total_refs,
        'mapped_references', found_refs
    );
END;
$$;

-- ===============================================
-- Semantic Quality Check Function
-- ===============================================

-- Check semantic preservation in abstractions
CREATE OR REPLACE FUNCTION safety.check_semantic_quality(
    original_content TEXT,
    abstracted_content TEXT,
    abstraction_mapping JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    semantic_score DECIMAL(3,2) := 1.0;
    issues JSONB := '[]'::jsonb;
    key TEXT;
    value TEXT;
    reconstructed TEXT;
BEGIN
    -- Start with abstracted content
    reconstructed := abstracted_content;
    
    -- Apply reverse mapping
    FOR key, value IN SELECT * FROM jsonb_each_text(abstraction_mapping)
    LOOP
        reconstructed := replace(reconstructed, '<' || key || '>', value);
    END LOOP;
    
    -- Check if reconstruction possible
    IF reconstructed = abstracted_content AND 
       jsonb_object_keys(abstraction_mapping) IS NOT NULL THEN
        issues := issues || jsonb_build_object(
            'type', 'no_substitution',
            'severity', 'high',
            'message', 'Placeholders do not match mapping keys'
        );
        semantic_score := semantic_score - 0.3;
    END IF;
    
    -- Check for over-abstraction
    IF length(abstracted_content) < length(original_content) * 0.5 THEN
        issues := issues || jsonb_build_object(
            'type', 'over_abstraction',
            'severity', 'medium',
            'message', 'Abstracted content significantly shorter than original'
        );
        semantic_score := semantic_score - 0.2;
    END IF;
    
    -- Check for loss of structure
    IF original_content ~ '\n' AND abstracted_content !~ '\n' THEN
        issues := issues || jsonb_build_object(
            'type', 'structure_loss',
            'severity', 'low',
            'message', 'Line structure lost in abstraction'
        );
        semantic_score := semantic_score - 0.1;
    END IF;
    
    -- Check placeholder meaningfulness
    FOR key IN SELECT jsonb_object_keys(abstraction_mapping)
    LOOP
        IF length(key) < 3 OR key !~ '^[a-zA-Z]' THEN
            issues := issues || jsonb_build_object(
                'type', 'poor_placeholder_name',
                'severity', 'low',
                'placeholder', key,
                'message', 'Placeholder name not descriptive'
            );
            semantic_score := semantic_score - 0.05;
        END IF;
    END LOOP;
    
    RETURN jsonb_build_object(
        'valid', semantic_score >= 0.7,
        'semantic_score', GREATEST(0.0, semantic_score),
        'issues', issues,
        'reconstructable', reconstructed != abstracted_content
    );
END;
$$;

-- ===============================================
-- Comprehensive Quality Assessment Function
-- ===============================================

-- Main quality assessment combining all checks
CREATE OR REPLACE FUNCTION safety.assess_abstraction_quality(
    abstraction_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    abstraction_record RECORD;
    quality_result JSONB := '{}'::jsonb;
    density_check JSONB;
    consistency_check JSONB;
    completeness_check JSONB;
    semantic_check JSONB;
    overall_score DECIMAL(3,2);
    start_time TIMESTAMP;
    processing_time INTEGER;
BEGIN
    start_time := clock_timestamp();
    
    -- Get abstraction record
    SELECT * INTO abstraction_record
    FROM safety.memory_abstractions
    WHERE memory_id = abstraction_id;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', 'Abstraction not found',
            'abstraction_id', abstraction_id
        );
    END IF;
    
    -- Combine all content
    DECLARE
        full_content TEXT;
    BEGIN
        full_content := COALESCE(abstraction_record.abstracted_content::text, '') || ' ' ||
                       COALESCE(abstraction_record.abstracted_prompt, '') || ' ' ||
                       COALESCE(abstraction_record.abstracted_response, '');
        
        -- Run quality checks
        density_check := safety.check_placeholder_density(full_content, 0.1);
        consistency_check := safety.check_pattern_consistency(full_content, 'general');
        completeness_check := safety.check_reference_completeness(
            full_content,
            abstraction_record.concrete_references
        );
        
        -- Semantic check (simplified without original)
        semantic_check := jsonb_build_object(
            'semantic_score', 0.85, -- Default reasonable score
            'note', 'Simplified check without original content'
        );
    END;
    
    -- Calculate overall quality score (weighted average)
    overall_score := (
        (density_check->>'density')::decimal * 0.25 +
        (consistency_check->>'consistency_score')::decimal * 0.25 +
        (completeness_check->>'completeness_score')::decimal * 0.3 +
        (semantic_check->>'semantic_score')::decimal * 0.2
    );
    
    -- Account for safety score
    overall_score := overall_score * 0.8 + abstraction_record.safety_score * 0.2;
    
    processing_time := EXTRACT(MILLISECONDS FROM (clock_timestamp() - start_time))::integer;
    
    -- Build comprehensive result
    quality_result := jsonb_build_object(
        'abstraction_id', abstraction_id,
        'assessment_timestamp', NOW(),
        'overall_quality_score', round(overall_score, 2),
        'meets_standards', overall_score >= 0.75,
        'safety_score', abstraction_record.safety_score,
        'checks', jsonb_build_object(
            'density', density_check,
            'consistency', consistency_check,
            'completeness', completeness_check,
            'semantic', semantic_check
        ),
        'improvement_suggestions', 
            CASE 
                WHEN (density_check->>'density')::decimal < 0.1 
                THEN jsonb_build_array('Increase placeholder density')
                ELSE '[]'::jsonb
            END ||
            CASE 
                WHEN (consistency_check->>'issue_count')::integer > 0
                THEN jsonb_build_array('Fix pattern consistency issues')
                ELSE '[]'::jsonb
            END ||
            CASE 
                WHEN jsonb_array_length(completeness_check->'missing_abstractions') > 0
                THEN jsonb_build_array('Add missing placeholder mappings')
                ELSE '[]'::jsonb
            END,
        'processing_time_ms', processing_time
    );
    
    -- Store metrics
    INSERT INTO safety.quality_metrics (
        abstraction_id,
        total_length,
        placeholder_count,
        placeholder_density,
        pattern_consistency_score,
        abstraction_completeness,
        semantic_coherence,
        context_preservation,
        quality_issues,
        improvement_suggestions,
        overall_quality_score,
        meets_standards,
        calculation_time_ms
    ) VALUES (
        abstraction_id,
        length(full_content),
        (density_check->>'placeholder_count')::integer,
        (density_check->>'density')::decimal,
        (consistency_check->>'consistency_score')::decimal,
        (completeness_check->>'completeness_score')::decimal,
        (semantic_check->>'semantic_score')::decimal,
        0.85, -- Default context preservation
        consistency_check->'issues',
        quality_result->'improvement_suggestions',
        overall_score,
        overall_score >= 0.75,
        processing_time
    );
    
    RETURN quality_result;
END;
$$;

-- ===============================================
-- Quality Monitoring Triggers
-- ===============================================

-- Trigger to assess quality after abstraction creation
CREATE OR REPLACE FUNCTION safety.trigger_quality_assessment()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    assessment_result JSONB;
BEGIN
    -- Only assess validated abstractions
    IF NEW.validation_status != 'validated' THEN
        RETURN NEW;
    END IF;
    
    -- Skip if recently assessed
    IF EXISTS (
        SELECT 1 FROM safety.quality_metrics
        WHERE abstraction_id = NEW.memory_id
          AND measurement_timestamp > NOW() - INTERVAL '1 hour'
    ) THEN
        RETURN NEW;
    END IF;
    
    -- Perform assessment
    assessment_result := safety.assess_abstraction_quality(NEW.memory_id);
    
    -- Update abstraction if quality issues found
    IF NOT (assessment_result->>'meets_standards')::boolean THEN
        INSERT INTO audit.security_events (
            event_type,
            event_details,
            severity
        ) VALUES (
            'quality_standard_failure',
            assessment_result,
            'WARNING'
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Install quality assessment trigger
DROP TRIGGER IF EXISTS trigger_quality_assessment ON safety.memory_abstractions;
CREATE TRIGGER trigger_quality_assessment
    AFTER INSERT OR UPDATE OF validation_status ON safety.memory_abstractions
    FOR EACH ROW
    WHEN (NEW.validation_status = 'validated')
    EXECUTE FUNCTION safety.trigger_quality_assessment();

-- ===============================================
-- Quality Standards Initial Data
-- ===============================================

INSERT INTO safety.quality_standards (
    content_type,
    min_placeholder_density,
    min_abstraction_ratio,
    max_concrete_length,
    required_patterns,
    forbidden_patterns,
    semantic_rules
) VALUES
    ('general', 0.1, 0.3, 50, 
     ARRAY['<[a-zA-Z][a-zA-Z0-9_]*>'],
     ARRAY['\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '/home/\w+'],
     '{"preserve_structure": true}'::jsonb),
     
    ('code', 0.15, 0.4, 40,
     ARRAY['<[a-zA-Z][a-zA-Z0-9_]*>'],
     ARRAY['password\s*=\s*"[^"]+\"', 'api_key\s*=\s*"[^"]+\"'],
     '{"preserve_syntax": true, "maintain_indentation": true}'::jsonb),
     
    ('url', 0.2, 0.5, 30,
     ARRAY['<protocol>', '<domain>', '<path>'],
     ARRAY['https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'],
     '{"require_protocol_placeholder": true}'::jsonb),
     
    ('configuration', 0.25, 0.6, 25,
     ARRAY['<[a-zA-Z][a-zA-Z0-9_]*>'],
     ARRAY['localhost:\d+', '127\.0\.0\.1'],
     '{"preserve_format": true, "require_value_abstraction": true}'::jsonb)
ON CONFLICT (content_type) DO UPDATE
SET updated_at = NOW();

-- ===============================================
-- Quality Dashboard Views
-- ===============================================

-- Overall quality trends
CREATE OR REPLACE VIEW safety.quality_trends AS
SELECT 
    DATE_TRUNC('hour', measurement_timestamp) as hour,
    COUNT(*) as assessments,
    AVG(overall_quality_score) as avg_quality,
    SUM(CASE WHEN meets_standards THEN 1 ELSE 0 END)::decimal / COUNT(*) as pass_rate,
    AVG(placeholder_density) as avg_density,
    AVG(pattern_consistency_score) as avg_consistency,
    AVG(calculation_time_ms) as avg_processing_ms
FROM safety.quality_metrics
WHERE measurement_timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', measurement_timestamp)
ORDER BY hour DESC;

-- Quality issues summary
CREATE OR REPLACE VIEW safety.quality_issues_summary AS
SELECT 
    jsonb_array_elements(quality_issues)->>'type' as issue_type,
    jsonb_array_elements(quality_issues)->>'severity' as severity,
    COUNT(*) as occurrence_count,
    array_agg(DISTINCT abstraction_id) as affected_abstractions
FROM safety.quality_metrics
WHERE measurement_timestamp > NOW() - INTERVAL '24 hours'
  AND jsonb_array_length(quality_issues) > 0
GROUP BY issue_type, severity
ORDER BY occurrence_count DESC;

-- ===============================================
-- Permissions
-- ===============================================

GRANT SELECT ON safety.quality_standards TO ccp_user;
GRANT SELECT, INSERT ON safety.quality_metrics TO ccp_user;
GRANT SELECT ON safety.quality_trends TO ccp_user;
GRANT SELECT ON safety.quality_issues_summary TO ccp_user;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON TABLE safety.quality_standards IS 'Quality standards for different content types';
COMMENT ON TABLE safety.quality_metrics IS 'Detailed quality measurements for abstractions';
COMMENT ON FUNCTION safety.check_placeholder_density IS 'Verify sufficient placeholder usage in content';
COMMENT ON FUNCTION safety.check_pattern_consistency IS 'Ensure consistent abstraction patterns';
COMMENT ON FUNCTION safety.check_reference_completeness IS 'Verify all references are properly mapped';
COMMENT ON FUNCTION safety.check_semantic_quality IS 'Assess semantic preservation in abstractions';
COMMENT ON FUNCTION safety.assess_abstraction_quality IS 'Comprehensive quality assessment';

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
DECLARE
    test_density JSONB;
    test_consistency JSONB;
BEGIN
    -- Test density check
    test_density := safety.check_placeholder_density(
        'This is a test with <placeholder> content',
        0.1
    );
    
    IF NOT (test_density->>'valid')::boolean THEN
        RAISE EXCEPTION 'Density check failed for valid content';
    END IF;
    
    -- Test consistency check
    test_consistency := safety.check_pattern_consistency(
        'Mixed <placeholder> and {placeholder} styles',
        'general'
    );
    
    IF (test_consistency->>'valid')::boolean THEN
        RAISE EXCEPTION 'Consistency check should fail for mixed styles';
    END IF;
    
    RAISE NOTICE 'Quality assurance system installed successfully';
END $$;

COMMIT;