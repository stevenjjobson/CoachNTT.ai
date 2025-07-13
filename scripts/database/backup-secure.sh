#!/bin/bash

# ===============================================
# Secure Encrypted Database Backup Script
# ===============================================
# Safety-first encrypted backup system for CoachNTT.ai
# Creates encrypted, validated backups with safety verification
# ===============================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ===============================================
# Configuration and Constants
# ===============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKUP_DIR="${POSTGRES_BACKUP_PATH:-./data/postgres-backups}"
readonly LOG_FILE="${BACKUP_DIR}/backup.log"
readonly AUDIT_LOG="${BACKUP_DIR}/backup-audit.log"
readonly ENCRYPTION_KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-/etc/ccp/backup.key}"

# Database configuration
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"

# Backup configuration
readonly BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
readonly COMPRESSION_LEVEL="${BACKUP_COMPRESSION_LEVEL:-9}"
readonly ENCRYPTION_ALGORITHM="aes-256-cbc"
readonly SAFETY_VALIDATION_REQUIRED=true

# Safety thresholds
readonly MIN_BACKUP_SIZE_MB=1
readonly MAX_BACKUP_SIZE_GB=10
readonly SAFETY_SCHEMA_REQUIRED="safety"

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

# ===============================================
# Safety Validation Functions
# ===============================================
validate_environment() {
    log_info "Validating backup environment..."
    
    # Check required directories
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        chmod 750 "$BACKUP_DIR"
    fi
    
    # Check database connectivity
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        log_error "Database not accessible: $DB_HOST:$DB_PORT/$DB_NAME"
        return 1
    fi
    
    # Check encryption key
    if [[ ! -f "$ENCRYPTION_KEY_FILE" ]]; then
        log_info "Generating new encryption key..."
        if ! generate_encryption_key; then
            log_error "Failed to generate encryption key"
            return 1
        fi
    fi
    
    # Validate key permissions
    local key_perms
    key_perms=$(stat -c %a "$ENCRYPTION_KEY_FILE" 2>/dev/null || echo "000")
    if [[ "$key_perms" != "600" ]]; then
        log_security "Fixing encryption key permissions: $key_perms -> 600"
        chmod 600 "$ENCRYPTION_KEY_FILE"
    fi
    
    # Check required tools
    local required_tools=("pg_dump" "gzip" "openssl" "sha256sum")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: $tool"
            return 1
        fi
    done
    
    log_safety "Environment validation passed"
    return 0
}

validate_safety_schema() {
    log_safety "Validating safety schema presence..."
    
    # Check if safety schema exists
    local schema_exists
    schema_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name='$SAFETY_SCHEMA_REQUIRED');" 2>/dev/null | xargs)
    
    if [[ "$schema_exists" != "t" ]]; then
        log_error "Safety schema '$SAFETY_SCHEMA_REQUIRED' not found - backup rejected"
        return 1
    fi
    
    # Check safety tables exist
    local safety_tables=("memory_abstractions" "abstraction_patterns" "reference_validation_rules")
    for table in "${safety_tables[@]}"; do
        local table_exists
        table_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='$SAFETY_SCHEMA_REQUIRED' AND table_name='$table');" 2>/dev/null | xargs)
        
        if [[ "$table_exists" != "t" ]]; then
            log_error "Required safety table not found: $SAFETY_SCHEMA_REQUIRED.$table"
            return 1
        fi
    done
    
    # Validate abstraction enforcement
    local abstraction_count
    abstraction_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM safety.memory_abstractions WHERE validation_status = 'validated';" 2>/dev/null | xargs)
    
    log_safety "Safety schema validation passed: $abstraction_count validated abstractions found"
    return 0
}

check_concrete_references() {
    log_safety "Scanning backup for concrete references..."
    
    local temp_dump_file="$1"
    local concrete_found=false
    
    # Patterns to detect concrete references
    local patterns=(
        "/home/[a-zA-Z0-9_-]+"
        "/Users/[a-zA-Z0-9_-]+"
        "C:\\\\[a-zA-Z0-9_\\\\-]+"
        "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+"
        "password.*=.*['\"][^'\"]+['\"]"
        "secret.*=.*['\"][^'\"]+['\"]"
        "token.*=.*['\"][^'\"]+['\"]"
    )
    
    for pattern in "${patterns[@]}"; do
        if grep -qE "$pattern" "$temp_dump_file" 2>/dev/null; then
            log_error "Concrete reference found in backup: $pattern"
            concrete_found=true
        fi
    done
    
    if [[ "$concrete_found" == "true" ]]; then
        log_error "Backup contains concrete references - safety validation failed"
        return 1
    fi
    
    log_safety "No concrete references found in backup"
    return 0
}

# ===============================================
# Encryption Functions
# ===============================================
generate_encryption_key() {
    log_security "Generating new encryption key..."
    
    # Create key directory if needed
    local key_dir
    key_dir=$(dirname "$ENCRYPTION_KEY_FILE")
    if [[ ! -d "$key_dir" ]]; then
        mkdir -p "$key_dir"
        chmod 700 "$key_dir"
    fi
    
    # Generate 256-bit key
    if ! openssl rand -hex 32 > "$ENCRYPTION_KEY_FILE"; then
        log_error "Failed to generate encryption key"
        return 1
    fi
    
    # Set secure permissions
    chmod 600 "$ENCRYPTION_KEY_FILE"
    chown root:root "$ENCRYPTION_KEY_FILE" 2>/dev/null || true
    
    log_security "Encryption key generated successfully"
    return 0
}

encrypt_backup() {
    local input_file="$1"
    local output_file="$2"
    
    log_security "Encrypting backup: $(basename "$input_file")"
    
    # Generate random IV for each backup
    local iv
    iv=$(openssl rand -hex 16)
    
    # Encrypt with AES-256-CBC
    if ! openssl enc -"$ENCRYPTION_ALGORITHM" -salt -iv "$iv" -K "$(cat "$ENCRYPTION_KEY_FILE")" \
         -in "$input_file" -out "$output_file"; then
        log_error "Backup encryption failed"
        return 1
    fi
    
    # Store IV for decryption
    echo "$iv" > "${output_file}.iv"
    chmod 600 "${output_file}.iv"
    
    log_security "Backup encrypted successfully"
    return 0
}

verify_backup_integrity() {
    local backup_file="$1"
    
    log_info "Verifying backup integrity..."
    
    # Check file exists and is readable
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Check file size
    local file_size_mb
    file_size_mb=$(du -m "$backup_file" | cut -f1)
    
    if [[ $file_size_mb -lt $MIN_BACKUP_SIZE_MB ]]; then
        log_error "Backup file too small: ${file_size_mb}MB (minimum: ${MIN_BACKUP_SIZE_MB}MB)"
        return 1
    fi
    
    if [[ $file_size_mb -gt $((MAX_BACKUP_SIZE_GB * 1024)) ]]; then
        log_error "Backup file too large: ${file_size_mb}MB (maximum: $((MAX_BACKUP_SIZE_GB * 1024))MB)"
        return 1
    fi
    
    # Generate and store checksum
    local checksum
    checksum=$(sha256sum "$backup_file" | cut -d' ' -f1)
    echo "$checksum" > "${backup_file}.sha256"
    
    log_info "Backup integrity verified: ${file_size_mb}MB, checksum: ${checksum:0:16}..."
    return 0
}

# ===============================================
# Backup Functions
# ===============================================
create_database_backup() {
    local timestamp="$1"
    local temp_backup_file="${BACKUP_DIR}/temp_backup_${timestamp}.sql"
    local compressed_file="${BACKUP_DIR}/backup_${timestamp}.sql.gz"
    local encrypted_file="${BACKUP_DIR}/backup_${timestamp}.sql.gz.enc"
    
    log_info "Creating database backup: $DB_NAME"
    
    # Create comprehensive database dump
    if ! pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --clean \
        --create \
        --if-exists \
        --format=plain \
        --encoding=UTF8 \
        --no-owner \
        --no-privileges \
        --schema-order \
        --serializable-deferrable \
        > "$temp_backup_file"; then
        log_error "Database dump failed"
        rm -f "$temp_backup_file"
        return 1
    fi
    
    # Safety validation of backup content
    if [[ "$SAFETY_VALIDATION_REQUIRED" == "true" ]]; then
        if ! check_concrete_references "$temp_backup_file"; then
            log_error "Backup failed safety validation"
            rm -f "$temp_backup_file"
            return 1
        fi
    fi
    
    # Compress backup
    log_info "Compressing backup..."
    if ! gzip -c -"$COMPRESSION_LEVEL" "$temp_backup_file" > "$compressed_file"; then
        log_error "Backup compression failed"
        rm -f "$temp_backup_file" "$compressed_file"
        return 1
    fi
    
    # Encrypt backup
    if ! encrypt_backup "$compressed_file" "$encrypted_file"; then
        log_error "Backup encryption failed"
        rm -f "$temp_backup_file" "$compressed_file" "$encrypted_file"
        return 1
    fi
    
    # Verify integrity
    if ! verify_backup_integrity "$encrypted_file"; then
        log_error "Backup integrity verification failed"
        rm -f "$temp_backup_file" "$compressed_file" "$encrypted_file"
        return 1
    fi
    
    # Clean up temporary files
    rm -f "$temp_backup_file" "$compressed_file"
    
    log_info "Backup created successfully: $(basename "$encrypted_file")"
    echo "$encrypted_file"
    return 0
}

backup_audit_logs() {
    local timestamp="$1"
    local audit_backup_file="${BACKUP_DIR}/audit_logs_${timestamp}.tar.gz.enc"
    
    log_info "Backing up audit logs..."
    
    # Create audit log archive
    local temp_archive="${BACKUP_DIR}/temp_audit_${timestamp}.tar.gz"
    
    if tar -czf "$temp_archive" -C /var/lib/postgresql audit/ 2>/dev/null; then
        # Encrypt audit backup
        if encrypt_backup "$temp_archive" "$audit_backup_file"; then
            verify_backup_integrity "$audit_backup_file"
            rm -f "$temp_archive"
            log_info "Audit logs backed up successfully"
        else
            log_error "Audit log backup encryption failed"
            rm -f "$temp_archive"
            return 1
        fi
    else
        log_info "No audit logs found to backup"
    fi
    
    return 0
}

# ===============================================
# Cleanup Functions
# ===============================================
cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: ${BACKUP_RETENTION_DAYS} days)..."
    
    local deleted_count=0
    
    # Find and delete old backup files
    find "$BACKUP_DIR" -name "backup_*.sql.gz.enc" -mtime +"$BACKUP_RETENTION_DAYS" -type f | while read -r old_backup; do
        local backup_date
        backup_date=$(basename "$old_backup" | sed 's/backup_\(.*\)\.sql\.gz\.enc/\1/')
        
        log_info "Deleting old backup: $(basename "$old_backup")"
        
        # Delete backup and associated files
        rm -f "$old_backup"
        rm -f "${old_backup}.iv"
        rm -f "${old_backup}.sha256"
        
        ((deleted_count++))
        
        log_security "Old backup deleted: $backup_date"
    done
    
    # Clean up old audit backups
    find "$BACKUP_DIR" -name "audit_logs_*.tar.gz.enc" -mtime +"$BACKUP_RETENTION_DAYS" -type f | while read -r old_audit; do
        log_info "Deleting old audit backup: $(basename "$old_audit")"
        rm -f "$old_audit"
        rm -f "${old_audit}.iv"
        rm -f "${old_audit}.sha256"
    done
    
    log_info "Cleanup completed"
    return 0
}

# ===============================================
# Main Backup Process
# ===============================================
main() {
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    
    log_info "Starting secure backup process..."
    log_security "Backup initiated by user: ${USER:-unknown}"
    
    # Step 1: Environment validation
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Step 2: Safety schema validation
    if [[ "$SAFETY_VALIDATION_REQUIRED" == "true" ]]; then
        if ! validate_safety_schema; then
            log_error "Safety schema validation failed"
            exit 1
        fi
    fi
    
    # Step 3: Create database backup
    local backup_file
    if ! backup_file=$(create_database_backup "$timestamp"); then
        log_error "Database backup creation failed"
        exit 1
    fi
    
    # Step 4: Backup audit logs
    if ! backup_audit_logs "$timestamp"; then
        log_error "Audit log backup failed"
        # Continue - not critical
    fi
    
    # Step 5: Cleanup old backups
    if ! cleanup_old_backups; then
        log_error "Backup cleanup failed"
        # Continue - not critical
    fi
    
    # Step 6: Final verification
    if [[ -f "$backup_file" ]]; then
        local backup_size
        backup_size=$(du -h "$backup_file" | cut -f1)
        
        log_info "Backup process completed successfully"
        log_info "Backup file: $(basename "$backup_file")"
        log_info "Backup size: $backup_size"
        log_security "Backup completed: $backup_file"
        
        # Create backup manifest
        cat > "${BACKUP_DIR}/backup_${timestamp}.manifest" << EOF
{
    "timestamp": "$timestamp",
    "database": "$DB_NAME",
    "backup_file": "$(basename "$backup_file")",
    "size": "$backup_size",
    "checksum": "$(cat "${backup_file}.sha256")",
    "safety_validated": $SAFETY_VALIDATION_REQUIRED,
    "encrypted": true,
    "retention_days": $BACKUP_RETENTION_DAYS
}
EOF
        
        echo "Backup completed: $backup_file"
    else
        log_error "Backup file not found after completion"
        exit 1
    fi
    
    return 0
}

# ===============================================
# Script Execution
# ===============================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi