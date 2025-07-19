#!/bin/bash
# ===============================================
# Phased Migration Runner with Performance Testing
# ===============================================
# Executes migrations in phases with memory and performance monitoring
# ===============================================

set -euo pipefail

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-test_user}"
DB_PASS="${DB_PASS:-test_password}"
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

# Wait for database
wait_for_db() {
    log "Waiting for database to be ready..."
    for i in {1..30}; do
        if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" &>/dev/null; then
            success "Database is ready"
            return 0
        fi
        echo -n "."
        sleep 2
    done
    error "Database failed to start"
    return 1
}

# Run a migration file
run_migration() {
    local migration_file=$1
    local start_time=$(date +%s%N)
    
    log "Running migration: $(basename $migration_file)"
    
    if PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration_file"; then
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
    
    # Test abstraction validation trigger
    local trigger_test=$(cat <<'EOF'
-- Test trigger performance
EXPLAIN (ANALYZE, BUFFERS, TIMING) 
INSERT INTO safety.abstraction_patterns (
    pattern_type, 
    pattern_template, 
    example_concrete, 
    example_abstract, 
    safety_level
) VALUES (
    'test_pattern',
    '<test>',
    '/home/user/test',
    '<test>',
    5
);
EOF
)
    
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$trigger_test" | grep "Execution Time"
}

# Get memory stats
get_memory_stats() {
    local stats=$(PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
        SELECT 
            pg_database_size('$DB_NAME') as db_size,
            (SELECT count(*) FROM pg_trigger) as trigger_count,
            (SELECT count(*) FROM pg_proc WHERE pronamespace = 'safety'::regnamespace) as safety_functions,
            (SELECT count(*) FROM pg_index) as index_count
    " | xargs)
    
    echo "$stats"
}

# Main execution
main() {
    log "Starting phased migration execution"
    log "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    
    # Wait for database
    wait_for_db || exit 1
    
    # Get baseline stats
    log "Baseline memory stats:"
    get_memory_stats
    
    # Phase 1: Foundation (000-003)
    echo -e "\n${BLUE}=== PHASE 1: Foundation Migrations ===${NC}"
    for i in 000 001 002 003; do
        migration_file="$MIGRATIONS_DIR/${i}_*.sql"
        if ls $migration_file 1> /dev/null 2>&1; then
            run_migration $migration_file || exit 1
            
            # Test trigger performance after each migration
            if [[ $i == "003" ]]; then
                test_trigger_performance
            fi
        else
            warning "Migration $i not found"
        fi
    done
    
    # Phase 1 validation
    log "Phase 1 memory stats:"
    get_memory_stats
    
    # Pause for memory check
    warning "Phase 1 complete. Check memory usage. Press Enter to continue to Phase 2..."
    read -r
    
    # Phase 2: Enhanced Features (004-006)
    echo -e "\n${BLUE}=== PHASE 2: Enhanced Features ===${NC}"
    for i in 004 005 006; do
        migration_file="$MIGRATIONS_DIR/${i}_*.sql"
        if ls $migration_file 1> /dev/null 2>&1; then
            run_migration $migration_file || exit 1
        else
            warning "Migration $i not found"
        fi
    done
    
    # Phase 2 validation
    log "Phase 2 memory stats:"
    get_memory_stats
    
    # Test validation functions
    log "Testing validation function performance..."
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
        EXPLAIN ANALYZE SELECT safety.validate_json_content('{\"test\": \"data\"}'::jsonb);
    " | grep "Execution Time"
    
    # Pause for memory check
    warning "Phase 2 complete. Check memory usage. Press Enter to continue to Phase 3..."
    read -r
    
    # Phase 3: Optimization (007-009)
    echo -e "\n${BLUE}=== PHASE 3: Optimization ===${NC}"
    for i in 007 008 009; do
        migration_file="$MIGRATIONS_DIR/${i}_*.sql"
        if ls $migration_file 1> /dev/null 2>&1; then
            run_migration $migration_file || exit 1
        else
            warning "Migration $i not found"
        fi
    done
    
    # Final stats
    log "Final memory stats:"
    get_memory_stats
    
    # Test query performance with indexes
    log "Testing query performance..."
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
        EXPLAIN (ANALYZE, BUFFERS) 
        SELECT * FROM safety.abstraction_patterns 
        WHERE pattern_type = 'file_path' 
        LIMIT 1;
    " | grep -E "(Execution Time|Index Scan)"
    
    success "All migrations completed successfully!"
    
    # Summary
    echo -e "\n${BLUE}=== Migration Summary ===${NC}"
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
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