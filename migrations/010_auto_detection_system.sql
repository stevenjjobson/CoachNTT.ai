-- ===============================================
-- Automatic Reference Detection System Migration (010)
-- ===============================================
-- Background workers and triggers for continuous safety monitoring
-- Pattern learning and auto-quarantine for suspicious content
-- ===============================================

BEGIN;

-- ===============================================
-- Detection Rules Engine Table
-- ===============================================
-- Dynamic rules for automatic detection

CREATE TABLE IF NOT EXISTS safety.detection_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN (
        'regex', 'similarity', 'entropy', 'structural', 'behavioral', 'composite'
    )),
    detection_pattern TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium' 
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    auto_action VARCHAR(50) NOT NULL DEFAULT 'flag' 
        CHECK (auto_action IN ('flag', 'quarantine', 'reject', 'remediate')),
    confidence_threshold DECIMAL(3,2) NOT NULL DEFAULT 0.8 
        CHECK (confidence_threshold >= 0.0 AND confidence_threshold <= 1.0),
    false_positive_rate DECIMAL(3,2) DEFAULT 0.0 
        CHECK (false_positive_rate >= 0.0 AND false_positive_rate <= 1.0),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL DEFAULT CURRENT_USER,
    detection_count INTEGER NOT NULL DEFAULT 0 CHECK (detection_count >= 0),
    last_triggered TIMESTAMP WITH TIME ZONE
);

-- ===============================================
-- Detection Events Table
-- ===============================================
-- Log all detection events for analysis

CREATE TABLE IF NOT EXISTS safety.detection_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detection_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    rule_id UUID REFERENCES safety.detection_rules(id),
    content_hash VARCHAR(64) NOT NULL,
    source_table VARCHAR(100) NOT NULL,
    source_id UUID,
    detected_pattern TEXT,
    confidence_score DECIMAL(3,2) NOT NULL CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    action_taken VARCHAR(50) NOT NULL,
    action_result JSONB NOT NULL DEFAULT '{}'::jsonb,
    processing_time_ms INTEGER NOT NULL CHECK (processing_time_ms >= 0),
    
    -- Index for analysis
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ===============================================
-- Background Scan Queue Table
-- ===============================================
-- Queue for async content scanning

CREATE TABLE IF NOT EXISTS safety.scan_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    priority INTEGER NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    source_table VARCHAR(100) NOT NULL,
    source_id UUID NOT NULL,
    content_preview TEXT,
    scan_type VARCHAR(50) NOT NULL DEFAULT 'full' 
        CHECK (scan_type IN ('full', 'quick', 'deep', 'targeted')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'skipped')),
    queued_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    scan_result JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    
    -- Ensure processing order
    CONSTRAINT unique_source_pending UNIQUE (source_table, source_id, status) 
        DEFERRABLE INITIALLY DEFERRED
);

-- ===============================================
-- Pattern Evolution Table
-- ===============================================
-- Track how patterns evolve and improve

CREATE TABLE IF NOT EXISTS safety.pattern_evolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_pattern_id UUID REFERENCES safety.pattern_learning(id),
    evolved_pattern TEXT NOT NULL,
    evolution_type VARCHAR(50) NOT NULL CHECK (evolution_type IN (
        'generalization', 'specialization', 'combination', 'mutation'
    )),
    fitness_score DECIMAL(3,2) NOT NULL CHECK (fitness_score >= 0.0 AND fitness_score <= 1.0),
    generation INTEGER NOT NULL DEFAULT 1 CHECK (generation > 0),
    parent_patterns UUID[] NOT NULL DEFAULT '{}',
    test_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_promoted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ===============================================
-- Continuous Monitoring Function
-- ===============================================

-- Background worker for continuous scanning
CREATE OR REPLACE FUNCTION safety.continuous_content_monitor()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    processed_count INTEGER := 0;
    scan_record RECORD;
    detection_result JSONB;
    start_time TIMESTAMP;
BEGIN
    start_time := clock_timestamp();
    
    -- Process pending scans in priority order
    FOR scan_record IN 
        SELECT * FROM safety.scan_queue
        WHERE status = 'pending'
        ORDER BY priority DESC, queued_at ASC
        LIMIT 100
        FOR UPDATE SKIP LOCKED
    LOOP
        -- Mark as processing
        UPDATE safety.scan_queue
        SET status = 'processing',
            started_at = NOW(),
            retry_count = retry_count + 1
        WHERE id = scan_record.id;
        
        -- Perform detection based on source
        BEGIN
            CASE scan_record.source_table
                WHEN 'safety.memory_abstractions' THEN
                    detection_result := safety.detect_unsafe_patterns(
                        scan_record.source_id,
                        'memory_abstraction'
                    );
                    
                WHEN 'public.cognitive_memory' THEN
                    detection_result := safety.detect_unsafe_patterns(
                        scan_record.source_id,
                        'cognitive_memory'
                    );
                    
                ELSE
                    detection_result := jsonb_build_object(
                        'error', 'Unknown source table',
                        'table', scan_record.source_table
                    );
            END CASE;
            
            -- Update scan result
            UPDATE safety.scan_queue
            SET status = 'completed',
                completed_at = NOW(),
                scan_result = detection_result
            WHERE id = scan_record.id;
            
            processed_count := processed_count + 1;
            
        EXCEPTION WHEN OTHERS THEN
            -- Log failure
            UPDATE safety.scan_queue
            SET status = CASE 
                    WHEN retry_count >= 3 THEN 'failed'
                    ELSE 'pending'
                END,
                scan_result = jsonb_build_object(
                    'error', SQLERRM,
                    'detail', SQLSTATE
                )
            WHERE id = scan_record.id;
        END;
    END LOOP;
    
    -- Log monitoring event if processed items
    IF processed_count > 0 THEN
        INSERT INTO audit.security_events (
            event_type,
            event_details,
            severity
        ) VALUES (
            'continuous_monitoring',
            jsonb_build_object(
                'processed_count', processed_count,
                'duration_ms', EXTRACT(MILLISECONDS FROM (clock_timestamp() - start_time))::integer
            ),
            'INFO'
        );
    END IF;
    
    RETURN processed_count;
END;
$$;

-- ===============================================
-- Pattern Detection Function
-- ===============================================

