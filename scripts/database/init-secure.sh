#!/bin/bash

# ===============================================
# Secure PostgreSQL Initialization Script
# ===============================================
# Safety-first database initialization with comprehensive validation
# for CoachNTT.ai Cognitive Coding Partner
# ===============================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ===============================================
# Configuration and Constants
# ===============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/lib/postgresql/logs/init-secure.log"
readonly AUDIT_LOG="/var/lib/postgresql/audit/init-secure-audit.log"
readonly SAFETY_VALIDATION_LOG="/var/lib/postgresql/audit/safety-validation.log"

# Database configuration
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"

# Safety thresholds
readonly MIN_SAFETY_SCORE=0.8
readonly MAX_CONCRETE_REFS=0
readonly REQUIRED_SAFETY_EXTENSIONS=("uuid-ossp" "vector" "pgcrypto" "pg_stat_statements")

# ===============================================
# Logging Functions
# ===============================================
log_info() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $message" | tee -a "$LOG_FILE"
}

log_error() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $message" | tee -a "$LOG_FILE" >&2
}

log_security() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SECURITY] $message" | tee -a "$AUDIT_LOG"
}

log_safety() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SAFETY] $message" | tee -a "$SAFETY_VALIDATION_LOG"
}

# ===============================================
# Safety Validation Functions
# ===============================================
validate_environment() {
    log_info "Validating environment safety..."
    
    # Check for required environment variables
    if [[ -z "${POSTGRES_USER:-}" ]]; then
        log_error "POSTGRES_USER environment variable not set"
        return 1
    fi
    
    if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
        log_error "POSTGRES_PASSWORD environment variable not set"
        return 1
    fi
    
    if [[ -z "${POSTGRES_DB:-}" ]]; then
        log_error "POSTGRES_DB environment variable not set"
        return 1
    fi
    
    # Validate safety schema configuration
    if [[ "${POSTGRES_SAFETY_SCHEMA_FIRST:-false}" != "true" ]]; then
        log_error "Safety schema must be created first (POSTGRES_SAFETY_SCHEMA_FIRST=true)"
        return 1
    fi
    
    log_safety "Environment validation passed"
    return 0
}

check_concrete_references() {
    local file="$1"
    local concrete_count=0
    
    # Check for common concrete reference patterns
    local patterns=(
        "/home/[a-zA-Z0-9_-]+"
        "/Users/[a-zA-Z0-9_-]+"
        "localhost:[0-9]+"
        "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+"
        "password.*=.*['\"][^'\"]+['\"]"
        "secret.*=.*['\"][^'\"]+['\"]"
        "token.*=.*['\"][^'\"]+['\"]"
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -qE "$pattern" "$file" 2>/dev/null; then
            ((concrete_count++))
            log_safety "Found potential concrete reference in $file: $pattern"
        fi
    done
    
    if [[ $concrete_count -gt $MAX_CONCRETE_REFS ]]; then
        log_error "Too many concrete references found in $file: $concrete_count (max: $MAX_CONCRETE_REFS)"
        return 1
    fi
    
    return 0
}

validate_sql_safety() {
    local sql_file="$1"
    
    log_safety "Validating SQL file safety: $sql_file"
    
    # Check for concrete references
    if ! check_concrete_references "$sql_file"; then
        return 1
    fi
    
    # Check for required safety patterns
    if ! grep -q "CREATE SCHEMA.*safety" "$sql_file"; then
        log_error "SQL file must create safety schema: $sql_file"
        return 1
    fi
    
    # Check for abstraction enforcement
    if ! grep -q "abstraction" "$sql_file"; then
        log_error "SQL file must include abstraction enforcement: $sql_file"
        return 1
    fi
    
    log_safety "SQL file validation passed: $sql_file"
    return 0
}

# ===============================================
# Database Connection and Validation
# ===============================================
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres >/dev/null 2>&1; then
            log_info "PostgreSQL is ready"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting..."
        sleep 2
        ((attempt++))
    done
    
    log_error "PostgreSQL did not become ready within timeout"
    return 1
}

validate_database_security() {
    log_security "Validating database security configuration..."
    
    # Check authentication method
    local auth_method
    auth_method=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -t -c "SHOW password_encryption;" 2>/dev/null | xargs)
    
    if [[ "$auth_method" != "scram-sha-256" ]]; then
        log_error "Database must use scram-sha-256 authentication, found: $auth_method"
        return 1
    fi
    
    # Check logging configuration
    local log_statement
    log_statement=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -t -c "SHOW log_statement;" 2>/dev/null | xargs)
    
    if [[ "$log_statement" != "all" ]]; then
        log_error "Database must log all statements for security audit, found: $log_statement"
        return 1
    fi
    
    log_security "Database security validation passed"
    return 0
}

