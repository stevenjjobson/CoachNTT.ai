-- ===============================================
-- Safety Scoring System Migration (007)
-- ===============================================
-- Real-time safety score calculation and enforcement triggers
-- Automatic quarantine and remediation for unsafe content
-- ===============================================

BEGIN;

-- ===============================================
-- Safety Score History Table
-- ===============================================
-- Track score changes over time for analysis

CREATE TABLE IF NOT EXISTS safety.score_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash VARCHAR(64) NOT NULL,
    score_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    previous_score DECIMAL(3,2),
    new_score DECIMAL(3,2) NOT NULL CHECK (new_score >= 0.0 AND new_score <= 1.0),
    score_delta DECIMAL(3,2) GENERATED ALWAYS AS (new_score - COALESCE(previous_score, 0)) STORED,
    calculation_method VARCHAR(50) NOT NULL,
    factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    triggered_by VARCHAR(100) NOT NULL DEFAULT CURRENT_USER,
    
    -- Index for trend analysis
    CONSTRAINT score_progression CHECK (
        previous_score IS NULL OR 
        (previous_score >= 0.0 AND previous_score <= 1.0)
    )
);

-- ===============================================
-- Real-time Score Calculation Trigger
-- ===============================================

-- Enhanced trigger for real-time safety scoring
CREATE OR REPLACE FUNCTION safety.calculate_realtime_safety_score()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    content_text TEXT;
    score_result JSONB;
    previous_score DECIMAL(3,2);
    content_type VARCHAR(50);
    content_hash VARCHAR(64);
BEGIN
    -- Determine content type and extract text
    IF TG_TABLE_NAME = 'memory_abstractions' THEN
        content_text := COALESCE(NEW.abstracted_content::text, '') || ' ' ||
                       COALESCE(NEW.abstracted_prompt, '') || ' ' ||
                       COALESCE(NEW.abstracted_response, '');
        content_type := 'memory';
        
        -- Get previous score if updating
        IF TG_OP = 'UPDATE' THEN
            previous_score := OLD.safety_score;
        END IF;
    ELSIF TG_TABLE_NAME = 'cognitive_memory' THEN
        content_text := COALESCE(NEW.metadata::text, '') || ' ' ||
                       COALESCE(NEW.tags::text, '');
        content_type := 'metadata';
    ELSE
        content_text := to_json(NEW)::text;
        content_type := 'general';
    END IF;
    
    -- Calculate content hash
    content_hash := encode(sha256(content_text::bytea), 'hex');
    
    -- Determine specific content type for validation
    IF content_text ~ '^[\{\[].*[\}\]]$' THEN
        -- Try to parse as JSON
        BEGIN
            PERFORM content_text::jsonb;
            content_type := 'json';
        EXCEPTION WHEN OTHERS THEN
            -- Not valid JSON, keep original type
            NULL;
        END;
    ELSIF content_text ~ '(function|class|import|def|var|const|let)' THEN
        content_type := 'code';
    ELSIF content_text ~ '^https?://' THEN
        content_type := 'url';
    END IF;
    
    -- Calculate composite safety score
    score_result := safety.calculate_composite_safety_score(
        content_text,
        content_type,
        jsonb_build_object(
            'table_name', TG_TABLE_NAME,
            'operation', TG_OP,
            'timestamp', NOW()
        )
    );
    
    -- Update the safety score
    IF TG_TABLE_NAME = 'memory_abstractions' THEN
        NEW.safety_score := (score_result->>'final_score')::decimal;
        
        -- Quarantine if score too low
        IF NEW.safety_score < 0.8 THEN
            NEW.validation_status := 'quarantined';
            
            -- Insert into quarantine table
            INSERT INTO safety.quarantine (
                original_content,
                content_hash,
                source_table,
                source_id,
                quarantine_reason,
                safety_score
            ) VALUES (
                content_text,
                content_hash,
                TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                NEW.memory_id,
                score_result->'validation_details',
                NEW.safety_score
            );
        END IF;
    END IF;
    
    -- Record score history
    INSERT INTO safety.score_history (
        content_hash,
        previous_score,
        new_score,
        calculation_method,
        factors
    ) VALUES (
        content_hash,
        previous_score,
        (score_result->>'final_score')::decimal,
        'realtime_trigger',
        score_result
    );
    
    -- Learn from violations
    IF (score_result->>'total_violations')::integer > 0 THEN
        PERFORM safety.learn_from_violation(
            left(content_text, 200),
            'composite_violation',
            score_result->'validation_details'
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- ===============================================
-- Automatic Quarantine Management
-- ===============================================

-- Function to automatically quarantine low-scoring content
CREATE OR REPLACE FUNCTION safety.auto_quarantine_content()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    quarantine_id UUID;
    suggested_abstraction TEXT;
BEGIN
    -- Only quarantine if score is critically low
    IF NEW.safety_score >= 0.8 THEN
        RETURN NEW;
    END IF;
    
    -- Generate suggested abstraction
    suggested_abstraction := safety.generate_abstraction_suggestion(
        to_json(NEW)::text,
        TG_TABLE_NAME
    );
    
    -- Check if already quarantined
    IF EXISTS (
        SELECT 1 FROM safety.quarantine
        WHERE source_table = TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
          AND source_id = CASE 
              WHEN TG_TABLE_NAME = 'memory_abstractions' THEN NEW.memory_id
              WHEN TG_TABLE_NAME = 'cognitive_memory' THEN NEW.id
              ELSE NULL
          END
          AND remediation_status = 'pending'
    ) THEN
        RETURN NEW; -- Already quarantined
    END IF;
    
    -- Insert into quarantine
    INSERT INTO safety.quarantine (
        original_content,
        content_hash,
        source_table,
        source_id,
        quarantine_reason,
        safety_score,
        suggested_abstraction
    ) VALUES (
        to_json(NEW)::text,
        encode(sha256(to_json(NEW)::text::bytea), 'hex'),
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        CASE 
            WHEN TG_TABLE_NAME = 'memory_abstractions' THEN NEW.memory_id
            WHEN TG_TABLE_NAME = 'cognitive_memory' THEN NEW.id
            ELSE gen_random_uuid()
        END,
        jsonb_build_object(
            'reason', 'low_safety_score',
            'score', NEW.safety_score,
            'threshold', 0.8,
            'table', TG_TABLE_NAME
        ),
        NEW.safety_score,
        suggested_abstraction
    )
    RETURNING id INTO quarantine_id;
    
    -- Log security event
    INSERT INTO audit.security_events (
        event_type,
        event_details,
        severity
    ) VALUES (
        'auto_quarantine',
        jsonb_build_object(
            'quarantine_id', quarantine_id,
            'table', TG_TABLE_NAME,
            'safety_score', NEW.safety_score
        ),
        'WARNING'
    );
    
    -- Prevent the insert/update if configured
    IF current_setting('safety.block_on_quarantine', true) = 'true' THEN
        RAISE EXCEPTION 'Content quarantined due to low safety score: %. Quarantine ID: %', 
            NEW.safety_score, quarantine_id;
    END IF;
    
    RETURN NEW;
END;
$$;

-- ===============================================
-- Score Degradation Over Time
-- ===============================================

-- Function to degrade scores for unvalidated content
CREATE OR REPLACE FUNCTION safety.degrade_unvalidated_scores()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER := 0;
    degradation_rate DECIMAL := 0.02; -- 2% per execution
    min_score DECIMAL := 0.5;
BEGIN
    -- Degrade scores for unvalidated memory abstractions
    WITH degraded AS (
        UPDATE safety.memory_abstractions
        SET safety_score = GREATEST(min_score, safety_score * (1 - degradation_rate)),
            updated_at = NOW()
        WHERE validation_status != 'validated'
          AND created_at < NOW() - INTERVAL '7 days'
          AND safety_score > min_score
        RETURNING memory_id
    )
    SELECT COUNT(*) INTO updated_count FROM degraded;
    
    -- Record degradation in history
    INSERT INTO safety.score_history (
        content_hash,
        new_score,
        calculation_method,
        factors
    )
    SELECT 
        encode(sha256(memory_id::text::bytea), 'hex'),
        safety_score,
        'time_degradation',
        jsonb_build_object(
            'days_old', EXTRACT(DAYS FROM (NOW() - created_at)),
            'degradation_rate', degradation_rate
        )
    FROM safety.memory_abstractions
    WHERE validation_status != 'validated'
      AND created_at < NOW() - INTERVAL '7 days';
    
    -- Log the degradation event
    IF updated_count > 0 THEN
        INSERT INTO audit.security_events (
            event_type,
            event_details,
            severity
        ) VALUES (
            'score_degradation',
            jsonb_build_object(
                'affected_records', updated_count,
                'degradation_rate', degradation_rate,
                'trigger', 'scheduled'
            ),
            'INFO'
        );
    END IF;
    
    RETURN updated_count;
END;
$$;

-- ===============================================
-- Batch Revalidation System
-- ===============================================

-- Function for batch revalidation after schema updates
CREATE OR REPLACE FUNCTION safety.batch_revalidate_content(
    table_name TEXT DEFAULT NULL,
    batch_size INTEGER DEFAULT 1000,
    force_revalidation BOOLEAN DEFAULT false
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    processed_count INTEGER := 0;
    updated_count INTEGER := 0;
    failed_count INTEGER := 0;
    start_time TIMESTAMP;
    record RECORD;
    new_score DECIMAL(3,2);
    validation_result JSONB;
BEGIN
    start_time := clock_timestamp();
    
    -- Validate memory abstractions
    IF table_name IS NULL OR table_name = 'memory_abstractions' THEN
        FOR record IN 
            SELECT memory_id, abstracted_content, abstracted_prompt, 
                   abstracted_response, safety_score
            FROM safety.memory_abstractions
            WHERE force_revalidation OR validation_status != 'validated'
            ORDER BY created_at DESC
            LIMIT batch_size
        LOOP
            processed_count := processed_count + 1;
            
            BEGIN
                -- Recalculate score
                validation_result := safety.calculate_composite_safety_score(
                    COALESCE(record.abstracted_content::text, '') || ' ' ||
                    COALESCE(record.abstracted_prompt, '') || ' ' ||
                    COALESCE(record.abstracted_response, ''),
                    'memory'
                );
                
                new_score := (validation_result->>'final_score')::decimal;
                
                -- Update if score changed significantly
                IF abs(new_score - record.safety_score) > 0.05 THEN
                    UPDATE safety.memory_abstractions
                    SET safety_score = new_score,
                        validation_status = CASE 
                            WHEN new_score >= 0.8 THEN 'validated'
                            WHEN new_score >= 0.5 THEN 'pending'
                            ELSE 'quarantined'
                        END,
                        updated_at = NOW()
                    WHERE memory_id = record.memory_id;
                    
                    updated_count := updated_count + 1;
                END IF;
                
            EXCEPTION WHEN OTHERS THEN
                failed_count := failed_count + 1;
                
                -- Log failure
                INSERT INTO audit.security_events (
                    event_type,
                    event_details,
                    severity
                ) VALUES (
                    'revalidation_error',
                    jsonb_build_object(
                        'memory_id', record.memory_id,
                        'error', SQLERRM
                    ),
                    'ERROR'
                );
            END;
        END LOOP;
    END IF;
    
    RETURN jsonb_build_object(
        'processed', processed_count,
        'updated', updated_count,
        'failed', failed_count,
        'duration_ms', EXTRACT(MILLISECONDS FROM (clock_timestamp() - start_time))::integer
    );
END;
$$;

-- ===============================================
-- Abstraction Suggestion Generator
-- ===============================================

-- Generate abstraction suggestions for quarantined content
CREATE OR REPLACE FUNCTION safety.generate_abstraction_suggestion(
    content TEXT,
    content_type VARCHAR(50) DEFAULT 'general'
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    suggestion TEXT;
    template RECORD;
BEGIN
    -- Start with original content
    suggestion := content;
    
    -- Apply templates based on patterns
    FOR template IN 
        SELECT * FROM safety.abstraction_templates
        WHERE is_active = true
        ORDER BY priority DESC
    LOOP
        -- Simple pattern replacement
        suggestion := regexp_replace(
            suggestion,
            template.input_pattern,
            template.output_template,
            'g'
        );
    END LOOP;
    
    -- Type-specific suggestions
    CASE content_type
        WHEN 'memory' THEN
            -- Replace file paths
            suggestion := regexp_replace(suggestion, 
                '(/home|/Users|C:\\)[/\\][a-zA-Z0-9_.-]+[/\\]?[a-zA-Z0-9_.-]*',
                '<file_path>', 'g');
            -- Replace IPs
            suggestion := regexp_replace(suggestion,
                '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
                '<ip_address>', 'g');
                
        WHEN 'code' THEN
            -- Replace string literals containing paths
            suggestion := regexp_replace(suggestion,
                '["''](/[^"'']+|[A-Z]:\\[^"'']+)["'']',
                '"<file_path>"', 'g');
            -- Replace hardcoded credentials
            suggestion := regexp_replace(suggestion,
                '(password|token|key)\s*[:=]\s*["''][^"'']+["'']',
                '\1 = "<\1_value>"', 'gi');
                
        WHEN 'url' THEN
            -- Replace domain names
            suggestion := regexp_replace(suggestion,
                'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                '<protocol>://<domain>', 'g');
            -- Replace API keys in URLs
            suggestion := regexp_replace(suggestion,
                '([?&])(api_key|token|key)=[^&]+',
                '\1\2=<\2_value>', 'g');
    END CASE;
    
    -- Generic replacements
    -- Email addresses
    suggestion := regexp_replace(suggestion,
        '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        '<email_address>', 'g');
    
    -- Long random strings (potential secrets)
    suggestion := regexp_replace(suggestion,
        '\b[a-zA-Z0-9_-]{32,}\b',
        '<secret_token>', 'g');
    
    RETURN suggestion;
END;
$$;

-- ===============================================
-- Safety Score Monitoring Views
-- ===============================================

-- Real-time safety score dashboard
CREATE OR REPLACE VIEW safety.score_dashboard AS
SELECT 
    DATE_TRUNC('hour', score_timestamp) as hour,
    COUNT(*) as total_calculations,
    AVG(new_score) as avg_score,
    MIN(new_score) as min_score,
    MAX(new_score) as max_score,
    SUM(CASE WHEN new_score < 0.8 THEN 1 ELSE 0 END) as failed_count,
    AVG(CASE WHEN score_delta IS NOT NULL THEN score_delta ELSE 0 END) as avg_delta
FROM safety.score_history
WHERE score_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', score_timestamp)
ORDER BY hour DESC;

-- Content requiring attention
CREATE OR REPLACE VIEW safety.attention_required AS
SELECT 
    q.id as quarantine_id,
    q.source_table,
    q.source_id,
    q.safety_score,
    q.quarantine_reason,
    q.remediation_attempts,
    q.quarantined_at,
    q.suggested_abstraction,
    EXTRACT(DAYS FROM (NOW() - q.quarantined_at)) as days_in_quarantine
FROM safety.quarantine q
WHERE q.remediation_status IN ('pending', 'in_progress')
  AND q.expires_at > NOW()
ORDER BY q.safety_score ASC, q.quarantined_at ASC;

-- ===============================================
-- Install Triggers
-- ===============================================

-- Real-time scoring triggers
DROP TRIGGER IF EXISTS trigger_realtime_safety_score ON safety.memory_abstractions;
CREATE TRIGGER trigger_realtime_safety_score
    BEFORE INSERT OR UPDATE ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.calculate_realtime_safety_score();

-- Auto-quarantine triggers
DROP TRIGGER IF EXISTS trigger_auto_quarantine_memory ON safety.memory_abstractions;
CREATE TRIGGER trigger_auto_quarantine_memory
    AFTER INSERT OR UPDATE OF safety_score ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.auto_quarantine_content();

DROP TRIGGER IF EXISTS trigger_auto_quarantine_cognitive ON public.cognitive_memory;
CREATE TRIGGER trigger_auto_quarantine_cognitive
    AFTER INSERT OR UPDATE ON public.cognitive_memory
    FOR EACH ROW 
    WHEN (NEW.is_validated = false)
    EXECUTE FUNCTION safety.auto_quarantine_content();

-- ===============================================
-- Scheduled Jobs Configuration
-- ===============================================

-- Create job configuration table
CREATE TABLE IF NOT EXISTS safety.scheduled_jobs (
    job_name VARCHAR(100) PRIMARY KEY,
    is_active BOOLEAN NOT NULL DEFAULT true,
    schedule_interval INTERVAL NOT NULL,
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    last_result JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Insert job configurations
INSERT INTO safety.scheduled_jobs (job_name, schedule_interval, next_run) VALUES
    ('score_degradation', INTERVAL '1 day', NOW() + INTERVAL '1 day'),
    ('batch_revalidation', INTERVAL '1 hour', NOW() + INTERVAL '1 hour'),
    ('quarantine_cleanup', INTERVAL '1 week', NOW() + INTERVAL '1 week')
ON CONFLICT (job_name) DO NOTHING;

-- ===============================================
-- Permissions
-- ===============================================

GRANT SELECT, INSERT ON safety.score_history TO ccp_user;
GRANT SELECT ON safety.score_dashboard TO ccp_user;
GRANT SELECT ON safety.attention_required TO ccp_user;
GRANT SELECT, UPDATE ON safety.scheduled_jobs TO ccp_user;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON TABLE safety.score_history IS 'Historical record of all safety score calculations';
COMMENT ON FUNCTION safety.calculate_realtime_safety_score IS 'Real-time trigger for calculating safety scores';
COMMENT ON FUNCTION safety.auto_quarantine_content IS 'Automatically quarantine content with low safety scores';
COMMENT ON FUNCTION safety.degrade_unvalidated_scores IS 'Reduce scores for content that remains unvalidated';
COMMENT ON FUNCTION safety.batch_revalidate_content IS 'Bulk revalidation of content after schema changes';
COMMENT ON FUNCTION safety.generate_abstraction_suggestion IS 'Generate abstraction suggestions for unsafe content';
COMMENT ON VIEW safety.score_dashboard IS 'Real-time monitoring of safety score trends';
COMMENT ON VIEW safety.attention_required IS 'Content requiring manual review and remediation';

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
BEGIN
    -- Verify functions exist
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'calculate_realtime_safety_score') THEN
        RAISE EXCEPTION 'Real-time scoring function not created';
    END IF;
    
    -- Verify triggers installed
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_realtime_safety_score') THEN
        RAISE EXCEPTION 'Real-time scoring trigger not installed';
    END IF;
    
    -- Test score calculation
    DECLARE
        test_score JSONB;
    BEGIN
        test_score := safety.calculate_composite_safety_score(
            'test content with /home/user/file.txt',
            'general'
        );
        
        IF (test_score->>'final_score')::decimal >= 0.8 THEN
            RAISE EXCEPTION 'Safety scoring not working correctly - should fail for concrete path';
        END IF;
    END;
    
    RAISE NOTICE 'Safety scoring system installed successfully';
END $$;

COMMIT;