-- Detect unsafe patterns using multiple methods
CREATE OR REPLACE FUNCTION safety.detect_unsafe_patterns(
    content_id UUID,
    content_type VARCHAR(50)
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    content_text TEXT;
    detection_results JSONB := '[]'::jsonb;
    rule RECORD;
    match_found BOOLEAN;
    confidence DECIMAL(3,2);
    total_detections INTEGER := 0;
    action_taken VARCHAR(50) := 'none';
BEGIN
    -- Get content based on type
    CASE content_type
        WHEN 'memory_abstraction' THEN
            SELECT 
                COALESCE(abstracted_content::text, '') || ' ' ||
                COALESCE(abstracted_prompt, '') || ' ' ||
                COALESCE(abstracted_response, '')
            INTO content_text
            FROM safety.memory_abstractions
            WHERE memory_id = content_id;
            
        WHEN 'cognitive_memory' THEN
            SELECT 
                COALESCE(metadata::text, '') || ' ' ||
                COALESCE(tags::text, '')
            INTO content_text
            FROM public.cognitive_memory
            WHERE id = content_id;
            
        ELSE
            RETURN jsonb_build_object(
                'error', 'Unknown content type',
                'content_type', content_type
            );
    END CASE;
    
    IF content_text IS NULL THEN
        RETURN jsonb_build_object(
            'error', 'Content not found',
            'content_id', content_id
        );
    END IF;
    
    -- Apply active detection rules
    FOR rule IN 
        SELECT * FROM safety.detection_rules
        WHERE is_active = true
        ORDER BY severity DESC, confidence_threshold DESC
    LOOP
        match_found := false;
        confidence := 0.0;
        
        -- Apply detection based on rule type
        CASE rule.rule_type
            WHEN 'regex' THEN
                match_found := content_text ~ rule.detection_pattern;
                confidence := CASE WHEN match_found THEN 0.95 ELSE 0.0 END;
                
            WHEN 'entropy' THEN
                DECLARE
                    entropy_score FLOAT;
                BEGIN
                    entropy_score := safety.calculate_shannon_entropy(content_text);
                    match_found := entropy_score > rule.detection_pattern::float;
                    confidence := LEAST(1.0, entropy_score / 5.0);
                END;
                
            WHEN 'similarity' THEN
                -- Check similarity to known bad patterns
                DECLARE
                    similarity_score FLOAT;
                BEGIN
                    similarity_score := similarity(content_text, rule.detection_pattern);
                    match_found := similarity_score > 0.8;
                    confidence := similarity_score;
                END;
                
            WHEN 'structural' THEN
                -- Check structural patterns (e.g., repeated sequences)
                match_found := length(content_text) > 50 AND 
                             content_text ~ '(.{10,})\1{2,}'; -- Repeated patterns
                confidence := CASE WHEN match_found THEN 0.85 ELSE 0.0 END;
        END CASE;
        
        -- Record detection if confidence meets threshold
        IF match_found AND confidence >= rule.confidence_threshold THEN
            total_detections := total_detections + 1;
            
            detection_results := detection_results || jsonb_build_object(
                'rule_id', rule.id,
                'rule_name', rule.rule_name,
                'severity', rule.severity,
                'confidence', confidence,
                'action', rule.auto_action
            );
            
            -- Take action based on severity
            IF rule.severity = 'critical' OR 
               (rule.severity = 'high' AND confidence > 0.9) THEN
                action_taken := rule.auto_action;
                
                -- Execute auto action
                CASE rule.auto_action
                    WHEN 'quarantine' THEN
                        INSERT INTO safety.quarantine (
                            original_content,
                            content_hash,
                            source_table,
                            source_id,
                            quarantine_reason,
                            safety_score
                        ) VALUES (
                            left(content_text, 1000),
                            encode(sha256(content_text::bytea), 'hex'),
                            content_type,
                            content_id,
                            jsonb_build_object(
                                'detection_rule', rule.rule_name,
                                'confidence', confidence
                            ),
                            0.0
                        );
                        
                    WHEN 'reject' THEN
                        -- Mark content as rejected
                        IF content_type = 'memory_abstraction' THEN
                            UPDATE safety.memory_abstractions
                            SET validation_status = 'rejected'
                            WHERE memory_id = content_id;
                        END IF;
                END CASE;
            END IF;
            
            -- Update rule statistics
            UPDATE safety.detection_rules
            SET detection_count = detection_count + 1,
                last_triggered = NOW()
            WHERE id = rule.id;
            
            -- Log detection event
            INSERT INTO safety.detection_events (
                rule_id,
                content_hash,
                source_table,
                source_id,
                detected_pattern,
                confidence_score,
                action_taken,
                processing_time_ms
            ) VALUES (
                rule.id,
                encode(sha256(content_text::bytea), 'hex'),
                content_type,
                content_id,
                left(rule.detection_pattern, 100),
                confidence,
                rule.auto_action,
                0
            );
        END IF;
    END LOOP;
    
    RETURN jsonb_build_object(
        'detections', detection_results,
        'total_detections', total_detections,
        'action_taken', action_taken,
        'content_length', length(content_text),
        'scan_timestamp', NOW()
    );
END;
$$;

-- ===============================================
-- Auto-Queue Triggers
-- ===============================================

-- Automatically queue new content for scanning
CREATE OR REPLACE FUNCTION safety.auto_queue_for_scanning()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Queue based on content characteristics
    DECLARE
        scan_priority INTEGER := 5;
        should_scan BOOLEAN := true;
    BEGIN
        -- Determine priority based on table and content
        IF TG_TABLE_NAME = 'memory_abstractions' THEN
            -- Higher priority for low safety scores
            IF NEW.safety_score < 0.85 THEN
                scan_priority := 8;
            ELSIF NEW.safety_score < 0.9 THEN
                scan_priority := 6;
            END IF;
            
            -- Skip if already validated with high score
            IF NEW.validation_status = 'validated' AND NEW.safety_score >= 0.95 THEN
                should_scan := false;
            END IF;
        END IF;
        
        -- Queue for scanning if needed
        IF should_scan THEN
            INSERT INTO safety.scan_queue (
                priority,
                source_table,
                source_id,
                content_preview,
                scan_type
            ) VALUES (
                scan_priority,
                TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                CASE 
                    WHEN TG_TABLE_NAME = 'memory_abstractions' THEN NEW.memory_id
                    WHEN TG_TABLE_NAME = 'cognitive_memory' THEN NEW.id
                    ELSE gen_random_uuid()
                END,
                left(to_json(NEW)::text, 200),
                CASE 
                    WHEN scan_priority >= 8 THEN 'deep'
                    WHEN scan_priority >= 6 THEN 'full'
                    ELSE 'quick'
                END
            )
            ON CONFLICT (source_table, source_id, status) 
            WHERE status = 'pending'
            DO UPDATE SET priority = GREATEST(scan_queue.priority, EXCLUDED.priority);
        END IF;
    END;
    
    RETURN NEW;
END;
$$;

-- Install auto-queue triggers
DROP TRIGGER IF EXISTS trigger_auto_queue_abstractions ON safety.memory_abstractions;
CREATE TRIGGER trigger_auto_queue_abstractions
    AFTER INSERT OR UPDATE ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION safety.auto_queue_for_scanning();

DROP TRIGGER IF EXISTS trigger_auto_queue_memories ON public.cognitive_memory;
CREATE TRIGGER trigger_auto_queue_memories
    AFTER INSERT OR UPDATE ON public.cognitive_memory
    FOR EACH ROW
    WHEN (NEW.is_validated = false)
    EXECUTE FUNCTION safety.auto_queue_for_scanning();

-- ===============================================
-- Pattern Learning Enhancement
-- ===============================================

-- Learn and evolve patterns from detections
CREATE OR REPLACE FUNCTION safety.evolve_detection_patterns()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    evolved_count INTEGER := 0;
    pattern RECORD;
    new_pattern TEXT;
    fitness DECIMAL(3,2);
BEGIN
    -- Analyze high-confidence patterns for evolution
    FOR pattern IN 
        SELECT * FROM safety.pattern_learning
        WHERE confidence_score > 0.8
          AND detection_count > 10
          AND NOT is_active
        ORDER BY confidence_score DESC
        LIMIT 20
    LOOP
        -- Try pattern generalization
        new_pattern := regexp_replace(pattern.pattern_text, 
            '[0-9]+', '[0-9]+', 'g'); -- Generalize numbers
        new_pattern := regexp_replace(new_pattern,
            '[a-zA-Z0-9]{32,}', '[a-zA-Z0-9]{32,}', 'g'); -- Generalize long strings
        
        -- Calculate fitness
        fitness := pattern.confidence_score * 
                  (1 - pattern.false_positive_count::decimal / GREATEST(pattern.detection_count, 1));
        
        -- Record evolution if different
        IF new_pattern != pattern.pattern_text THEN
            INSERT INTO safety.pattern_evolution (
                base_pattern_id,
                evolved_pattern,
                evolution_type,
                fitness_score,
                parent_patterns
            ) VALUES (
                pattern.id,
                new_pattern,
                'generalization',
                fitness,
                ARRAY[pattern.id]
            );
            
            evolved_count := evolved_count + 1;
        END IF;
    END LOOP;
    
    -- Promote high-fitness evolved patterns
    UPDATE safety.pattern_learning pl
    SET is_active = true,
        is_confirmed = true,
        confirmed_at = NOW(),
        suggested_regex = pe.evolved_pattern
    FROM safety.pattern_evolution pe
    WHERE pe.base_pattern_id = pl.id
      AND pe.fitness_score > 0.9
      AND NOT pe.is_promoted;
    
    -- Mark promoted evolutions
    UPDATE safety.pattern_evolution
    SET is_promoted = true
    WHERE fitness_score > 0.9
      AND NOT is_promoted;
    
    RETURN evolved_count;
END;
$$;

-- ===============================================
-- Initial Detection Rules
-- ===============================================

INSERT INTO safety.detection_rules (
    rule_name, rule_type, detection_pattern, severity, auto_action, confidence_threshold
) VALUES
    -- File system paths
    ('absolute_unix_path', 'regex', '^/(?:home|usr|var|etc|opt)/[a-zA-Z0-9._/-]+', 'critical', 'quarantine', 0.95),
    ('windows_path', 'regex', '^[A-Z]:\\(?:Users|Windows|Program Files)\\', 'critical', 'quarantine', 0.95),
    
    -- Network addresses
    ('private_ip', 'regex', '^(?:10|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.', 'high', 'flag', 0.9),
    ('localhost_ref', 'regex', '(?:localhost|127\.0\.0\.1)(?::\d+)?', 'high', 'flag', 0.85),
    
    -- Credentials
    ('aws_key', 'regex', 'AKIA[0-9A-Z]{16}', 'critical', 'reject', 1.0),
    ('api_key_pattern', 'regex', '(?:api[_-]?key|token)\s*[:=]\s*["\'][a-zA-Z0-9_-]{32,}["\']', 'critical', 'quarantine', 0.9),
    
    -- High entropy
    ('high_entropy_secret', 'entropy', '4.5', 'high', 'flag', 0.85),
    ('base64_secret', 'regex', '^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$', 'medium', 'flag', 0.8),
    
    -- Behavioral patterns
    ('repeated_pattern', 'structural', '(.{20,})\1{3,}', 'medium', 'flag', 0.8),
    ('suspicious_length', 'structural', '.{10000,}', 'high', 'quarantine', 0.9)
ON CONFLICT (rule_name) DO UPDATE
SET updated_at = NOW();

-- ===============================================
-- Monitoring Views
-- ===============================================

-- Real-time detection dashboard
CREATE OR REPLACE VIEW safety.detection_dashboard AS
SELECT 
    DATE_TRUNC('hour', detection_timestamp) as hour,
    COUNT(*) as total_detections,
    COUNT(DISTINCT rule_id) as unique_rules_triggered,
    COUNT(DISTINCT source_id) as unique_content_items,
    AVG(confidence_score) as avg_confidence,
    MAX(confidence_score) as max_confidence,
    COUNT(CASE WHEN action_taken = 'quarantine' THEN 1 END) as quarantined,
    COUNT(CASE WHEN action_taken = 'reject' THEN 1 END) as rejected
FROM safety.detection_events
WHERE detection_timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', detection_timestamp)
ORDER BY hour DESC;

-- Queue status view
CREATE OR REPLACE VIEW safety.scan_queue_status AS
SELECT 
    status,
    scan_type,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (NOW() - queued_at))) as avg_age_seconds,
    MIN(priority) as highest_priority,
    MAX(retry_count) as max_retries
