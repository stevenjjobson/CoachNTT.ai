#!/bin/bash

# ===============================================
# Secure Database Restore Script with Safety Validation
# ===============================================
# Safety-first encrypted backup restore for CoachNTT.ai
# Validates safety compliance before restoring any data
# ===============================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ===============================================
# Configuration and Constants
# ===============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKUP_DIR="${POSTGRES_BACKUP_PATH:-./data/postgres-backups}"
readonly LOG_FILE="${BACKUP_DIR}/restore.log"
readonly AUDIT_LOG="${BACKUP_DIR}/restore-audit.log"
readonly ENCRYPTION_KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-/etc/ccp/backup.key}"

# Database configuration
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"

# Safety configuration
readonly SAFETY_VALIDATION_REQUIRED=true
readonly CONCRETE_REF_TOLERANCE=0  # Zero tolerance for concrete references
readonly MIN_SAFETY_SCORE=0.8
readonly REQUIRED_SAFETY_SCHEMAS=("safety" "audit")

# Restore options
readonly CREATE_BACKUP_BEFORE_RESTORE=true
readonly RESTORE_TIMEOUT_SECONDS=1800  # 30 minutes
readonly VALIDATION_TIMEOUT_SECONDS=300  # 5 minutes

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SAFETY] $message" | tee -a "$AUDIT_LOG"
}

log_warning() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARNING] $message" | tee -a "$LOG_FILE"
}

# ===============================================
# Safety Validation Functions
# ===============================================
validate_environment() {
    log_info "Validating restore environment..."
    
    # Check backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        return 1
    fi
    
    # Check encryption key exists
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log_error "Encryption key not found: $ENCRYPTION_KEY_FILE"
        return 1
    fi
    
    # Validate key permissions
    local key_perms
    key_perms=$(stat -c %a "$ENCRYPTION_KEY_FILE" 2>/dev/null || echo "000")
    if [[ "$key_perms" != "600" ]]; then
        log_security "Encryption key permissions not secure: $key_perms"
        return 1
    fi
    
    # Check database connectivity
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres >/dev/null 2>&1; then
        log_error "Database not accessible: $DB_HOST:$DB_PORT"
        return 1
    fi
    
    # Check required tools
    local required_tools=("psql" "pg_restore" "gunzip" "openssl" "sha256sum")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: $tool"
            return 1
        fi
    done
    
    log_safety "Environment validation passed"
    return 0
}

validate_backup_file() {
    local backup_file="$1"
    
    log_info "Validating backup file: $(basename "$backup_file")"
    
    # Check file exists
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Check associated files exist
    if [[ ! -f "${backup_file}.iv" ]]; then
        log_error "Encryption IV file not found: ${backup_file}.iv"
        return 1
    fi
    
    if [[ ! -f "${backup_file}.sha256" ]]; then
        log_error "Checksum file not found: ${backup_file}.sha256"
        return 1
    fi
    
    # Verify checksum
    local expected_checksum
    local actual_checksum
    expected_checksum=$(cat "${backup_file}.sha256")
    actual_checksum=$(sha256sum "$backup_file" | cut -d' ' -f1)
    
    if [[ "$expected_checksum" != "$actual_checksum" ]]; then
        log_error "Backup file integrity check failed"
        log_error "Expected: $expected_checksum"
        log_error "Actual: $actual_checksum"
        return 1
    fi
    
    log_security "Backup file integrity verified"
    return 0
}

decrypt_backup() {
    local encrypted_file="$1"
    local decrypted_file="$2"
    
    log_security "Decrypting backup: $(basename "$encrypted_file")"
    
    # Get IV for decryption
    local iv
    iv=$(cat "${encrypted_file}.iv")
    
    # Decrypt backup
    if ! openssl enc -aes-256-cbc -d -iv "$iv" -K "$(cat "$ENCRYPTION_KEY_FILE")" \
         -in "$encrypted_file" -out "$decrypted_file"; then
        log_error "Backup decryption failed"
        return 1
    fi
    
    log_security "Backup decrypted successfully"
    return 0
}

validate_backup_content_safety() {
    local backup_file="$1"
    
    log_safety "Performing comprehensive safety validation of backup content..."
    
    local safety_violations=0
    local concrete_ref_count=0
    
    # Patterns to detect concrete references
    local critical_patterns=(
        "/home/[a-zA-Z0-9_.-]+"
        "/Users/[a-zA-Z0-9_.-]+"
        "C:\\\\[a-zA-Z0-9_\\\\.-]+"
        "[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}"
        "password\s*[:=]\s*['\"][^'\"]+['\"]"
        "secret\s*[:=]\s*['\"][^'\"]+['\"]"
        "token\s*[:=]\s*['\"][^'\"]+['\"]"
        "api_key\s*[:=]\s*['\"][^'\"]+['\"]"
    )
    
    local warning_patterns=(
        "localhost:[0-9]+"
        "127\\.0\\.0\\.1"
        "user@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    )
    
    # Check for critical safety violations
    for pattern in "${critical_patterns[@]}"; do
        local matches
        matches=$(grep -cE "$pattern" "$backup_file" 2>/dev/null || echo "0")
        if [[ $matches -gt 0 ]]; then
            log_error "CRITICAL: Concrete reference pattern found: $pattern ($matches occurrences)"
            ((safety_violations++))
            ((concrete_ref_count += matches))
        fi
    done
    
    # Check for warning patterns
    for pattern in "${warning_patterns[@]}"; do
        local matches
        matches=$(grep -cE "$pattern" "$backup_file" 2>/dev/null || echo "0")
        if [[ $matches -gt 0 ]]; then
            log_warning "Potential concrete reference: $pattern ($matches occurrences)"
        fi
    done
    
    # Check for required safety elements
    if ! grep -q "CREATE SCHEMA.*safety" "$backup_file"; then
        log_error "CRITICAL: Safety schema not found in backup"
        ((safety_violations++))
    fi
    
    if ! grep -q "memory_abstractions" "$backup_file"; then
        log_error "CRITICAL: Memory abstractions table not found in backup"
        ((safety_violations++))
    fi
    
    # Check abstraction placeholders are present
    local placeholder_count
    placeholder_count=$(grep -cE '<[a-zA-Z][a-zA-Z0-9_]*>' "$backup_file" 2>/dev/null || echo "0")
    
    if [[ $placeholder_count -eq 0 ]]; then
        log_error "CRITICAL: No abstraction placeholders found in backup"
        ((safety_violations++))
    else
        log_safety "Found $placeholder_count abstraction placeholders"
    fi
    
    # Safety violation assessment
    if [[ $safety_violations -gt 0 ]]; then
        log_error "Backup failed safety validation: $safety_violations critical violations"
        log_error "Concrete references found: $concrete_ref_count"
        return 1
    fi
    
    if [[ $concrete_ref_count -gt $CONCRETE_REF_TOLERANCE ]]; then
        log_error "Backup exceeds concrete reference tolerance: $concrete_ref_count > $CONCRETE_REF_TOLERANCE"
        return 1
    fi
    
    log_safety "Backup content safety validation PASSED"
    log_safety "Placeholder abstractions: $placeholder_count"
    log_safety "Concrete references: $concrete_ref_count (tolerance: $CONCRETE_REF_TOLERANCE)"
    
    return 0
}

validate_restored_database_safety() {
    log_safety "Validating restored database safety compliance..."
    
    # Check required schemas exist
    for schema in "${REQUIRED_SAFETY_SCHEMAS[@]}"; do
        local schema_exists
        schema_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name='$schema');" 2>/dev/null | xargs)
        
        if [[ "$schema_exists" != "t" ]]; then
            log_error "Required schema missing after restore: $schema"
            return 1
        fi
    done
    
    # Validate safety tables
    local safety_tables=("memory_abstractions" "abstraction_patterns" "reference_validation_rules")
    for table in "${safety_tables[@]}"; do
        local table_exists
        table_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='safety' AND table_name='$table');" 2>/dev/null | xargs)
        
        if [[ "$table_exists" != "t" ]]; then
            log_error "Required safety table missing after restore: safety.$table"
            return 1
        fi
    done
    
    # Check trigger functions exist
    local required_functions=("validate_memory_abstraction" "validate_cognitive_memory")
    for func in "${required_functions[@]}"; do
        local func_exists
        func_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.routines WHERE routine_schema='safety' AND routine_name='$func');" 2>/dev/null | xargs)
        
        if [[ "$func_exists" != "t" ]]; then
            log_error "Required safety function missing after restore: safety.$func"
            return 1
        fi
    done
    
    # Validate search path prioritizes safety
    local search_path
    search_path=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SHOW search_path;" 2>/dev/null | xargs)
    
    if [[ ! "$search_path" =~ ^safety ]]; then
        log_warning "Search path does not prioritize safety schema: $search_path"
    fi
    
    # Test safety enforcement
    if ! test_safety_enforcement; then
        log_error "Safety enforcement test failed after restore"
        return 1
    fi
    
    log_safety "Restored database safety validation PASSED"
    return 0
}

test_safety_enforcement() {
    log_safety "Testing safety enforcement on restored database..."
    
    # Test 1: Try to insert data with low safety score (should fail)
    local test_sql="INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"test\": \"data\"}', '{\"path\": \"/home/user\"}', 0.5);"
    
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$test_sql" >/dev/null 2>&1; then
        log_error "Safety enforcement FAILED: Low safety score accepted"
        return 1
    fi
    
    # Test 2: Try to insert valid abstracted data (should succeed)
    local valid_sql="INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"test with <file_path>\"}', '{\"path\": \"<file_path>\"}', 0.9);"
    
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$valid_sql" >/dev/null 2>&1; then
        log_error "Safety enforcement FAILED: Valid abstracted data rejected"
        return 1
    fi
    
    # Clean up test data
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DELETE FROM safety.memory_abstractions WHERE abstracted_content::text LIKE '%test%';" >/dev/null 2>&1
    
    log_safety "Safety enforcement tests PASSED"
    return 0
}

# ===============================================
# Backup and Restore Functions
# ===============================================
create_pre_restore_backup() {
    log_info "Creating pre-restore backup..."
    
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local pre_restore_backup="${BACKUP_DIR}/pre_restore_backup_${timestamp}.sql"
    
    # Check if database exists
    local db_exists
    db_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -t -c "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname='$DB_NAME');" 2>/dev/null | xargs)
    
    if [[ "$db_exists" == "t" ]]; then
        if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --clean --create > "$pre_restore_backup"; then
            gzip "$pre_restore_backup"
            log_info "Pre-restore backup created: ${pre_restore_backup}.gz"
        else
            log_warning "Failed to create pre-restore backup"
        fi
    else
        log_info "Database does not exist, skipping pre-restore backup"
    fi
    
    return 0
}

perform_restore() {
    local backup_file="$1"
    
    log_info "Starting database restore from: $(basename "$backup_file")"
    log_security "Restore initiated by user: ${USER:-unknown}"
    
    # Restore with timeout
    local restore_cmd="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -f $backup_file"
    
    if timeout "$RESTORE_TIMEOUT_SECONDS" bash -c "$restore_cmd"; then
        log_info "Database restore completed successfully"
        return 0
    else
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_error "Database restore timed out after $RESTORE_TIMEOUT_SECONDS seconds"
        else
            log_error "Database restore failed with exit code: $exit_code"
        fi
        return 1
    fi
}

# ===============================================
# User Confirmation Functions
# ===============================================
confirm_restore() {
    local backup_file="$1"
    
    echo
    echo "==============================================="
    echo "DATABASE RESTORE CONFIRMATION"
    echo "==============================================="
    echo "Backup file: $(basename "$backup_file")"
    echo "Target database: $DB_NAME"
    echo "Safety validation: $SAFETY_VALIDATION_REQUIRED"
    echo "Pre-restore backup: $CREATE_BACKUP_BEFORE_RESTORE"
    echo
    echo "WARNING: This will completely replace the current database!"
    echo
    
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
    
    echo
    read -p "Type 'CONFIRM RESTORE' to proceed: " -r
    if [[ "$REPLY" != "CONFIRM RESTORE" ]]; then
        log_info "Restore cancelled - confirmation text incorrect"
        exit 0
    fi
    
    log_security "Restore confirmed by user"
}

# ===============================================
# Main Restore Process
# ===============================================
usage() {
    echo "Usage: $0 <backup_file>"
    echo
    echo "Restores encrypted database backup with safety validation"
    echo
    echo "Arguments:"
    echo "  backup_file    Path to encrypted backup file (.enc)"
    echo
    echo "Example:"
    echo "  $0 /path/to/backup_20250113_120000.sql.gz.enc"
    echo
    echo "Environment variables:"
    echo "  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_DB"
    echo "  BACKUP_ENCRYPTION_KEY_FILE"
    echo "  POSTGRES_BACKUP_PATH"
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
        exit 1
    fi
    
    local backup_file="$1"
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    
    log_info "Starting secure database restore process..."
    log_security "Restore process initiated"
    
    # Step 1: Environment validation
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Step 2: Backup file validation
    if ! validate_backup_file "$backup_file"; then
        log_error "Backup file validation failed"
        exit 1
    fi
    
    # Step 3: User confirmation
    confirm_restore "$backup_file"
    
    # Step 4: Create temporary working directory
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    # Step 5: Decrypt backup
    local compressed_file="${temp_dir}/backup.sql.gz"
    if ! decrypt_backup "$backup_file" "$compressed_file"; then
        log_error "Backup decryption failed"
        exit 1
    fi
    
    # Step 6: Decompress backup
    local sql_file="${temp_dir}/backup.sql"
    if ! gunzip -c "$compressed_file" > "$sql_file"; then
        log_error "Backup decompression failed"
        exit 1
    fi
    
    # Step 7: Safety validation of backup content
    if [[ "$SAFETY_VALIDATION_REQUIRED" == "true" ]]; then
        if ! timeout "$VALIDATION_TIMEOUT_SECONDS" validate_backup_content_safety "$sql_file"; then
            log_error "Backup content safety validation failed"
            exit 1
        fi
    fi
    
    # Step 8: Create pre-restore backup
    if [[ "$CREATE_BACKUP_BEFORE_RESTORE" == "true" ]]; then
        if ! create_pre_restore_backup; then
            log_warning "Pre-restore backup failed, but continuing..."
        fi
    fi
    
    # Step 9: Perform restore
    if ! perform_restore "$sql_file"; then
        log_error "Database restore failed"
        exit 1
    fi
    
    # Step 10: Post-restore safety validation
    if [[ "$SAFETY_VALIDATION_REQUIRED" == "true" ]]; then
        if ! validate_restored_database_safety; then
            log_error "Post-restore safety validation failed"
            log_error "Database may be in an unsafe state - immediate attention required"
            exit 1
        fi
    fi
    
    log_info "Database restore completed successfully"
    log_security "Restore process completed successfully"
    log_safety "All safety validations passed"
    
    echo
    echo "==============================================="
    echo "RESTORE COMPLETED SUCCESSFULLY"
    echo "==============================================="
    echo "Database: $DB_NAME"
    echo "Restored from: $(basename "$backup_file")"
    echo "Safety validation: PASSED"
    echo "==============================================="
    
    return 0
}

# ===============================================
# Script Execution
# ===============================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi