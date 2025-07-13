-- ===============================================
-- Cognitive Memory Enhancements Migration (005)
-- ===============================================
-- Advanced constraints, views, and temporal features for cognitive memory
-- Builds on safety-first foundation with enhanced validation
-- ===============================================

BEGIN;

-- ===============================================
-- Additional Constraints for Cognitive Memory
-- ===============================================

-- Composite constraint: Ensure memory consistency
ALTER TABLE public.cognitive_memory
    ADD CONSTRAINT memory_temporal_consistency CHECK (
        created_at <= updated_at AND
        created_at <= last_accessed AND
        (access_count = 0 OR last_accessed >= created_at)
    );

-- Composite constraint: Tag validation
ALTER TABLE public.cognitive_memory
    ADD CONSTRAINT valid_tag_structure CHECK (
        jsonb_typeof(tags) = 'array' AND
        (jsonb_array_length(tags) = 0 OR 
         NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(tags) AS tag
            WHERE length(tag) = 0 OR length(tag) > 50
         ))
    );

-- Composite constraint: Metadata safety
ALTER TABLE public.cognitive_memory
    ADD CONSTRAINT metadata_no_concrete_refs CHECK (
        NOT (metadata::text ~* '(/home/|/users/|c:\\|password\s*[:=]|api[_-]?key\s*[:=]|secret\s*[:=])')
    );

-- Constraint: Embedding vector validation
ALTER TABLE public.cognitive_memory
    ADD CONSTRAINT valid_embedding_dimensions CHECK (
        (prompt_embedding IS NULL OR array_length(prompt_embedding, 1) = 1536) AND
        (response_embedding IS NULL OR array_length(response_embedding, 1) = 1536)
    );

-- ===============================================
-- Memory Relationships Table
-- ===============================================
-- Track relationships between memories for context building

CREATE TABLE IF NOT EXISTS public.memory_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES public.cognitive_memory(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES public.cognitive_memory(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'continuation', 'refinement', 'contradiction', 'expansion',
        'implementation', 'question_answer', 'error_correction', 'related_topic'
    )),
    relationship_strength DECIMAL(3,2) NOT NULL DEFAULT 0.5 
        CHECK (relationship_strength > 0.0 AND relationship_strength <= 1.0),
    context JSONB DEFAULT '{}'::jsonb,
    is_bidirectional BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100) NOT NULL DEFAULT CURRENT_USER,
    
    -- Prevent self-relationships
    CONSTRAINT no_self_relationship CHECK (source_memory_id != target_memory_id),
    
    -- Unique relationships per type
    CONSTRAINT unique_relationship UNIQUE (source_memory_id, target_memory_id, relationship_type)
);

-- ===============================================
-- Memory Decay Configuration Table
-- ===============================================
-- Configure temporal decay parameters per memory type

CREATE TABLE IF NOT EXISTS public.memory_decay_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_type VARCHAR(50) NOT NULL UNIQUE REFERENCES public.cognitive_memory(interaction_type),
    base_decay_rate DECIMAL(10,8) NOT NULL DEFAULT 0.0001 
        CHECK (base_decay_rate > 0.0 AND base_decay_rate < 1.0),
    minimum_weight DECIMAL(5,4) NOT NULL DEFAULT 0.0100 
        CHECK (minimum_weight >= 0.0 AND minimum_weight < 1.0),
    reinforcement_factor DECIMAL(3,2) NOT NULL DEFAULT 1.5 
        CHECK (reinforcement_factor > 1.0 AND reinforcement_factor <= 10.0),
    decay_acceleration_days INTEGER NOT NULL DEFAULT 30 
        CHECK (decay_acceleration_days > 0),
    preserve_threshold DECIMAL(3,2) NOT NULL DEFAULT 0.8 
        CHECK (preserve_threshold > minimum_weight AND preserve_threshold <= 1.0),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ===============================================
-- Memory Clusters Table
-- ===============================================
-- Group related memories for efficient retrieval

CREATE TABLE IF NOT EXISTS public.memory_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_name VARCHAR(200) NOT NULL,
    cluster_type VARCHAR(50) NOT NULL CHECK (cluster_type IN (
        'topic', 'session', 'project', 'temporal', 'semantic', 'pattern'
    )),
    centroid_embedding vector(1536),
    member_count INTEGER NOT NULL DEFAULT 0 CHECK (member_count >= 0),
    avg_safety_score DECIMAL(3,2) CHECK (avg_safety_score >= 0.0 AND avg_safety_score <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Cluster quality constraint
    CONSTRAINT valid_cluster CHECK (
        member_count = 0 OR avg_safety_score >= 0.8
    )
);