FROM safety.scan_queue
GROUP BY status, scan_type
ORDER BY status, scan_type;

-- ===============================================
-- Scheduled Job for Pattern Evolution
-- ===============================================

INSERT INTO safety.scheduled_jobs (job_name, schedule_interval, next_run) VALUES
    ('pattern_evolution', INTERVAL '6 hours', NOW() + INTERVAL '6 hours'),
    ('continuous_monitoring', INTERVAL '5 minutes', NOW() + INTERVAL '5 minutes')
ON CONFLICT (job_name) DO UPDATE
SET schedule_interval = EXCLUDED.schedule_interval;

-- ===============================================
-- Permissions
-- ===============================================

GRANT SELECT, INSERT, UPDATE ON safety.detection_rules TO ccp_user;
GRANT SELECT ON safety.detection_events TO ccp_user;
GRANT SELECT, INSERT, UPDATE ON safety.scan_queue TO ccp_user;
GRANT SELECT ON safety.pattern_evolution TO ccp_user;
GRANT SELECT ON safety.detection_dashboard TO ccp_user;
GRANT SELECT ON safety.scan_queue_status TO ccp_user;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON TABLE safety.detection_rules IS 'Configurable rules for automatic unsafe content detection';
COMMENT ON TABLE safety.detection_events IS 'Log of all automatic detection events';
COMMENT ON TABLE safety.scan_queue IS 'Queue for asynchronous content scanning';
COMMENT ON TABLE safety.pattern_evolution IS 'Machine learning pattern evolution tracking';
COMMENT ON FUNCTION safety.continuous_content_monitor IS 'Background worker for processing scan queue';
COMMENT ON FUNCTION safety.detect_unsafe_patterns IS 'Multi-method pattern detection engine';
COMMENT ON FUNCTION safety.evolve_detection_patterns IS 'ML-based pattern evolution and improvement';

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
BEGIN
    -- Test pattern detection
    DECLARE
        test_result JSONB;
    BEGIN
        -- Test should detect hardcoded path
        test_result := safety.detect_unsafe_patterns(
            gen_random_uuid(),
            'memory_abstraction'
        );
        
        -- Should return error for non-existent content
        IF NOT (test_result ? 'error') THEN
            RAISE WARNING 'Detection function should handle missing content';
        END IF;
    END;
    
    -- Verify triggers installed
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_auto_queue_abstractions') THEN
        RAISE EXCEPTION 'Auto-queue trigger not installed';
    END IF;
    
    RAISE NOTICE 'Automatic detection system installed successfully';
END $$;

COMMIT;