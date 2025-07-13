-- ===============================================
-- Performance Indexes Migration (009)
-- ===============================================
-- Safety-aware indexes optimized for validation performance
-- Partial, expression, and covering indexes for common queries
-- ===============================================

BEGIN;

-- ===============================================
-- Drop Existing Suboptimal Indexes
-- ===============================================
-- Remove indexes that will be replaced with better versions

DROP INDEX IF EXISTS idx_memory_abstractions_safety_score;
DROP INDEX IF EXISTS idx_memory_abstractions_validation;
DROP INDEX IF EXISTS idx_cognitive_memory_weight;
DROP INDEX IF EXISTS idx_cognitive_memory_last_accessed;

-- ===============================================
-- Partial Indexes on Validated Content
-- ===============================================
-- Only index validated content for better performance

-- Validated memories only (most queries filter by this)
CREATE INDEX idx_validated_memories_only 
    ON safety.memory_abstractions (memory_id, safety_score DESC) 
    WHERE validation_status = 'validated';

-- High-safety validated content (for fast retrieval of safe content)
CREATE INDEX idx_high_safety_validated 
    ON safety.memory_abstractions (safety_score DESC, created_at DESC) 
    WHERE validation_status = 'validated' AND safety_score >= 0.9;

-- Pending validation (for validation queue processing)
CREATE INDEX idx_pending_validation 
    ON safety.memory_abstractions (created_at ASC) 
    WHERE validation_status = 'pending';

-- Quarantined content (for remediation workflows)
CREATE INDEX idx_quarantined_content 
    ON safety.memory_abstractions (safety_score ASC, updated_at DESC) 
    WHERE validation_status = 'quarantined';

-- ===============================================
-- Expression Indexes for Safety Scoring
-- ===============================================
-- Indexes on computed values for complex queries

-- Safety score buckets for analytics
CREATE INDEX idx_safety_score_buckets 
    ON safety.memory_abstractions (
        CASE 
            WHEN safety_score >= 0.95 THEN 'excellent'
            WHEN safety_score >= 0.9 THEN 'very_good'
            WHEN safety_score >= 0.8 THEN 'good'
            WHEN safety_score >= 0.7 THEN 'fair'
            ELSE 'poor'
        END,
        created_at DESC
    );

-- Content length categories
CREATE INDEX idx_content_length_category 
    ON safety.memory_abstractions (
        CASE 
            WHEN length(abstracted_content::text) < 100 THEN 'short'
            WHEN length(abstracted_content::text) < 500 THEN 'medium'
            WHEN length(abstracted_content::text) < 2000 THEN 'long'
            ELSE 'very_long'
        END
    ) WHERE validation_status = 'validated';

-- Placeholder density expression index
CREATE INDEX idx_placeholder_density_expr 
    ON safety.memory_abstractions (
        (array_length(
            regexp_split_to_array(abstracted_content::text, '<[a-zA-Z][a-zA-Z0-9_]*>'), 
            1
        ) - 1)::decimal / GREATEST(length(abstracted_content::text), 1)
    ) WHERE validation_status = 'validated';

-- ===============================================
-- GIN Indexes for JSONB Safety Validation
-- ===============================================
-- Optimized for JSONB containment and existence queries

-- Concrete references GIN index
CREATE INDEX idx_concrete_refs_gin 
    ON safety.memory_abstractions USING gin (concrete_references);

-- Abstraction mapping GIN index
CREATE INDEX idx_abstraction_mapping_gin 
    ON safety.memory_abstractions USING gin (abstraction_mapping);

-- Metadata safety validation
CREATE INDEX idx_metadata_gin 
    ON public.cognitive_memory USING gin (metadata);

-- Tags for categorization
CREATE INDEX idx_tags_gin 
    ON public.cognitive_memory USING gin (tags);

-- Validation history violations
CREATE INDEX idx_violations_gin 
    ON safety.validation_history USING gin (violations);

-- Quality issues tracking
CREATE INDEX idx_quality_issues_gin 
    ON safety.quality_metrics USING gin (quality_issues);

-- ===============================================
-- Covering Indexes for Common Queries
-- ===============================================
-- Include all needed columns to avoid table lookups

-- Memory retrieval with safety info
CREATE INDEX idx_memory_retrieval_covering 
    ON public.cognitive_memory (
        session_id, 
        weight DESC, 
        last_accessed DESC
    ) INCLUDE (
        interaction_type,
        abstraction_id,
        is_validated,
        access_count
    ) WHERE is_validated = true;

-- Abstraction lookup with safety scores
CREATE INDEX idx_abstraction_lookup_covering 
    ON safety.memory_abstractions (
        memory_id,
        validation_status
    ) INCLUDE (
        safety_score,
        abstracted_prompt,
        updated_at
    );

