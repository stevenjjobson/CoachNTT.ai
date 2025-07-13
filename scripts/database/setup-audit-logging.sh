#!/bin/bash

# ===============================================
# Audit Logging Setup Script
# ===============================================
# Comprehensive audit logging configuration for CoachNTT.ai
# Sets up security monitoring, log rotation, and alert systems
# ===============================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ===============================================
# Configuration and Constants
# ===============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/lib/postgresql/logs/audit-setup.log"
readonly AUDIT_CONFIG_DIR="/etc/ccp/audit"
readonly LOGROTATE_CONFIG_DIR="/etc/logrotate.d"

# Database configuration
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"

# Audit configuration
readonly AUDIT_LOG_RETENTION_DAYS="${AUDIT_LOG_RETENTION_DAYS:-365}"
readonly SECURITY_LOG_RETENTION_DAYS="${SECURITY_LOG_RETENTION_DAYS:-90}"
readonly LOG_COMPRESSION_ENABLED=true
readonly REAL_TIME_MONITORING=true

# Alert thresholds
readonly FAILED_AUTH_THRESHOLD=5
readonly CONCURRENT_CONN_THRESHOLD=80
readonly LARGE_QUERY_THRESHOLD_MS=10000
readonly SUSPICIOUS_PATTERN_THRESHOLD=3

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SECURITY] $message" | tee -a "$LOG_FILE"
}

# ===============================================
# Directory and Permission Setup
# ===============================================
setup_audit_directories() {
    log_info "Setting up audit logging directories..."
    
    # Create audit configuration directory
    if [[ ! -d "$AUDIT_CONFIG_DIR" ]]; then
        mkdir -p "$AUDIT_CONFIG_DIR"
        chmod 750 "$AUDIT_CONFIG_DIR"
    fi
    
    # Create PostgreSQL audit directories
    local audit_dirs=(
        "/var/lib/postgresql/audit"
        "/var/lib/postgresql/logs"
        "/var/lib/postgresql/security"
        "/var/lib/postgresql/monitoring"
    )
    
    for dir in "${audit_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            chown postgres:postgres "$dir"
            chmod 750 "$dir"
            log_info "Created audit directory: $dir"
        fi
    done
    
    return 0
}

# ===============================================
# PostgreSQL Audit Configuration
# ===============================================
configure_postgresql_audit() {
    log_info "Configuring PostgreSQL audit settings..."
    
    # Create audit configuration SQL
    cat > "${AUDIT_CONFIG_DIR}/audit_config.sql" << 'EOF'
-- ===============================================
-- PostgreSQL Audit Configuration
-- ===============================================

-- Enable comprehensive logging
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 100;
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_hostname = on;
ALTER SYSTEM SET log_line_prefix = '%m [%p] %q%u@%d from %h [%x] ';

-- Security-focused logging
ALTER SYSTEM SET log_checkpoints = on;
ALTER SYSTEM SET log_lock_waits = on;
ALTER SYSTEM SET log_temp_files = 0;
ALTER SYSTEM SET log_autovacuum_min_duration = 0;

-- Error and warning logging
ALTER SYSTEM SET log_min_error_statement = 'error';
ALTER SYSTEM SET log_error_verbosity = 'verbose';

-- Log destination configuration
ALTER SYSTEM SET logging_collector = on;
ALTER SYSTEM SET log_destination = 'stderr,syslog';
ALTER SYSTEM SET log_directory = '/var/lib/postgresql/logs';
ALTER SYSTEM SET log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log';
ALTER SYSTEM SET log_file_mode = 0640;
ALTER SYSTEM SET log_rotation_age = '1d';
ALTER SYSTEM SET log_rotation_size = '100MB';
ALTER SYSTEM SET log_truncate_on_rotation = on;

-- Syslog configuration
ALTER SYSTEM SET syslog_facility = 'local0';
ALTER SYSTEM SET syslog_ident = 'postgres-ccp';

-- Reload configuration
SELECT pg_reload_conf();
EOF

    # Apply audit configuration
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "${AUDIT_CONFIG_DIR}/audit_config.sql"; then
        log_info "PostgreSQL audit configuration applied successfully"
    else
        log_error "Failed to apply PostgreSQL audit configuration"
        return 1
    fi
    
    return 0
}

