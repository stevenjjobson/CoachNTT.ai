-- ===============================================
-- Advanced Validation Functions Migration (006)
-- ===============================================
-- Comprehensive validation functions for all content types
-- Deep inspection and safety verification at database level
-- ===============================================

BEGIN;

-- ===============================================
-- JSON Content Validation
-- ===============================================

-- Deep JSON validation for nested structures
CREATE OR REPLACE FUNCTION safety.validate_json_content(
    content JSONB,
    max_depth INTEGER DEFAULT 10,
    path_prefix TEXT DEFAULT '$'
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    violations JSONB := '[]'::jsonb;
    violation JSONB;
    key TEXT;
    value JSONB;
    nested_result JSONB;
    current_path TEXT;
BEGIN
    -- Check depth limit
    IF max_depth <= 0 THEN
        RETURN jsonb_build_object(
            'valid', false,
            'violations', jsonb_build_array(jsonb_build_object(
                'path', path_prefix,
                'type', 'depth_exceeded',
                'message', 'Maximum nesting depth exceeded'
            ))
        );
    END IF;
    
    -- Handle different JSON types
    CASE jsonb_typeof(content)
        WHEN 'object' THEN
            -- Iterate through object keys
            FOR key, value IN SELECT * FROM jsonb_each(content)
            LOOP
                current_path := path_prefix || '.' || key;
                
                -- Check key name for sensitive patterns
                IF key ~* '(password|secret|token|api_key|private_key|credential)' THEN
                    violation := jsonb_build_object(
                        'path', current_path,
                        'type', 'sensitive_key',
                        'severity', 'high',
                        'message', format('Sensitive key detected: %s', key)
                    );
                    violations := violations || violation;
                END IF;
                
                -- Check string values for concrete references
                IF jsonb_typeof(value) = 'string' THEN
                    IF value::text ~ '/(home|Users)/[a-zA-Z0-9_.-]+' OR
                       value::text ~ '[A-Z]:\\[a-zA-Z0-9_\\.-]+' OR
                       value::text ~ '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' OR
                       value::text ~* 'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' THEN
                        violation := jsonb_build_object(
                            'path', current_path,
                            'type', 'concrete_reference',
                            'severity', 'critical',
                            'message', 'Concrete reference in JSON value',
                            'value', left(value::text, 50)
                        );
                        violations := violations || violation;
                    END IF;
                ELSE
                    -- Recursively validate nested structures
                    nested_result := safety.validate_json_content(value, max_depth - 1, current_path);
                    violations := violations || COALESCE(nested_result->'violations', '[]'::jsonb);
                END IF;
            END LOOP;
            
        WHEN 'array' THEN
            -- Validate array elements
            FOR key, value IN SELECT * FROM jsonb_array_elements(content) WITH ORDINALITY AS t(value, idx)
            LOOP
                current_path := path_prefix || '[' || (key::integer - 1) || ']';
                
                IF jsonb_typeof(value) = 'string' THEN
                    IF value::text ~ '/(home|Users)/[a-zA-Z0-9_.-]+' OR
                       value::text ~* '(password|secret|token)[:=]' THEN
                        violation := jsonb_build_object(
                            'path', current_path,
                            'type', 'concrete_reference',
                            'severity', 'critical',
                            'message', 'Concrete reference in array element'
                        );
                        violations := violations || violation;
                    END IF;
                ELSE
                    nested_result := safety.validate_json_content(value, max_depth - 1, current_path);
                    violations := violations || COALESCE(nested_result->'violations', '[]'::jsonb);
                END IF;
            END LOOP;
            
        WHEN 'string' THEN
            -- Direct string validation
            IF content::text ~ '/(home|Users)/[a-zA-Z0-9_.-]+' THEN
                violations := violations || jsonb_build_object(
                    'path', path_prefix,
                    'type', 'concrete_path',
                    'severity', 'critical',
                    'message', 'File path in string'
                );
            END IF;
            
        ELSE
            -- Numbers, booleans, null are safe
            NULL;
    END CASE;
    
    RETURN jsonb_build_object(
        'valid', jsonb_array_length(violations) = 0,
        'violations', violations,
        'safety_score', CASE 
            WHEN jsonb_array_length(violations) = 0 THEN 1.0
            WHEN jsonb_array_length(violations) <= 2 THEN 0.7
            WHEN jsonb_array_length(violations) <= 5 THEN 0.5
            ELSE 0.0
        END
    );
END;
$$;

-- ===============================================
-- Code Abstraction Validation
-- ===============================================

-- Special validation for code snippets
CREATE OR REPLACE FUNCTION safety.validate_code_abstractions(
    code_content TEXT,
    language VARCHAR(50) DEFAULT 'auto'
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    violations JSONB := '[]'::jsonb;
    violation JSONB;
    line_number INTEGER := 0;
    line TEXT;
    placeholder_count INTEGER := 0;
    import_count INTEGER := 0;
    concrete_import_count INTEGER := 0;
BEGIN
    -- Process code line by line
    FOR line IN SELECT unnest(string_to_array(code_content, E'\n'))
    LOOP
        line_number := line_number + 1;
        
        -- Skip empty lines and comments
        IF trim(line) = '' OR line ~ '^\s*(//|#|--|\*)' THEN
            CONTINUE;
        END IF;
        
        -- Check for file paths in code
        IF line ~ '["'']/(home|Users)/[a-zA-Z0-9_.-]+' OR
           line ~ '["''][A-Z]:\\[a-zA-Z0-9_\\.-]+' THEN
            violation := jsonb_build_object(
                'line', line_number,
                'type', 'hardcoded_path',
                'severity', 'critical',
                'message', 'Hardcoded file path in code',
                'content', left(trim(line), 80)
            );
            violations := violations || violation;
        END IF;
        
        -- Check for hardcoded credentials
        IF line ~* '(password|secret|api_key|token)\s*[:=]\s*["''][^"'']+["'']' AND
           line !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
            violation := jsonb_build_object(
                'line', line_number,
                'type', 'hardcoded_credential',
                'severity', 'critical',
                'message', 'Hardcoded credential detected',
                'content', regexp_replace(trim(line), '["''][^"'']+["'']', '"<REDACTED>"', 'g')
            );
            violations := violations || violation;
        END IF;
        
        -- Check for hardcoded URLs
        IF line ~ 'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[/a-zA-Z0-9._~:/?#@!$&''()*+,;=-]*' AND
           line !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
            violation := jsonb_build_object(
                'line', line_number,
                'type', 'hardcoded_url',
                'severity', 'high',
                'message', 'Hardcoded URL detected',
                'content', left(trim(line), 80)
            );
            violations := violations || violation;
        END IF;
        
        -- Check for IP addresses
        IF line ~ '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' AND
           line !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
            violation := jsonb_build_object(
                'line', line_number,
                'type', 'hardcoded_ip',
                'severity', 'high',
                'message', 'Hardcoded IP address detected',
                'content', left(trim(line), 80)
            );
            violations := violations || violation;
        END IF;
        
        -- Count placeholders
        placeholder_count := placeholder_count + 
            array_length(regexp_split_to_array(line, '<[a-zA-Z][a-zA-Z0-9_]*>'), 1) - 1;
        
        -- Track imports/includes
        IF line ~* '^\s*(import|include|require|using|from .* import)' THEN
            import_count := import_count + 1;
            IF line ~ '["'']\.{0,2}/[^"'']+["'']' THEN
                concrete_import_count := concrete_import_count + 1;
            END IF;
        END IF;
    END LOOP;
    
    -- Calculate code abstraction score
    DECLARE
        abstraction_score DECIMAL(3,2);
        total_lines INTEGER := line_number;
    BEGIN
        IF total_lines = 0 THEN
            abstraction_score := 1.0;
        ELSE
            abstraction_score := GREATEST(0.0, 
                1.0 - (jsonb_array_length(violations) * 0.2) + 
                (placeholder_count::decimal / GREATEST(total_lines, 1) * 0.5)
            );
            
            -- Penalize concrete imports
            IF import_count > 0 AND concrete_import_count > 0 THEN
                abstraction_score := abstraction_score * (1 - (concrete_import_count::decimal / import_count * 0.3));
            END IF;
        END IF;
        
        RETURN jsonb_build_object(
            'valid', jsonb_array_length(violations) = 0,
            'violations', violations,
            'safety_score', abstraction_score,
            'metrics', jsonb_build_object(
                'total_lines', total_lines,
                'placeholder_count', placeholder_count,
                'import_count', import_count,
                'concrete_imports', concrete_import_count
            )
        );
    END;
END;
$$;

-- ===============================================
-- URL Abstraction Validation
-- ===============================================

-- Validate URL patterns and ensure proper abstraction
CREATE OR REPLACE FUNCTION safety.validate_url_abstractions(
    url_content TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    violations JSONB := '[]'::jsonb;
    violation JSONB;
    url_parts TEXT[];
    protocol TEXT;
    domain TEXT;
    path TEXT;
    query_string TEXT;
    has_placeholders BOOLEAN := false;
BEGIN
    -- Basic URL structure check
    IF url_content !~ '^[a-zA-Z][a-zA-Z0-9+.-]*://' THEN
        RETURN jsonb_build_object(
            'valid', false,
            'violations', jsonb_build_array(jsonb_build_object(
                'type', 'invalid_url',
                'message', 'Invalid URL format'
            )),
            'safety_score', 0.0
        );
    END IF;
    
    -- Extract URL components
    protocol := regexp_replace(url_content, '^([a-zA-Z][a-zA-Z0-9+.-]*)://.*', '\1');
    domain := regexp_replace(url_content, '^[a-zA-Z][a-zA-Z0-9+.-]*://([^/]+).*', '\1');
    path := regexp_replace(url_content, '^[a-zA-Z][a-zA-Z0-9+.-]*://[^/]+(/[^?]*).*', '\1');
    query_string := regexp_replace(url_content, '^[a-zA-Z][a-zA-Z0-9+.-]*://[^?]+\?(.*)$', '\1');
    
    -- Check for placeholders
    has_placeholders := url_content ~ '<[a-zA-Z][a-zA-Z0-9_]*>';
    
    -- Validate protocol
    IF protocol NOT IN ('http', 'https', 'ftp', 'sftp', 'ssh', 'git', 'ws', 'wss') AND
       protocol !~ '^<[a-zA-Z][a-zA-Z0-9_]*>$' THEN
        violation := jsonb_build_object(
            'type', 'unusual_protocol',
            'severity', 'medium',
            'message', format('Unusual protocol: %s', protocol)
        );
        violations := violations || violation;
    END IF;
    
    -- Validate domain
    IF domain ~ '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' THEN
        violation := jsonb_build_object(
            'type', 'concrete_ip',
            'severity', 'critical',
            'message', 'IP address instead of domain placeholder'
        );
        violations := violations || violation;
    ELSIF domain ~ '^(localhost|127\.0\.0\.1)' AND domain !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
        violation := jsonb_build_object(
            'type', 'localhost_reference',
            'severity', 'high',
            'message', 'Localhost reference should be abstracted'
        );
        violations := violations || violation;
    ELSIF domain !~ '<[a-zA-Z][a-zA-Z0-9_]*>' AND 
          domain ~ '\.(local|internal|corp|test)$' THEN
        violation := jsonb_build_object(
            'type', 'internal_domain',
            'severity', 'high',
            'message', 'Internal domain should be abstracted'
        );
        violations := violations || violation;
    END IF;
    
    -- Validate path
    IF path ~ '/home/[a-zA-Z0-9_-]+' OR path ~ '/Users/[a-zA-Z0-9_-]+' THEN
        violation := jsonb_build_object(
            'type', 'file_path_in_url',
            'severity', 'critical',
            'message', 'File system path in URL'
        );
        violations := violations || violation;
    END IF;
    
    -- Validate query parameters
    IF query_string IS NOT NULL AND query_string != '' THEN
        IF query_string ~* '(api_key|token|secret|password)=[^&]+' AND
           query_string !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
            violation := jsonb_build_object(
                'type', 'credential_in_url',
                'severity', 'critical',
                'message', 'Credential parameter in URL query string'
            );
            violations := violations || violation;
        END IF;
    END IF;
    
    -- Calculate safety score
    DECLARE
        safety_score DECIMAL(3,2);
    BEGIN
        IF NOT has_placeholders AND jsonb_array_length(violations) > 0 THEN
            safety_score := 0.0;
        ELSIF has_placeholders AND jsonb_array_length(violations) = 0 THEN
            safety_score := 1.0;
        ELSIF has_placeholders THEN
            safety_score := GREATEST(0.3, 1.0 - (jsonb_array_length(violations) * 0.3));
        ELSE
            safety_score := GREATEST(0.0, 0.5 - (jsonb_array_length(violations) * 0.2));
        END IF;
        
        RETURN jsonb_build_object(
            'valid', jsonb_array_length(violations) = 0,
            'violations', violations,
            'safety_score', safety_score,
            'components', jsonb_build_object(
                'protocol', protocol,
                'domain', domain,
                'path', path,
                'has_placeholders', has_placeholders
            )
        );
    END;
END;
$$;

-- ===============================================
-- Credential Abstraction Validation
-- ===============================================

-- Validate credential abstractions with extra scrutiny
CREATE OR REPLACE FUNCTION safety.validate_credential_abstractions(
    content TEXT,
    context JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    violations JSONB := '[]'::jsonb;
    violation JSONB;
    credential_patterns TEXT[] := ARRAY[
        -- API Keys
        'sk_[a-zA-Z0-9]{32,}',
        'pk_[a-zA-Z0-9]{32,}',
        'api_[a-zA-Z0-9]{32,}',
        'key-[a-zA-Z0-9]{32,}',
        -- AWS
        'AKIA[0-9A-Z]{16}',
        'aws_[a-zA-Z0-9]{32,}',
        -- GitHub
        'ghp_[a-zA-Z0-9]{36}',
        'gho_[a-zA-Z0-9]{36}',
        'ghu_[a-zA-Z0-9]{36}',
        -- Generic secrets
        '[a-zA-Z0-9_-]{40,}',
        -- JWT tokens
        'eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
    ];
    pattern TEXT;
    entropy FLOAT;
BEGIN
    -- Check for known credential patterns
    FOREACH pattern IN ARRAY credential_patterns
    LOOP
        IF content ~ pattern AND content !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
            violation := jsonb_build_object(
                'type', 'credential_pattern',
                'severity', 'critical',
                'pattern', left(pattern, 20) || '...',
                'message', 'Potential credential detected'
            );
            violations := violations || violation;
            EXIT; -- One violation is enough
        END IF;
    END LOOP;
    
    -- Check for high entropy strings (potential secrets)
    IF length(content) >= 20 AND content !~ '<[a-zA-Z][a-zA-Z0-9_]*>' THEN
        entropy := safety.calculate_shannon_entropy(content);
        IF entropy > 4.5 THEN -- High entropy threshold
            violation := jsonb_build_object(
                'type', 'high_entropy',
                'severity', 'high',
                'entropy', round(entropy::numeric, 2),
                'message', 'High entropy string detected (possible secret)'
            );
            violations := violations || violation;
        END IF;
    END IF;
    
    -- Check for base64 encoded content
    IF content ~ '^[A-Za-z0-9+/]+={0,2}$' AND length(content) > 40 THEN
        violation := jsonb_build_object(
            'type', 'base64_content',
            'severity', 'medium',
            'message', 'Base64 encoded content should be abstracted'
        );
        violations := violations || violation;
    END IF;
    
    -- Context-aware checks
    IF context ? 'field_name' THEN
        IF context->>'field_name' ~* '(password|secret|token|key|credential)' AND
           content !~ '<[a-zA-Z][a-zA-Z0-9_]*>' AND
           length(content) > 0 THEN
            violation := jsonb_build_object(
                'type', 'sensitive_field',
                'severity', 'critical',
                'field', context->>'field_name',
                'message', 'Sensitive field contains non-abstracted value'
            );
            violations := violations || violation;
        END IF;
    END IF;
    
    -- Calculate safety score
    DECLARE
        safety_score DECIMAL(3,2);
        has_placeholders BOOLEAN;
    BEGIN
        has_placeholders := content ~ '<[a-zA-Z][a-zA-Z0-9_]*>';
        
        IF jsonb_array_length(violations) = 0 AND has_placeholders THEN
            safety_score := 1.0;
        ELSIF jsonb_array_length(violations) = 0 THEN
            safety_score := 0.8; -- No violations but no placeholders
        ELSE
            safety_score := 0.0; -- Any credential violation is critical
        END IF;
        
        RETURN jsonb_build_object(
            'valid', jsonb_array_length(violations) = 0,
            'violations', violations,
            'safety_score', safety_score,
            'has_placeholders', has_placeholders
        );
    END;
END;
$$;

-- ===============================================
-- Helper Function: Shannon Entropy
-- ===============================================

-- Calculate Shannon entropy for randomness detection
CREATE OR REPLACE FUNCTION safety.calculate_shannon_entropy(
    input_string TEXT
)
RETURNS FLOAT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    char_count JSONB := '{}'::jsonb;
    total_chars INTEGER;
    char TEXT;
    frequency FLOAT;
    entropy FLOAT := 0.0;
BEGIN
    total_chars := length(input_string);
    
    IF total_chars = 0 THEN
        RETURN 0.0;
    END IF;
    
    -- Count character frequencies
    FOR i IN 1..total_chars LOOP
        char := substr(input_string, i, 1);
        IF char_count ? char THEN
            char_count := jsonb_set(char_count, ARRAY[char], 
                to_jsonb((char_count->>char)::integer + 1));
        ELSE
            char_count := char_count || jsonb_build_object(char, 1);
        END IF;
    END LOOP;
    
    -- Calculate entropy
    FOR char IN SELECT jsonb_object_keys(char_count) LOOP
        frequency := (char_count->>char)::float / total_chars;
        IF frequency > 0 THEN
            entropy := entropy - (frequency * log(2, frequency));
        END IF;
    END LOOP;
    
    RETURN entropy;
END;
$$;

-- ===============================================
-- Composite Safety Score Calculation
-- ===============================================

-- Multi-factor safety scoring with weighted components
CREATE OR REPLACE FUNCTION safety.calculate_composite_safety_score(
    content TEXT,
    content_type VARCHAR(50) DEFAULT 'general',
    additional_context JSONB DEFAULT '{}'::jsonb
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    validation_results JSONB := '{}'::jsonb;
    component_scores JSONB := '{}'::jsonb;
    final_score DECIMAL(3,2);
    total_violations INTEGER := 0;
    critical_violations INTEGER := 0;
BEGIN
    -- Base concrete reference check
    validation_results := jsonb_set(validation_results, '{base_validation}',
        safety.validate_abstraction_quality(content, 0.0));
    
    -- Type-specific validation
    CASE content_type
        WHEN 'json' THEN
            BEGIN
                validation_results := jsonb_set(validation_results, '{json_validation}',
                    safety.validate_json_content(content::jsonb));
            EXCEPTION WHEN OTHERS THEN
                validation_results := jsonb_set(validation_results, '{json_validation}',
                    jsonb_build_object('valid', false, 'error', SQLERRM));
            END;
            
        WHEN 'code' THEN
            validation_results := jsonb_set(validation_results, '{code_validation}',
                safety.validate_code_abstractions(content));
            
        WHEN 'url' THEN
            validation_results := jsonb_set(validation_results, '{url_validation}',
                safety.validate_url_abstractions(content));
            
        WHEN 'credential' THEN
            validation_results := jsonb_set(validation_results, '{credential_validation}',
                safety.validate_credential_abstractions(content, additional_context));
            
        ELSE
            -- General validation only
            NULL;
    END CASE;
    
    -- Aggregate violations
    FOR key IN SELECT jsonb_object_keys(validation_results) LOOP
        IF validation_results->key ? 'violations' THEN
            total_violations := total_violations + 
                jsonb_array_length(validation_results->key->'violations');
            
            -- Count critical violations
            critical_violations := critical_violations + (
                SELECT COUNT(*)
                FROM jsonb_array_elements(validation_results->key->'violations') v
                WHERE v->>'severity' = 'critical'
            );
        END IF;
        
        -- Collect component scores
        IF validation_results->key ? 'safety_score' THEN
            component_scores := jsonb_set(component_scores, ARRAY[key],
                validation_results->key->'safety_score');
        END IF;
    END LOOP;
    
    -- Calculate weighted final score
    IF critical_violations > 0 THEN
        final_score := 0.0; -- Any critical violation fails
    ELSIF jsonb_object_keys(component_scores) IS NULL THEN
        final_score := 1.0; -- No specific validations performed
    ELSE
        -- Average of component scores with penalty for total violations
        SELECT AVG(value::decimal)::decimal(3,2)
        INTO final_score
        FROM jsonb_each_text(component_scores);
        
        -- Apply violation penalty
        final_score := GREATEST(0.0, final_score - (total_violations * 0.1));
    END IF;
    
    RETURN jsonb_build_object(
        'final_score', final_score,
        'passed', final_score >= 0.8,
        'total_violations', total_violations,
        'critical_violations', critical_violations,
        'component_scores', component_scores,
        'validation_details', validation_results,
        'content_type', content_type
    );
END;
$$;

-- ===============================================
-- Batch Validation Function
-- ===============================================

-- Validate multiple contents efficiently
CREATE OR REPLACE FUNCTION safety.batch_validate_contents(
    contents JSONB -- Array of {content, type, context} objects
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    results JSONB := '[]'::jsonb;
    item JSONB;
    validation_result JSONB;
    start_time TIMESTAMP;
    total_time INTERVAL;
BEGIN
    start_time := clock_timestamp();
    
    FOR item IN SELECT * FROM jsonb_array_elements(contents)
    LOOP
        validation_result := safety.calculate_composite_safety_score(
            item->>'content',
            COALESCE(item->>'type', 'general'),
            COALESCE(item->'context', '{}'::jsonb)
        );
        
        validation_result := jsonb_set(validation_result, '{id}', 
            COALESCE(item->'id', to_jsonb(gen_random_uuid()::text)));
            
        results := results || validation_result;
    END LOOP;
    
    total_time := clock_timestamp() - start_time;
    
    RETURN jsonb_build_object(
        'results', results,
        'summary', jsonb_build_object(
            'total_items', jsonb_array_length(contents),
            'passed', (SELECT COUNT(*) FROM jsonb_array_elements(results) r WHERE (r->>'passed')::boolean),
            'failed', (SELECT COUNT(*) FROM jsonb_array_elements(results) r WHERE NOT (r->>'passed')::boolean),
            'processing_time_ms', EXTRACT(MILLISECONDS FROM total_time)::integer
        )
    );
END;
$$;

-- ===============================================
-- Pattern Learning Function
-- ===============================================

-- Learn from validation failures to improve detection
CREATE OR REPLACE FUNCTION safety.learn_from_violation(
    content TEXT,
    violation_type VARCHAR(50),
    context JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    pattern_text TEXT;
    existing_pattern RECORD;
BEGIN
    -- Extract pattern from content based on violation type
    CASE violation_type
        WHEN 'file_path' THEN
            pattern_text := substring(content from '(/[a-zA-Z0-9_.-]+)+');
        WHEN 'url' THEN
            pattern_text := substring(content from 'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}');
        WHEN 'credential' THEN
            -- Don't store actual credentials, just the pattern structure
            pattern_text := regexp_replace(content, '[a-zA-Z0-9]', 'X', 'g');
        ELSE
            pattern_text := left(content, 100);
    END CASE;
    
    IF pattern_text IS NULL OR length(pattern_text) < 5 THEN
        RETURN;
    END IF;
    
    -- Update or insert pattern
    INSERT INTO safety.pattern_learning (
        pattern_text,
        pattern_type,
        detection_count,
        confidence_score
    ) VALUES (
        pattern_text,
        violation_type,
        1,
        0.5
    )
    ON CONFLICT (pattern_text, pattern_type) DO UPDATE
    SET detection_count = pattern_learning.detection_count + 1,
        last_seen = NOW(),
        confidence_score = LEAST(1.0, pattern_learning.confidence_score + 0.05);
END;
$$;

-- ===============================================
-- Grant Permissions
-- ===============================================

GRANT EXECUTE ON FUNCTION safety.validate_json_content TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.validate_code_abstractions TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.validate_url_abstractions TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.validate_credential_abstractions TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.calculate_shannon_entropy TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.calculate_composite_safety_score TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.batch_validate_contents TO ccp_user;
GRANT EXECUTE ON FUNCTION safety.learn_from_violation TO ccp_user;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON FUNCTION safety.validate_json_content IS 'Deep validation of JSON structures for concrete references';
COMMENT ON FUNCTION safety.validate_code_abstractions IS 'Specialized validation for code snippets and source files';
COMMENT ON FUNCTION safety.validate_url_abstractions IS 'URL pattern validation ensuring proper abstraction';
COMMENT ON FUNCTION safety.validate_credential_abstractions IS 'High-security validation for credential content';
COMMENT ON FUNCTION safety.calculate_shannon_entropy IS 'Calculate randomness/entropy of strings for secret detection';
COMMENT ON FUNCTION safety.calculate_composite_safety_score IS 'Multi-factor safety scoring with type-specific validation';
COMMENT ON FUNCTION safety.batch_validate_contents IS 'Efficient batch validation of multiple contents';
COMMENT ON FUNCTION safety.learn_from_violation IS 'Machine learning feedback for improving pattern detection';

-- ===============================================
-- Test the Functions
-- ===============================================

DO $$
DECLARE
    test_result JSONB;
BEGIN
    -- Test JSON validation
    test_result := safety.validate_json_content('{"path": "/home/user/file.txt"}'::jsonb);
    IF (test_result->>'valid')::boolean THEN
        RAISE EXCEPTION 'JSON validation should have failed for concrete path';
    END IF;
    
    -- Test code validation
    test_result := safety.validate_code_abstractions('password = "secretpass123"');
    IF (test_result->>'valid')::boolean THEN
        RAISE EXCEPTION 'Code validation should have failed for hardcoded credential';
    END IF;
    
    -- Test URL validation
    test_result := safety.validate_url_abstractions('https://api.example.com/v1/users?api_key=secret123');
    IF (test_result->>'valid')::boolean THEN
        RAISE EXCEPTION 'URL validation should have failed for credential in query';
    END IF;
    
    RAISE NOTICE 'All validation functions tested successfully';
END $$;

COMMIT;