-- Session activity analysis
CREATE INDEX idx_session_activity_covering 
    ON public.cognitive_memory (
        session_id,
        created_at DESC
    ) INCLUDE (
        interaction_type,
        weight,
        abstraction_id
    ) WHERE is_validated = true;

-- ===============================================
-- Specialized Indexes for Vector Search
-- ===============================================
-- Optimized for similarity searches

-- Prompt embeddings with filtering
CREATE INDEX idx_prompt_embedding_filtered 
    ON public.cognitive_memory USING ivfflat (prompt_embedding vector_cosine_ops) 
    WITH (lists = 200)
    WHERE is_validated = true AND weight > 0.5;

-- Response embeddings with filtering
CREATE INDEX idx_response_embedding_filtered 
    ON public.cognitive_memory USING ivfflat (response_embedding vector_cosine_ops) 
    WITH (lists = 200)
    WHERE is_validated = true AND weight > 0.5;

-- Cluster centroids for fast grouping
CREATE INDEX idx_cluster_centroids 
    ON public.memory_clusters USING ivfflat (centroid_embedding vector_cosine_ops) 
    WITH (lists = 50);

-- ===============================================
-- Temporal Indexes for Time-based Queries
-- ===============================================

-- Recent high-value memories
CREATE INDEX idx_recent_high_value 
    ON public.cognitive_memory (last_accessed DESC, weight DESC) 
    WHERE last_accessed > (NOW() - INTERVAL '30 days') 
      AND weight > 0.7 
      AND is_validated = true;

-- Score history trends
CREATE INDEX idx_score_history_trends 
    ON safety.score_history (
        content_hash, 
        score_timestamp DESC
    ) INCLUDE (
        new_score,
        score_delta
    );

-- Validation history by result
CREATE INDEX idx_validation_history_result 
    ON safety.validation_history (
        validation_result,
        validation_timestamp DESC
    ) INCLUDE (
        safety_score,
        concrete_refs_found
    ) WHERE validation_timestamp > (NOW() - INTERVAL '7 days');

-- ===============================================
-- Cache Performance Indexes
-- ===============================================

-- Active cache entries
CREATE INDEX idx_cache_active 
    ON safety.abstraction_cache (
        last_accessed DESC,
        hit_count DESC
    ) WHERE is_valid = true AND expires_at > NOW();

-- Cache key lookup
CREATE UNIQUE INDEX idx_cache_key_unique 
    ON safety.abstraction_cache (cache_key) 
    WHERE is_valid = true;

-- ===============================================
-- Pattern Learning Indexes
-- ===============================================

-- High confidence patterns
CREATE INDEX idx_pattern_confidence 
    ON safety.pattern_learning (
        confidence_score DESC,
        detection_count DESC
    ) WHERE is_active = false AND confidence_score > 0.8;

-- Active patterns by type
CREATE INDEX idx_active_patterns 
    ON safety.pattern_learning (
        pattern_type,
        true_positive_rate DESC
    ) WHERE is_active = true;

-- ===============================================
-- Quarantine Management Indexes
-- ===============================================

-- Pending remediation
CREATE INDEX idx_quarantine_pending 
    ON safety.quarantine (
        safety_score ASC,
        quarantined_at ASC
    ) WHERE remediation_status = 'pending';

-- Expiring quarantine items
CREATE INDEX idx_quarantine_expiring 
    ON safety.quarantine (expires_at ASC) 
    WHERE remediation_status != 'resolved';

-- ===============================================
-- Composite Indexes for Complex Queries
-- ===============================================

-- Memory relationship traversal
CREATE INDEX idx_memory_relationships_composite 
    ON public.memory_relationships (
        source_memory_id,
        relationship_type,
        relationship_strength DESC
    );

-- Quality metrics analysis
CREATE INDEX idx_quality_metrics_composite 
    ON safety.quality_metrics (
        meets_standards,
        overall_quality_score DESC,
        measurement_timestamp DESC
    );

-- ===============================================
-- Function-based Indexes
-- ===============================================

-- Abstraction age in days
CREATE INDEX idx_abstraction_age_days 
    ON safety.memory_abstractions (
        EXTRACT(DAY FROM (NOW() - created_at))
    ) WHERE validation_status != 'validated';

-- Access rate calculation
CREATE INDEX idx_access_rate 
    ON public.cognitive_memory (
        (access_count::decimal / GREATEST(1, EXTRACT(DAY FROM (NOW() - created_at))))
    ) WHERE is_validated = true;

-- ===============================================
-- Maintenance and Statistics
-- ===============================================