-- Memory cluster membership
CREATE TABLE IF NOT EXISTS public.memory_cluster_members (
    cluster_id UUID NOT NULL REFERENCES public.memory_clusters(id) ON DELETE CASCADE,
    memory_id UUID NOT NULL REFERENCES public.cognitive_memory(id) ON DELETE CASCADE,
    membership_score DECIMAL(3,2) NOT NULL DEFAULT 1.0 
        CHECK (membership_score > 0.0 AND membership_score <= 1.0),
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    PRIMARY KEY (cluster_id, memory_id)
);

-- ===============================================
-- Materialized Views for Performance
-- ===============================================

-- Validated memories only (refreshed hourly)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.validated_memories AS
SELECT 
    cm.id,
    cm.session_id,
    cm.interaction_type,
    cm.abstraction_id,
    ma.abstracted_content,
    ma.abstracted_prompt,
    ma.abstracted_response,
    ma.safety_score,
    cm.weight,
    cm.last_accessed,
    cm.access_count,
    cm.tags,
    cm.metadata,
    cm.created_at,
    cm.updated_at
FROM public.cognitive_memory cm
INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
WHERE cm.is_validated = true
  AND ma.validation_status = 'validated'
  AND ma.safety_score >= 0.8
WITH DATA;

-- High-value memories (weight > 0.5, accessed recently)
CREATE MATERIALIZED VIEW IF NOT EXISTS public.active_memories AS
SELECT 
    cm.*,
    ma.safety_score,
    ma.abstracted_prompt,
    EXTRACT(DAYS FROM (NOW() - cm.last_accessed)) as days_since_access,
    cm.access_count / GREATEST(1, EXTRACT(DAYS FROM (NOW() - cm.created_at))) as access_rate
FROM public.cognitive_memory cm
INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
WHERE cm.weight > 0.5
  AND cm.last_accessed > NOW() - INTERVAL '30 days'
  AND cm.is_validated = true
ORDER BY cm.weight DESC, cm.last_accessed DESC
WITH DATA;

-- Memory statistics by session
CREATE MATERIALIZED VIEW IF NOT EXISTS public.session_memory_stats AS
SELECT 
    session_id,
    COUNT(*) as total_memories,
    AVG(weight) as avg_weight,
    MAX(weight) as max_weight,
    MIN(weight) as min_weight,
    AVG(ma.safety_score) as avg_safety_score,
    SUM(access_count) as total_accesses,
    MAX(last_accessed) as last_activity,
    array_agg(DISTINCT interaction_type) as interaction_types
FROM public.cognitive_memory cm
INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
WHERE cm.is_validated = true
GROUP BY session_id
WITH DATA;

-- Create indexes on materialized views
CREATE INDEX idx_validated_memories_session ON public.validated_memories(session_id);
CREATE INDEX idx_validated_memories_weight ON public.validated_memories(weight DESC);
CREATE INDEX idx_active_memories_access ON public.active_memories(last_accessed DESC);
CREATE INDEX idx_session_stats_activity ON public.session_memory_stats(last_activity DESC);

-- ===============================================
-- Functions for Memory Management
-- ===============================================

-- Function to calculate memory decay
CREATE OR REPLACE FUNCTION public.calculate_memory_decay(
    current_weight DECIMAL(5,4),
    last_accessed TIMESTAMP WITH TIME ZONE,
    interaction_type VARCHAR(50),
    access_count INTEGER DEFAULT 0
)
RETURNS DECIMAL(5,4)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    decay_config RECORD;
    days_elapsed INTEGER;
    decay_multiplier DECIMAL;
    new_weight DECIMAL(5,4);
BEGIN
    -- Get decay configuration
    SELECT * INTO decay_config
    FROM public.memory_decay_config
    WHERE memory_decay_config.interaction_type = calculate_memory_decay.interaction_type
      AND is_active = true;
    
    -- Use defaults if no config found
    IF NOT FOUND THEN
        decay_config.base_decay_rate := 0.0001;
        decay_config.minimum_weight := 0.01;
        decay_config.decay_acceleration_days := 30;
    END IF;
    
    -- Calculate days elapsed
    days_elapsed := EXTRACT(DAYS FROM (NOW() - last_accessed));
    
    -- Calculate decay multiplier (accelerates after threshold)
    IF days_elapsed > decay_config.decay_acceleration_days THEN
        decay_multiplier := 1.5; -- Faster decay for old memories
    ELSE
        decay_multiplier := 1.0;
    END IF;
    
    -- Apply exponential decay
    new_weight := current_weight * EXP(-decay_config.base_decay_rate * days_elapsed * decay_multiplier);
    
    -- Apply access count bonus (logarithmic)
    IF access_count > 1 THEN
        new_weight := new_weight * (1 + LN(access_count) * 0.05);
    END IF;
    
    -- Enforce minimum weight
    new_weight := GREATEST(new_weight, decay_config.minimum_weight);
    
    -- Cap at 1.0
    RETURN LEAST(new_weight, 1.0);
END;
$$;

-- Function to reinforce memory weight
CREATE OR REPLACE FUNCTION public.reinforce_memory(
    memory_id UUID,
    reinforcement_strength DECIMAL(3,2) DEFAULT 1.0
)
RETURNS DECIMAL(5,4)
LANGUAGE plpgsql
AS $$
DECLARE
    current_memory RECORD;
    decay_config RECORD;
    new_weight DECIMAL(5,4);
BEGIN
    -- Get current memory
    SELECT * INTO current_memory
    FROM public.cognitive_memory
    WHERE id = memory_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Memory not found: %', memory_id;
    END IF;
    
    -- Get decay config
    SELECT * INTO decay_config
    FROM public.memory_decay_config
    WHERE interaction_type = current_memory.interaction_type
      AND is_active = true;
    
    -- Calculate reinforced weight
    new_weight := current_memory.weight * COALESCE(decay_config.reinforcement_factor, 1.5) * reinforcement_strength;
    
    -- Cap at 1.0 but ensure it's higher than current
    new_weight := LEAST(new_weight, 1.0);
    new_weight := GREATEST(new_weight, current_memory.weight * 1.1); -- At least 10% increase
    
    -- Update memory
    UPDATE public.cognitive_memory
    SET weight = new_weight,
        last_accessed = NOW(),
        access_count = access_count + 1
    WHERE id = memory_id;
    
    RETURN new_weight;
END;
$$;