# ===============================================
# Log Rotation Configuration
# ===============================================
setup_log_rotation() {
    log_info "Setting up log rotation for audit logs..."
    
    # PostgreSQL logs rotation
    cat > "${LOGROTATE_CONFIG_DIR}/postgresql-ccp" << EOF
/var/lib/postgresql/logs/*.log {
    daily
    rotate ${SECURITY_LOG_RETENTION_DAYS}
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    create 640 postgres postgres
    postrotate
        /usr/bin/killall -HUP rsyslog 2>/dev/null || true
        echo "\$(date): PostgreSQL log rotated" >> /var/lib/postgresql/logs/rotation.log
    endscript
}
EOF

    # Audit logs rotation
    cat > "${LOGROTATE_CONFIG_DIR}/audit-ccp" << EOF
/var/lib/postgresql/audit/*.log {
    daily
    rotate ${AUDIT_LOG_RETENTION_DAYS}
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    create 640 postgres postgres
    # Do not truncate audit logs - append only
    copytruncate
    postrotate
        echo "\$(date): Audit log rotated" >> /var/lib/postgresql/audit/rotation.log
    endscript
}
EOF

    # Security monitoring logs rotation
    cat > "${LOGROTATE_CONFIG_DIR}/security-monitoring-ccp" << EOF
/var/lib/postgresql/security/*.log {
    daily
    rotate 90
    missingok
    notifempty
    compress
    delaycompress
    create 640 postgres postgres
    postrotate
        echo "\$(date): Security monitoring log rotated" >> /var/lib/postgresql/security/rotation.log
    endscript
}
EOF

    log_info "Log rotation configuration completed"
    return 0
}

# ===============================================
# Real-Time Security Monitoring
# ===============================================
setup_security_monitoring() {
    log_info "Setting up real-time security monitoring..."
    
    # Create security monitoring script
    cat > "${AUDIT_CONFIG_DIR}/security_monitor.sh" << 'EOF'
#!/bin/bash

# ===============================================
# Real-Time Security Monitoring for PostgreSQL
# ===============================================

set -euo pipefail

readonly SECURITY_LOG="/var/lib/postgresql/security/security_monitor.log"
readonly ALERT_LOG="/var/lib/postgresql/security/alerts.log"
readonly PG_LOG_DIR="/var/lib/postgresql/logs"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"

# Alert thresholds
readonly FAILED_AUTH_THRESHOLD=5
readonly CONCURRENT_CONN_THRESHOLD=80
readonly LARGE_QUERY_THRESHOLD_MS=10000

log_security() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SECURITY] $1" >> "$SECURITY_LOG"
}

log_alert() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ALERT] $message" >> "$ALERT_LOG"
    logger -p local0.warning "CCP-SECURITY-ALERT: $message"
}

check_failed_authentications() {
    local failed_count
    failed_count=$(tail -n 1000 "$PG_LOG_DIR"/postgresql-*.log 2>/dev/null | grep -c "authentication failed" || echo "0")
    
    if [[ $failed_count -gt $FAILED_AUTH_THRESHOLD ]]; then
        log_alert "High number of authentication failures: $failed_count"
        
        # Get unique failing IPs
        local failing_ips
        failing_ips=$(tail -n 1000 "$PG_LOG_DIR"/postgresql-*.log 2>/dev/null | grep "authentication failed" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sort | uniq -c | sort -nr)
        log_alert "Failing IPs: $failing_ips"
    fi
}

check_connection_count() {
    local active_connections
    active_connections=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)
    
    if [[ $active_connections -gt $CONCURRENT_CONN_THRESHOLD ]]; then
        log_alert "High number of concurrent connections: $active_connections"
    fi
    
    log_security "Active connections: $active_connections"
}

check_long_running_queries() {
    local long_queries
    long_queries=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT count(*) FROM pg_stat_activity 
        WHERE state = 'active' 
        AND query_start < NOW() - INTERVAL '${LARGE_QUERY_THRESHOLD_MS} milliseconds'
        AND query NOT LIKE '%pg_stat_activity%';" 2>/dev/null | xargs)
    
    if [[ $long_queries -gt 0 ]]; then
        log_alert "Long running queries detected: $long_queries"
        
        # Log details of long running queries
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
            SELECT pid, usename, client_addr, query_start, left(query, 100) 
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND query_start < NOW() - INTERVAL '${LARGE_QUERY_THRESHOLD_MS} milliseconds'
            AND query NOT LIKE '%pg_stat_activity%';" >> "$SECURITY_LOG" 2>/dev/null
    fi
}

check_suspicious_queries() {
    # Check for potentially dangerous SQL patterns
    local suspicious_patterns=(
        "DROP DATABASE"
        "DROP TABLE"
        "ALTER USER.*SUPERUSER"
        "COPY.*FROM PROGRAM"
        "SELECT.*pg_read_file"
        "SELECT.*pg_ls_dir"
    )
    
    for pattern in "${suspicious_patterns[@]}"; do
        local matches
        matches=$(tail -n 100 "$PG_LOG_DIR"/postgresql-*.log 2>/dev/null | grep -ci "$pattern" || echo "0")
        
        if [[ $matches -gt 0 ]]; then
            log_alert "Suspicious query pattern detected: $pattern ($matches matches)"
        fi
    done
}

check_safety_violations() {
    # Check for safety validation failures
    local safety_violations
    safety_violations=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT count(*) FROM audit.safety_validations 
        WHERE created_at > NOW() - INTERVAL '1 hour' 
        AND validation_result = 'failed';" 2>/dev/null | xargs)
    
    if [[ $safety_violations -gt 0 ]]; then
        log_alert "Safety validation failures in last hour: $safety_violations"
    fi
}

# Main monitoring loop
main() {
    log_security "Security monitoring started"
    
    while true; do
        check_failed_authentications
        check_connection_count
        check_long_running_queries
        check_suspicious_queries
        check_safety_violations
        
        sleep 60  # Check every minute
    done
}

# Trap to handle shutdown
trap 'log_security "Security monitoring stopped"; exit 0' TERM INT

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
EOF

    chmod +x "${AUDIT_CONFIG_DIR}/security_monitor.sh"
    
    # Create systemd service for security monitoring
    if command -v systemctl >/dev/null 2>&1; then
        cat > "/etc/systemd/system/ccp-security-monitor.service" << EOF
[Unit]
Description=CoachNTT.ai Security Monitor
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=postgres
Group=postgres
ExecStart=${AUDIT_CONFIG_DIR}/security_monitor.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable ccp-security-monitor.service
        log_info "Security monitoring service created and enabled"
    fi
    
    return 0
}

# ===============================================
# Database Audit Triggers Setup
# ===============================================
setup_audit_triggers() {
    log_info "Setting up database audit triggers..."
    
    cat > "${AUDIT_CONFIG_DIR}/audit_triggers.sql" << 'EOF'
-- ===============================================
-- Advanced Audit Triggers for Security Monitoring
-- ===============================================

-- Function to log security events with detailed context
CREATE OR REPLACE FUNCTION audit.log_security_event(
    event_type VARCHAR(50),
    event_details JSONB DEFAULT '{}'::jsonb,
    severity VARCHAR(20) DEFAULT 'INFO'
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO audit.security_events (
        event_type,
        event_details,
        user_context,
        ip_address,
        session_id,
        severity
    ) VALUES (
        event_type,
        event_details || jsonb_build_object(
            'session_user', session_user,
            'current_user', current_user,
            'application_name', current_setting('application_name'),
            'client_encoding', current_setting('client_encoding'),
            'transaction_timestamp', transaction_timestamp()
        ),
        jsonb_build_object(
            'backend_pid', pg_backend_pid(),
            'backend_start', pg_postmaster_start_time(),
            'transaction_id', txid_current()
        ),
        inet_client_addr(),
        current_setting('ccp.session_id', true),
        severity
    );
END;
$$;

-- Trigger for DDL operations (schema changes)
CREATE OR REPLACE FUNCTION audit.log_ddl_operations()
RETURNS event_trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    ddl_info RECORD;
BEGIN
    FOR ddl_info IN SELECT * FROM pg_event_trigger_ddl_commands()
    LOOP
        PERFORM audit.log_security_event(
            'ddl_operation',
            jsonb_build_object(
                'command_tag', ddl_info.command_tag,
                'object_type', ddl_info.object_type,
                'object_identity', ddl_info.object_identity,
                'in_extension', ddl_info.in_extension
            ),
            'WARNING'
        );
    END LOOP;
END;
$$;

-- Create DDL event trigger
DROP EVENT TRIGGER IF EXISTS audit_ddl_operations;
CREATE EVENT TRIGGER audit_ddl_operations
    ON ddl_command_end
    EXECUTE FUNCTION audit.log_ddl_operations();

-- Trigger for dropped objects
CREATE OR REPLACE FUNCTION audit.log_drop_operations()
RETURNS event_trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    drop_info RECORD;
BEGIN
    FOR drop_info IN SELECT * FROM pg_event_trigger_dropped_objects()
    LOOP
        PERFORM audit.log_security_event(
            'drop_operation',
            jsonb_build_object(
                'object_type', drop_info.object_type,
                'object_name', drop_info.object_name,
                'object_identity', drop_info.object_identity,
                'is_temporary', drop_info.is_temporary
            ),
            'ERROR'
        );
    END LOOP;
END;
$$;

-- Create drop event trigger
DROP EVENT TRIGGER IF EXISTS audit_drop_operations;
CREATE EVENT TRIGGER audit_drop_operations
    ON sql_drop
    EXECUTE FUNCTION audit.log_drop_operations();

-- Function to monitor privilege escalations
CREATE OR REPLACE FUNCTION audit.check_privilege_escalation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Check for superuser grants
    IF TG_TABLE_NAME = 'pg_authid' AND NEW.rolsuper = true AND OLD.rolsuper = false THEN
        PERFORM audit.log_security_event(
            'privilege_escalation',
            jsonb_build_object(
                'role_name', NEW.rolname,
                'operation', 'superuser_granted'
            ),
            'CRITICAL'
        );
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create privilege escalation trigger (if accessible)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pg_authid') THEN
        CREATE TRIGGER audit_privilege_escalation
            AFTER UPDATE ON pg_authid
            FOR EACH ROW
            EXECUTE FUNCTION audit.check_privilege_escalation();
    END IF;
EXCEPTION
    WHEN insufficient_privilege THEN
        -- Skip if we don't have permission
        NULL;
END $$;

-- Function to monitor safety schema changes
CREATE OR REPLACE FUNCTION audit.monitor_safety_schema_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Log any changes to safety schema objects
    PERFORM audit.log_security_event(
        'safety_schema_modification',
        jsonb_build_object(
            'table_name', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            'operation', TG_OP,
            'old_data', CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
            'new_data', CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END
        ),
        'WARNING'
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$;

-- Apply safety schema monitoring to key tables
CREATE TRIGGER audit_abstraction_patterns_changes
    AFTER INSERT OR UPDATE OR DELETE ON safety.abstraction_patterns
    FOR EACH ROW EXECUTE FUNCTION audit.monitor_safety_schema_changes();

CREATE TRIGGER audit_reference_validation_rules_changes
    AFTER INSERT OR UPDATE OR DELETE ON safety.reference_validation_rules
    FOR EACH ROW EXECUTE FUNCTION audit.monitor_safety_schema_changes();

-- Function to detect bulk operations
CREATE OR REPLACE FUNCTION audit.detect_bulk_operations()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    stmt_count INTEGER;
BEGIN
    -- Count statements in current transaction
    SELECT count(*) INTO stmt_count
    FROM pg_stat_statements 
    WHERE userid = (SELECT usesysid FROM pg_user WHERE usename = session_user)
    AND calls > 10;  -- Threshold for bulk operations
    
    IF stmt_count > 100 THEN  -- Large bulk operation threshold
        PERFORM audit.log_security_event(
            'bulk_operation_detected',
            jsonb_build_object(
                'statement_count', stmt_count,
                'table_name', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'operation', TG_OP
            ),
            'WARNING'
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
EXCEPTION
    WHEN OTHERS THEN
        -- If pg_stat_statements not available, skip
        RETURN COALESCE(NEW, OLD);
END;
$$;

-- Apply bulk operation detection to key tables
CREATE TRIGGER audit_bulk_memory_operations
    AFTER INSERT OR UPDATE OR DELETE ON public.cognitive_memory
    FOR EACH STATEMENT EXECUTE FUNCTION audit.detect_bulk_operations();

COMMENT ON FUNCTION audit.log_security_event(VARCHAR, JSONB, VARCHAR) IS 'Central function for logging security events with full context';
COMMENT ON EVENT TRIGGER audit_ddl_operations IS 'Monitors all DDL operations for security audit';
COMMENT ON EVENT TRIGGER audit_drop_operations IS 'Monitors all DROP operations for security audit';
EOF

    # Apply audit triggers
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "${AUDIT_CONFIG_DIR}/audit_triggers.sql"; then
        log_info "Database audit triggers configured successfully"
    else
        log_error "Failed to configure database audit triggers"
        return 1
    fi
    
    return 0
}

# ===============================================
# Syslog Configuration
# ===============================================
setup_syslog() {
    log_info "Configuring syslog for PostgreSQL audit logging..."
    
    # Create rsyslog configuration for PostgreSQL
    cat > "/etc/rsyslog.d/30-postgresql-ccp.conf" << EOF
# PostgreSQL logging for CoachNTT.ai
\$ModLoad imudp
\$UDPServerRun 514
\$UDPServerAddress 127.0.0.1

# PostgreSQL audit logs
local0.*    /var/lib/postgresql/audit/postgresql-audit.log;RSYSLOG_FileFormat
& stop

# Security alerts
local0.warning    /var/lib/postgresql/security/security-alerts.log;RSYSLOG_FileFormat
EOF

    # Restart rsyslog if running
    if systemctl is-active --quiet rsyslog; then
        systemctl restart rsyslog
        log_info "Rsyslog restarted with PostgreSQL configuration"
    fi
    
    return 0
}

# ===============================================
# Audit Report Generation
# ===============================================
create_audit_reports() {
    log_info "Setting up audit report generation..."
    
    cat > "${AUDIT_CONFIG_DIR}/generate_audit_report.sh" << 'EOF'
#!/bin/bash

# ===============================================
# Audit Report Generator
# ===============================================

set -euo pipefail

readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly REPORT_DIR="/var/lib/postgresql/audit/reports"

mkdir -p "$REPORT_DIR"

# Generate daily security report
generate_daily_report() {
    local report_date="${1:-$(date '+%Y-%m-%d')}"
    local report_file="${REPORT_DIR}/security_report_${report_date}.json"
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT jsonb_build_object(
        'report_date', '$report_date',
        'total_events', (SELECT count(*) FROM audit.security_events WHERE DATE(created_at) = '$report_date'),
        'critical_events', (SELECT count(*) FROM audit.security_events WHERE DATE(created_at) = '$report_date' AND severity = 'CRITICAL'),
        'error_events', (SELECT count(*) FROM audit.security_events WHERE DATE(created_at) = '$report_date' AND severity = 'ERROR'),
        'warning_events', (SELECT count(*) FROM audit.security_events WHERE DATE(created_at) = '$report_date' AND severity = 'WARNING'),
        'safety_validations', (SELECT count(*) FROM audit.safety_validations WHERE DATE(created_at) = '$report_date'),
        'validation_failures', (SELECT count(*) FROM audit.safety_validations WHERE DATE(created_at) = '$report_date' AND validation_result = 'failed'),
        'unique_users', (SELECT count(DISTINCT user_context->>'session_user') FROM audit.security_events WHERE DATE(created_at) = '$report_date'),
        'unique_ips', (SELECT count(DISTINCT ip_address) FROM audit.security_events WHERE DATE(created_at) = '$report_date' AND ip_address IS NOT NULL),
        'top_event_types', (
            SELECT jsonb_agg(jsonb_build_object('event_type', event_type, 'count', event_count))
            FROM (
                SELECT event_type, count(*) as event_count
                FROM audit.security_events 
                WHERE DATE(created_at) = '$report_date'
                GROUP BY event_type
                ORDER BY count(*) DESC
                LIMIT 10
            ) top_events
        )
    );" -t > "$report_file"
    
    echo "Daily report generated: $report_file"
}

# Generate weekly summary
generate_weekly_report() {
    local week_start="${1:-$(date -d 'last monday' '+%Y-%m-%d')}"
    local week_end="$(date -d "$week_start + 6 days" '+%Y-%m-%d')"
    local report_file="${REPORT_DIR}/weekly_summary_${week_start}_${week_end}.json"
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT jsonb_build_object(
        'week_start', '$week_start',
        'week_end', '$week_end',
        'total_events', (SELECT count(*) FROM audit.security_events WHERE created_at >= '$week_start' AND created_at < '$week_end'::date + interval '1 day'),
        'safety_score_avg', (SELECT avg(abstraction_score) FROM audit.safety_validations WHERE created_at >= '$week_start' AND created_at < '$week_end'::date + interval '1 day'),
        'critical_incidents', (SELECT count(*) FROM audit.security_events WHERE created_at >= '$week_start' AND created_at < '$week_end'::date + interval '1 day' AND severity = 'CRITICAL'),
        'trend_analysis', (
            SELECT jsonb_agg(jsonb_build_object('date', event_date, 'count', daily_count))
            FROM (
                SELECT DATE(created_at) as event_date, count(*) as daily_count
                FROM audit.security_events 
                WHERE created_at >= '$week_start' AND created_at < '$week_end'::date + interval '1 day'
                GROUP BY DATE(created_at)
                ORDER BY event_date
            ) daily_trends
        )
    );" -t > "$report_file"
    
    echo "Weekly report generated: $report_file"
}

case "${1:-daily}" in
    daily)
        generate_daily_report
        ;;
    weekly)
        generate_weekly_report
        ;;
    *)
        echo "Usage: $0 [daily|weekly]"
        exit 1
        ;;
esac
EOF

    chmod +x "${AUDIT_CONFIG_DIR}/generate_audit_report.sh"
    
    # Create cron job for daily reports
    echo "0 1 * * * postgres ${AUDIT_CONFIG_DIR}/generate_audit_report.sh daily" > /etc/cron.d/ccp-audit-reports
    echo "0 2 * * 1 postgres ${AUDIT_CONFIG_DIR}/generate_audit_report.sh weekly" >> /etc/cron.d/ccp-audit-reports
    
    log_info "Audit report generation configured"
    return 0
}

# ===============================================
# Main Setup Process
# ===============================================
main() {
    log_info "Starting audit logging setup for CoachNTT.ai..."
    
    # Step 1: Setup directories and permissions
    if ! setup_audit_directories; then
        log_error "Failed to setup audit directories"
        exit 1
    fi
    
    # Step 2: Configure PostgreSQL audit settings
    if ! configure_postgresql_audit; then
        log_error "Failed to configure PostgreSQL audit settings"
        exit 1
    fi
    
    # Step 3: Setup log rotation
    if ! setup_log_rotation; then
        log_error "Failed to setup log rotation"
        exit 1
    fi
    
    # Step 4: Setup syslog
    if ! setup_syslog; then
        log_error "Failed to setup syslog"
        exit 1
    fi
    
    # Step 5: Setup database audit triggers
    if ! setup_audit_triggers; then
        log_error "Failed to setup audit triggers"
        exit 1
    fi
    
    # Step 6: Setup security monitoring
    if [[ "$REAL_TIME_MONITORING" == "true" ]]; then
        if ! setup_security_monitoring; then
            log_error "Failed to setup security monitoring"
            exit 1
        fi
    fi
    
    # Step 7: Setup audit reports
    if ! create_audit_reports; then
        log_error "Failed to setup audit reports"
        exit 1
    fi
    
    log_info "Audit logging setup completed successfully"
    log_security "Audit system initialized and configured"
    
    echo
    echo "==============================================="
    echo "AUDIT LOGGING SETUP COMPLETED"
    echo "==============================================="
    echo "Configuration directory: $AUDIT_CONFIG_DIR"
    echo "Log retention:"
    echo "  - Security logs: ${SECURITY_LOG_RETENTION_DAYS} days"
    echo "  - Audit logs: ${AUDIT_LOG_RETENTION_DAYS} days"
    echo "Real-time monitoring: $REAL_TIME_MONITORING"
    echo "==============================================="
    
    return 0
}

# ===============================================
# Script Execution
# ===============================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi