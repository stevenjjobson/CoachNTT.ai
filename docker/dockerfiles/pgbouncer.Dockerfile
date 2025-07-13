# ===============================================
# Secure PgBouncer Connection Pool - Safety-First Database Access
# ===============================================
# Security-hardened PgBouncer container for CoachNTT.ai
# Provides secure, monitored connection pooling
# ===============================================

FROM alpine:3.18

# ===============================================
# Security Labels and Metadata  
# ===============================================
LABEL org.opencontainers.image.title="CoachNTT.ai Secure PgBouncer"
LABEL org.opencontainers.image.description="Security-hardened connection pooling for safety-first database access"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="2025-01-13"
LABEL security.level="high"
LABEL safety.monitoring.enabled="true"

# ===============================================
# Security Hardening - Package Installation
# ===============================================
RUN apk add --no-cache \
    # Core PgBouncer and dependencies
    pgbouncer \
    postgresql-client \
    # Security monitoring tools
    htop \
    tcpdump \
    netstat-nat \
    # Logging and audit
    logrotate \
    rsyslog \
    # SSL/TLS support
    openssl \
    ca-certificates \
    # Process monitoring
    procps \
    # File integrity
    aide \
    # Network security
    iptables \
    # Clean up
    && rm -rf /var/cache/apk/*

# ===============================================
# Create Non-Root User for Security
# ===============================================
RUN addgroup -g 999 pgbouncer && \
    adduser -u 999 -G pgbouncer -s /bin/sh -D pgbouncer && \
    # Create secure directories
    mkdir -p /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer && \
    # Set secure ownership
    chown -R pgbouncer:pgbouncer /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer && \
    # Set secure permissions
    chmod 750 /etc/pgbouncer /var/log/pgbouncer /var/run/pgbouncer

# ===============================================
# Security Configuration Files
# ===============================================
# Copy secure PgBouncer configuration
COPY pgbouncer-secure.ini /etc/pgbouncer/pgbouncer.ini
COPY userlist-secure.txt /etc/pgbouncer/userlist.txt

# Set secure permissions on config files
RUN chown pgbouncer:pgbouncer /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/userlist.txt && \
    chmod 640 /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/userlist.txt

# ===============================================
# Monitoring and Logging Setup
# ===============================================
# Create monitoring script
RUN cat > /usr/local/bin/pgbouncer-monitor.sh << 'EOF'
#!/bin/sh
# PgBouncer monitoring and safety checks

LOG_FILE="/var/log/pgbouncer/monitor.log"
SECURITY_LOG="/var/log/pgbouncer/security.log"

log_security() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SECURITY] $1" >> "$SECURITY_LOG"
}

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1" >> "$LOG_FILE"
}

# Monitor connection counts
check_connections() {
    local active_connections
    active_connections=$(psql -p 6432 -U pgbouncer pgbouncer -t -c "SHOW STATS;" 2>/dev/null | wc -l)
    
    if [ "$active_connections" -gt 80 ]; then
        log_security "High connection count detected: $active_connections"
    fi
    
    log_info "Active connections: $active_connections"
}

# Check for suspicious connection patterns
check_security() {
    # Check for failed authentication attempts
    local failed_auths
    failed_auths=$(grep -c "authentication failed" /var/log/pgbouncer/pgbouncer.log 2>/dev/null || echo "0")
    
    if [ "$failed_auths" -gt 5 ]; then
        log_security "Multiple authentication failures detected: $failed_auths"
    fi
    
    # Check for unusual connection sources
    netstat -tn | grep :6432 | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -10 >> "$LOG_FILE"
}

# Main monitoring loop
while true; do
    check_connections
    check_security
    sleep 30
done
EOF

RUN chmod +x /usr/local/bin/pgbouncer-monitor.sh && \
    chown pgbouncer:pgbouncer /usr/local/bin/pgbouncer-monitor.sh

# ===============================================
# Health Check Script
# ===============================================
RUN cat > /usr/local/bin/pgbouncer-healthcheck.sh << 'EOF'
#!/bin/sh
# Comprehensive health check for PgBouncer

set -e

# Check if PgBouncer is responding
if ! psql -p 6432 -U pgbouncer pgbouncer -c "SHOW VERSION;" >/dev/null 2>&1; then
    echo "PgBouncer not responding"
    exit 1
fi

# Check connection to backend database
if ! psql -p 6432 -U ccp_user cognitive_coding_partner -c "SELECT 1;" >/dev/null 2>&1; then
    echo "Backend database connection failed"
    exit 1
fi

# Check configuration integrity
if [ ! -f /etc/pgbouncer/pgbouncer.ini ]; then
    echo "Configuration file missing"
    exit 1
fi

# Check log directory permissions
if [ ! -w /var/log/pgbouncer ]; then
    echo "Log directory not writable"
    exit 1
fi

echo "PgBouncer healthy"
exit 0
EOF

RUN chmod +x /usr/local/bin/pgbouncer-healthcheck.sh && \
    chown pgbouncer:pgbouncer /usr/local/bin/pgbouncer-healthcheck.sh

# ===============================================
# Startup Script with Security Validation
# ===============================================
RUN cat > /usr/local/bin/pgbouncer-start.sh << 'EOF'
#!/bin/sh
# Secure startup script for PgBouncer

set -e

LOG_FILE="/var/log/pgbouncer/startup.log"

log_startup() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_startup "Starting secure PgBouncer initialization..."

# Validate configuration files exist and have correct permissions
if [ ! -f /etc/pgbouncer/pgbouncer.ini ]; then
    log_startup "ERROR: pgbouncer.ini not found"
    exit 1
fi

if [ ! -f /etc/pgbouncer/userlist.txt ]; then
    log_startup "ERROR: userlist.txt not found"
    exit 1
fi

# Check file permissions
config_perms=$(stat -c %a /etc/pgbouncer/pgbouncer.ini)
if [ "$config_perms" != "640" ]; then
    log_startup "WARNING: pgbouncer.ini permissions not secure: $config_perms"
fi

# Validate configuration syntax
if ! pgbouncer -t /etc/pgbouncer/pgbouncer.ini; then
    log_startup "ERROR: Configuration validation failed"
    exit 1
fi

log_startup "Configuration validation passed"

# Start monitoring in background
/usr/local/bin/pgbouncer-monitor.sh &
monitor_pid=$!
log_startup "Monitoring started with PID: $monitor_pid"

# Start PgBouncer with security logging
log_startup "Starting PgBouncer..."
exec pgbouncer -v /etc/pgbouncer/pgbouncer.ini
EOF

RUN chmod +x /usr/local/bin/pgbouncer-start.sh && \
    chown pgbouncer:pgbouncer /usr/local/bin/pgbouncer-start.sh

# ===============================================
# File Integrity Monitoring
# ===============================================
RUN aide --init && \
    mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# ===============================================
# Security Hardening - Final Steps
# ===============================================
# Remove unnecessary packages and files
RUN rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/* \
           /usr/share/man/* \
           /usr/share/doc/*

# Set secure umask
RUN echo 'umask 027' >> /etc/profile

# Expose PgBouncer port
EXPOSE 6432

# Set working directory
WORKDIR /var/log/pgbouncer

# Switch to non-root user
USER pgbouncer

# ===============================================
# Health Check Configuration
# ===============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/pgbouncer-healthcheck.sh

# ===============================================
# Secure Startup Command
# ===============================================
CMD ["/usr/local/bin/pgbouncer-start.sh"]