-- Update table statistics for query planner
ANALYZE safety.memory_abstractions;
ANALYZE public.cognitive_memory;
ANALYZE safety.validation_history;
ANALYZE safety.abstraction_cache;
ANALYZE safety.quality_metrics;

-- Create index usage tracking view
CREATE OR REPLACE VIEW safety.index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'RARELY_USED'
        WHEN idx_scan < 1000 THEN 'OCCASIONALLY_USED'
        ELSE 'FREQUENTLY_USED'
    END as usage_category
FROM pg_stat_user_indexes
WHERE schemaname IN ('safety', 'public', 'audit')
ORDER BY idx_scan DESC;

-- Create index bloat monitoring view
CREATE OR REPLACE VIEW safety.index_bloat_check AS
WITH btree_index_atts AS (
    SELECT 
        nspname,
        indexclass.relname as index_name,
        indexclass.reltuples,
        indexclass.relpages,
        tableclass.relname as tablename,
        regexp_split_to_table(indkey::text, ' ')::smallint AS attnum,
        indexrelid as index_oid
    FROM pg_index
    JOIN pg_class AS indexclass ON pg_index.indexrelid = indexclass.oid
    JOIN pg_class AS tableclass ON pg_index.indrelid = tableclass.oid
    JOIN pg_namespace ON pg_namespace.oid = indexclass.relnamespace
    WHERE indexclass.relkind = 'i'
      AND nspname IN ('safety', 'public')
)
SELECT
    nspname as schema_name,
    tablename,
    index_name,
    pg_size_pretty(pg_relation_size(index_oid)) as index_size,
    CASE
        WHEN relpages < 10 THEN 'TINY'
        WHEN relpages < 100 THEN 'SMALL'
        WHEN relpages < 1000 THEN 'MEDIUM'
        ELSE 'LARGE'
    END as size_category
FROM btree_index_atts
GROUP BY nspname, tablename, index_name, index_oid, relpages
ORDER BY pg_relation_size(index_oid) DESC;

-- ===============================================
-- Permissions
-- ===============================================

GRANT SELECT ON safety.index_usage_stats TO ccp_user;
GRANT SELECT ON safety.index_bloat_check TO ccp_user;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON INDEX idx_validated_memories_only IS 'Fast access to validated memories only';
COMMENT ON INDEX idx_high_safety_validated IS 'Quick retrieval of highest quality content';
COMMENT ON INDEX idx_safety_score_buckets IS 'Analytics queries by safety score ranges';
COMMENT ON INDEX idx_memory_retrieval_covering IS 'Covering index for common memory queries';
COMMENT ON INDEX idx_prompt_embedding_filtered IS 'Vector search on high-value validated content';
COMMENT ON VIEW safety.index_usage_stats IS 'Monitor index usage patterns';
COMMENT ON VIEW safety.index_bloat_check IS 'Identify indexes needing maintenance';

-- ===============================================
-- Performance Testing
-- ===============================================

DO $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    test_duration INTERVAL;
BEGIN
    -- Test query performance with new indexes
    start_time := clock_timestamp();
    
    -- Test validated memory query
    PERFORM COUNT(*) 
    FROM safety.memory_abstractions 
    WHERE validation_status = 'validated' 
      AND safety_score >= 0.9;
    
    -- Test JSONB containment query
    PERFORM COUNT(*)
    FROM safety.memory_abstractions
    WHERE concrete_references @> '{"type": "file_path"}'::jsonb;
    
    -- Test covering index query
    PERFORM session_id, weight, interaction_type
    FROM public.cognitive_memory
    WHERE session_id = gen_random_uuid()
      AND is_validated = true
    ORDER BY weight DESC
    LIMIT 10;
    
    end_time := clock_timestamp();
    test_duration := end_time - start_time;
    
    IF EXTRACT(MILLISECONDS FROM test_duration) > 100 THEN
        RAISE WARNING 'Index performance test took longer than expected: %ms', 
            EXTRACT(MILLISECONDS FROM test_duration);
    ELSE
        RAISE NOTICE 'Index performance test completed in %ms', 
            EXTRACT(MILLISECONDS FROM test_duration);
    END IF;
END $$;

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
DECLARE
    index_count INTEGER;
BEGIN
    -- Count new indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname IN ('safety', 'public')
      AND indexname LIKE 'idx_%'
      AND indexdef LIKE '%CREATE INDEX%';
    
    IF index_count < 30 THEN
        RAISE WARNING 'Expected at least 30 indexes, found %', index_count;
    END IF;
    
    RAISE NOTICE 'Performance indexes created successfully: % indexes', index_count;
END $$;

COMMIT;