-- Function to find related memories
CREATE OR REPLACE FUNCTION public.find_related_memories(
    source_memory_id UUID,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    similarity_score DECIMAL(3,2),
    interaction_type VARCHAR(50),
    weight DECIMAL(5,4),
    relationship_type VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH vector_similarities AS (
        SELECT 
            cm.id,
            1 - (cm.prompt_embedding <=> src.prompt_embedding) as prompt_similarity,
            1 - (cm.response_embedding <=> src.response_embedding) as response_similarity,
            cm.interaction_type,
            cm.weight
        FROM public.cognitive_memory cm, public.cognitive_memory src
        WHERE src.id = source_memory_id
          AND cm.id != source_memory_id
          AND cm.is_validated = true
    ),
    existing_relationships AS (
        SELECT 
            target_memory_id,
            relationship_type,
            relationship_strength
        FROM public.memory_relationships
        WHERE source_memory_id = find_related_memories.source_memory_id
    )
    SELECT 
        vs.id as memory_id,
        GREATEST(vs.prompt_similarity, vs.response_similarity)::DECIMAL(3,2) as similarity_score,
        vs.interaction_type,
        vs.weight,
        COALESCE(er.relationship_type, 'similar')::VARCHAR(50) as relationship_type
    FROM vector_similarities vs
    LEFT JOIN existing_relationships er ON vs.id = er.target_memory_id
    WHERE GREATEST(vs.prompt_similarity, vs.response_similarity) >= similarity_threshold
    ORDER BY GREATEST(vs.prompt_similarity, vs.response_similarity) DESC
    LIMIT max_results;
END;
$$;

-- ===============================================
-- Triggers for Enhanced Functionality
-- ===============================================

-- Trigger to maintain cluster statistics
CREATE OR REPLACE FUNCTION public.update_cluster_stats()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    cluster_stats RECORD;
BEGIN
    -- Calculate updated statistics
    SELECT 
        COUNT(*) as member_count,
        AVG(ma.safety_score) as avg_safety_score
    INTO cluster_stats
    FROM public.memory_cluster_members mcm
    INNER JOIN public.cognitive_memory cm ON mcm.memory_id = cm.id
    INNER JOIN safety.memory_abstractions ma ON cm.abstraction_id = ma.memory_id
    WHERE mcm.cluster_id = COALESCE(NEW.cluster_id, OLD.cluster_id);
    
    -- Update cluster
    UPDATE public.memory_clusters
    SET member_count = cluster_stats.member_count,
        avg_safety_score = cluster_stats.avg_safety_score,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.cluster_id, OLD.cluster_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER trigger_update_cluster_stats
    AFTER INSERT OR DELETE ON public.memory_cluster_members
    FOR EACH ROW EXECUTE FUNCTION public.update_cluster_stats();

-- Trigger to cascade validation status
CREATE OR REPLACE FUNCTION public.cascade_validation_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- If abstraction validation changes, update memory
    IF TG_TABLE_NAME = 'memory_abstractions' THEN
        UPDATE public.cognitive_memory
        SET is_validated = (NEW.validation_status = 'validated' AND NEW.safety_score >= 0.8)
        WHERE abstraction_id = NEW.memory_id;
    END IF;
    
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_cascade_validation
    AFTER UPDATE OF validation_status, safety_score ON safety.memory_abstractions
    FOR EACH ROW EXECUTE FUNCTION public.cascade_validation_status();

-- ===============================================
-- Initial Configuration Data
-- ===============================================

-- Insert default decay configurations
INSERT INTO public.memory_decay_config (
    interaction_type, base_decay_rate, minimum_weight, 
    reinforcement_factor, decay_acceleration_days, preserve_threshold
) VALUES
    ('conversation', 0.0002, 0.01, 1.5, 30, 0.85),
    ('code_generation', 0.0001, 0.02, 2.0, 60, 0.90),
    ('problem_solving', 0.00015, 0.015, 1.8, 45, 0.87),
    ('documentation', 0.00005, 0.03, 1.3, 90, 0.80),
    ('debugging', 0.00025, 0.01, 2.5, 20, 0.88)
ON CONFLICT (interaction_type) DO NOTHING;

-- ===============================================
-- Permissions and Security
-- ===============================================

-- Grant permissions on new tables
GRANT SELECT, INSERT, UPDATE, DELETE ON public.memory_relationships TO ccp_user;
GRANT SELECT, INSERT, UPDATE ON public.memory_decay_config TO ccp_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.memory_clusters TO ccp_user;
GRANT SELECT, INSERT, DELETE ON public.memory_cluster_members TO ccp_user;

-- Grant permissions on materialized views
GRANT SELECT ON public.validated_memories TO ccp_user;
GRANT SELECT ON public.active_memories TO ccp_user;
GRANT SELECT ON public.session_memory_stats TO ccp_user;

-- Create refresh policies for materialized views
CREATE OR REPLACE FUNCTION public.refresh_memory_views()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.validated_memories;
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.active_memories;
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.session_memory_stats;
END;
$$;

-- ===============================================
-- Documentation
-- ===============================================

COMMENT ON TABLE public.memory_relationships IS 'Tracks semantic and logical relationships between memories';
COMMENT ON TABLE public.memory_decay_config IS 'Configurable temporal decay parameters by interaction type';
COMMENT ON TABLE public.memory_clusters IS 'Groups of related memories for efficient retrieval';
COMMENT ON TABLE public.memory_cluster_members IS 'Membership mapping for memory clusters';

COMMENT ON MATERIALIZED VIEW public.validated_memories IS 'Pre-filtered view of validated memories only';
COMMENT ON MATERIALIZED VIEW public.active_memories IS 'High-value memories with recent activity';
COMMENT ON MATERIALIZED VIEW public.session_memory_stats IS 'Aggregated statistics per session';

COMMENT ON FUNCTION public.calculate_memory_decay IS 'Calculates temporal weight decay for memories';
COMMENT ON FUNCTION public.reinforce_memory IS 'Increases memory weight based on access patterns';
COMMENT ON FUNCTION public.find_related_memories IS 'Finds semantically similar memories using vector similarity';

-- ===============================================
-- Success Verification
-- ===============================================

DO $$
DECLARE
    enhancement_count INTEGER;
BEGIN
    -- Count enhancements
    SELECT COUNT(*) INTO enhancement_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('memory_relationships', 'memory_decay_config', 'memory_clusters', 'memory_cluster_members');
    
    IF enhancement_count != 4 THEN
        RAISE EXCEPTION 'Memory enhancement incomplete: expected 4 new tables, found %', enhancement_count;
    END IF;
    
    -- Verify materialized views
    IF NOT EXISTS (SELECT 1 FROM pg_matviews WHERE schemaname = 'public' AND matviewname = 'validated_memories') THEN
        RAISE EXCEPTION 'Materialized view validated_memories not created';
    END IF;
    
    RAISE NOTICE 'Cognitive memory enhancements completed successfully';
END $$;

COMMIT;