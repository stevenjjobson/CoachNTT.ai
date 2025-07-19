#!/bin/bash
# ===============================================
# Phased Migration Runner for Docker Container
# ===============================================
# Executes migrations in phases using docker exec
# ===============================================

set -euo pipefail

# Configuration
CONTAINER_NAME="${CONTAINER_NAME:-ccp_postgres_minimal}"
DB_USER="${DB_USER:-test_user}"
DB_NAME="${DB_NAME:-test_db}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Helper functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        error "Container $CONTAINER_NAME is not running"
        return 1
    fi
    success "Container is running"
    return 0
}

# Run a migration file
run_migration() {
    local migration_file=$1
    local start_time=$(date +%s%N)
    
    log "Running migration: $(basename $migration_file)"
    
    if docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$migration_file"; then
        local end_time=$(date +%s%N)
        local duration=$((($end_time - $start_time) / 1000000))
        success "Migration completed in ${duration}ms"
        return 0
    else
        error "Migration failed"
        return 1
    fi
}

# Test trigger performance
test_trigger_performance() {
    log "Testing trigger performance..."
    
    local result=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "
        EXPLAIN (ANALYZE, BUFFERS, TIMING OFF) 
        INSERT INTO safety.abstraction_patterns (
            pattern_type, pattern_template, example_concrete, example_abstract, safety_level
        ) VALUES ('test_pattern', '<test>', '/home/user/test', '<test>', 5);
    " | grep -E "Execution Time|Planning Time" | head -1)
    
    echo "Trigger execution: $result"
}

# Get memory stats
get_memory_stats() {
    # Database stats
    local db_stats=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "
        SELECT 
            pg_size_pretty(pg_database_size('$DB_NAME')) as db_size,
            (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal) as trigger_count,
            (SELECT count(*) FROM pg_proc WHERE pronamespace = 'safety'::regnamespace) as safety_functions,
            (SELECT count(*) FROM pg_index) as index_count
    ")
    
    # Container memory
    local container_mem=$(docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME")
    
    echo "Database: $db_stats | Container: $container_mem"
}

# Main execution
main() {
    log "Starting phased migration execution"
    log "Container: $CONTAINER_NAME"
    
    # Check container
    check_container || exit 1
    
    # Get baseline stats
    log "Baseline stats:"
    get_memory_stats
    
    # Phase 1: Foundation (000-003)
    echo -e "\n${BLUE}=== PHASE 1: Foundation Migrations ===${NC}"
    for i in 000 001 002 003; do
        migration_file=$(ls $MIGRATIONS_DIR/${i}_*.sql 2>/dev/null | head -1)
        if [[ -n "$migration_file" ]]; then
            run_migration "$migration_file" || exit 1
            
            # Test trigger performance after migration 003
            if [[ $i == "003" ]]; then
                test_trigger_performance
            fi
        else
            warning "Migration $i not found"
        fi
    done
    
    # Phase 1 validation
    log "Phase 1 stats:"
    get_memory_stats
    
    # Show current memory usage
    docker stats --no-stream "$CONTAINER_NAME"
    
    # Pause for memory check
    warning "Phase 1 complete. Check memory usage. Press Enter to continue to Phase 2..."
    read -r
    
    # Phase 2: Enhanced Features (004-006)
    echo -e "\n${BLUE}=== PHASE 2: Enhanced Features ===${NC}"
    for i in 004 005 006; do
        migration_file=$(ls $MIGRATIONS_DIR/${i}_*.sql 2>/dev/null | head -1)
        if [[ -n "$migration_file" ]]; then
            run_migration "$migration_file" || exit 1
        else
            warning "Migration $i not found"
        fi
    done
    
    # Phase 2 validation
    log "Phase 2 stats:"
    get_memory_stats
    
    # Test validation functions
    log "Testing validation function performance..."
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
        EXPLAIN ANALYZE SELECT safety.validate_json_content('{\"test\": \"data\"}'::jsonb);
    " | grep "Execution Time"
    
    # Show current memory usage
    docker stats --no-stream "$CONTAINER_NAME"
    
    # Pause for memory check
    warning "Phase 2 complete. Check memory usage. Press Enter to continue to Phase 3..."
    read -r
    
    # Phase 3: Optimization (007-009)
    echo -e "\n${BLUE}=== PHASE 3: Optimization ===${NC}"
    for i in 007 008 009; do
        migration_file=$(ls $MIGRATIONS_DIR/${i}_*.sql 2>/dev/null | head -1)
        if [[ -n "$migration_file" ]]; then
            run_migration "$migration_file" || exit 1
        else
            warning "Migration $i not found"
        fi
    done
    
    # Final stats
    log "Final stats:"
    get_memory_stats
    
    # Test query performance with indexes
    log "Testing query performance..."
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
        EXPLAIN (ANALYZE, BUFFERS) 
        SELECT * FROM safety.abstraction_patterns 
        WHERE pattern_type = 'file_path' 
        LIMIT 1;
    " | grep -E "(Execution Time|Index Scan)"
    
    # Final memory usage
    docker stats --no-stream "$CONTAINER_NAME"
    
    success "All migrations completed successfully!"
    
    # Summary
    echo -e "\n${BLUE}=== Migration Summary ===${NC}"
    docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            'Tables' as object_type, count(*) as count 
        FROM information_schema.tables 
        WHERE table_schema IN ('safety', 'audit', 'public')
        UNION ALL
        SELECT 'Triggers', count(*) FROM pg_trigger WHERE tgisinternal = false
        UNION ALL
        SELECT 'Functions', count(*) FROM pg_proc WHERE pronamespace IN ('safety'::regnamespace, 'audit'::regnamespace)
        UNION ALL
        SELECT 'Indexes', count(*) FROM pg_index;
    "
}

# Run main function
main "$@"