# ===============================================
# Safety Schema Validation
# ===============================================
validate_safety_extensions() {
    log_safety "Validating safety extensions..."
    
    for extension in "${REQUIRED_SAFETY_EXTENSIONS[@]}"; do
        local exists
        exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='$extension');" 2>/dev/null | xargs)
        
        if [[ "$exists" != "t" ]]; then
            log_error "Required safety extension not installed: $extension"
            return 1
        fi
        
        log_safety "Safety extension validated: $extension"
    done
    
    return 0
}

validate_safety_schema() {
    log_safety "Validating safety schema exists and is configured..."
    
    # Check safety schema exists
    local schema_exists
    schema_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name='safety');" 2>/dev/null | xargs)
    
    if [[ "$schema_exists" != "t" ]]; then
        log_error "Safety schema does not exist"
        return 1
    fi
    
    # Check search path includes safety first
    local search_path
    search_path=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SHOW search_path;" 2>/dev/null | xargs)
    
    if [[ ! "$search_path" =~ ^safety ]]; then
        log_error "Search path must include safety schema first, found: $search_path"
        return 1
    fi
    
    log_safety "Safety schema validation passed"
    return 0
}

# ===============================================
# Main Initialization Process
# ===============================================
initialize_directories() {
    log_info "Initializing secure directories..."
    
    # Create log directories with secure permissions
    mkdir -p /var/lib/postgresql/logs
    mkdir -p /var/lib/postgresql/audit
    mkdir -p /var/lib/postgresql/backups
    
    # Set secure permissions
    chmod 750 /var/lib/postgresql/logs
    chmod 750 /var/lib/postgresql/audit
    chmod 750 /var/lib/postgresql/backups
    
    # Ensure postgres user owns directories
    chown -R postgres:postgres /var/lib/postgresql/logs
    chown -R postgres:postgres /var/lib/postgresql/audit
    chown -R postgres:postgres /var/lib/postgresql/backups
    
    log_info "Secure directories initialized"
}

run_safety_migrations() {
    log_safety "Running safety-first migrations..."
    
    local migration_dir="/migrations"
    
    if [[ ! -d "$migration_dir" ]]; then
        log_error "Migration directory not found: $migration_dir"
        return 1
    fi
    
    # Process migrations in order
    for migration_file in "$migration_dir"/*.sql; do
        if [[ -f "$migration_file" ]]; then
            log_safety "Processing migration: $(basename "$migration_file")"
            
            # Validate migration safety before execution
            if ! validate_sql_safety "$migration_file"; then
                log_error "Migration failed safety validation: $migration_file"
                return 1
            fi
            
            # Execute migration
            if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration_file"; then
                log_error "Migration execution failed: $migration_file"
                return 1
            fi
            
            log_safety "Migration completed successfully: $(basename "$migration_file")"
        fi
    done
    
    return 0
}

test_safety_enforcement() {
    log_safety "Testing safety enforcement with invalid data..."
    
    # Test 1: Try to insert concrete reference (should fail)
    local test_sql="INSERT INTO memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"test\"}', '{\"path\": \"/home/user/file.txt\"}', 0.5);"
    
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$test_sql" >/dev/null 2>&1; then
        log_error "Safety enforcement failed: Database accepted low safety score"
        return 1
    fi
    
    log_safety "Safety enforcement test passed: Low safety score rejected"
    
    # Test 2: Try to insert valid abstracted data (should succeed)
    local valid_sql="INSERT INTO memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"test with <file_path>\"}', '{\"path\": \"<file_path>\"}', 0.9);"
    
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$valid_sql" >/dev/null 2>&1; then
        log_error "Valid abstracted data was rejected"
        return 1
    fi
    
    log_safety "Safety enforcement test passed: Valid abstracted data accepted"
    return 0
}

# ===============================================
# Main Execution
# ===============================================
main() {
    log_info "Starting secure PostgreSQL initialization..."
    log_security "Security audit log initialized"
    log_safety "Safety validation log initialized"
    
    # Step 1: Environment validation
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Step 2: Initialize directories
    initialize_directories
    
    # Step 3: Wait for PostgreSQL
    if ! wait_for_postgres; then
        log_error "PostgreSQL startup timeout"
        exit 1
    fi
    
    # Step 4: Validate database security
    if ! validate_database_security; then
        log_error "Database security validation failed"
        exit 1
    fi
    
    # Step 5: Validate safety extensions
    if ! validate_safety_extensions; then
        log_error "Safety extension validation failed"
        exit 1
    fi
    
    # Step 6: Validate safety schema
    if ! validate_safety_schema; then
        log_error "Safety schema validation failed"
        exit 1
    fi
    
    # Step 7: Run safety migrations
    if ! run_safety_migrations; then
        log_error "Safety migration execution failed"
        exit 1
    fi
    
    # Step 8: Test safety enforcement
    if ! test_safety_enforcement; then
        log_error "Safety enforcement testing failed"
        exit 1
    fi
    
    log_info "Secure PostgreSQL initialization completed successfully"
    log_security "Security initialization audit completed"
    log_safety "Safety validation completed successfully"
    
    return 0
}

# ===============================================
# Script Execution
# ===============================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi