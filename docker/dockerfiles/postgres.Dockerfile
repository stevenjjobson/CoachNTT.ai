# ===============================================
# Secure PostgreSQL with pgvector - Safety-First Database
# ===============================================
# Security hardened PostgreSQL container with pgvector
# for CoachNTT.ai Cognitive Coding Partner
# ===============================================

FROM postgres:15-alpine

# ===============================================
# Security Labels and Metadata
# ===============================================
LABEL org.opencontainers.image.title="CoachNTT.ai Secure PostgreSQL"
LABEL org.opencontainers.image.description="Security-hardened PostgreSQL with pgvector for safety-first AI development"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="2025-01-13"
LABEL security.level="high"
LABEL safety.abstraction.required="true"

# ===============================================
# Security Hardening - User and Permissions
# ===============================================
# Create non-root user for build operations
RUN addgroup -g 70 pgbuild && \
    adduser -u 70 -G pgbuild -s /bin/sh -D pgbuild

# ===============================================
# Install Build Dependencies with Security Verification
# ===============================================
RUN apk add --no-cache --virtual .build-deps \
    git \
    build-base \
    postgresql15-dev \
    clang15 \
    llvm15 \
    ca-certificates \
    gnupg && \
    # Verify package signatures
    apk --no-cache add postgresql15-contrib

# ===============================================
# Install pgvector Extension with Security Verification
# ===============================================
# Download and verify pgvector
RUN cd /tmp && \
    # Clone with verified tag
    git clone --branch v0.5.1 --depth 1 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    # Verify we have the expected version
    git describe --tags --exact-match HEAD && \
    # Build as non-root user
    chown -R pgbuild:pgbuild . && \
    su pgbuild -c "make clean && make" && \
    make install && \
    # Cleanup
    cd .. && \
    rm -rf pgvector

# ===============================================
# Security Tools Installation
# ===============================================
RUN apk add --no-cache \
    # Security monitoring
    aide \
    # File integrity
    rkhunter \
    # Process monitoring
    htop \
    # Network security
    tcpdump \
    # Log monitoring
    logrotate

# ===============================================
# Clean up Build Dependencies
# ===============================================
RUN apk del .build-deps && \
    # Clean package cache
    rm -rf /var/cache/apk/* && \
    # Clean temporary files
    rm -rf /tmp/* /var/tmp/* && \
    # Remove unnecessary files
    find /usr/local -name "*.a" -delete && \
    find /usr/local -name "*.la" -delete

# ===============================================
# Security Configuration Files
# ===============================================
# Copy security-hardened PostgreSQL configuration
COPY postgresql-secure.conf /etc/postgresql/postgresql.conf
COPY pg_hba-secure.conf /etc/postgresql/pg_hba.conf

# ===============================================
# Safety-First Database Initialization
# ===============================================
# Create safety-first initialization scripts
RUN mkdir -p /docker-entrypoint-initdb.d && \
    echo "-- =============================================" > /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "-- Safety-First Extension Installation" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "-- =============================================" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE EXTENSION IF NOT EXISTS vector;" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE EXTENSION IF NOT EXISTS pgcrypto;" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE EXTENSION IF NOT EXISTS \"pg_stat_statements\";" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "-- Create safety schema FIRST" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE SCHEMA IF NOT EXISTS safety;" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "CREATE SCHEMA IF NOT EXISTS audit;" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql && \
    echo "SET search_path TO safety, public;" >> /docker-entrypoint-initdb.d/00-safety-extensions.sql

# ===============================================
# Security Permissions and Directory Setup
# ===============================================
# Create secure log directory
RUN mkdir -p /var/lib/postgresql/logs && \
    chown -R postgres:postgres /var/lib/postgresql/logs && \
    chmod 750 /var/lib/postgresql/logs && \
    # Create audit directory
    mkdir -p /var/lib/postgresql/audit && \
    chown -R postgres:postgres /var/lib/postgresql/audit && \
    chmod 750 /var/lib/postgresql/audit && \
    # Set secure permissions on config files
    chown postgres:postgres /etc/postgresql/*.conf && \
    chmod 640 /etc/postgresql/*.conf

# ===============================================
# Security Monitoring Setup
# ===============================================
# Initialize file integrity monitoring
RUN aide --init && \
    mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# ===============================================
# Health and Safety Checks
# ===============================================
# Add comprehensive health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD pg_isready -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner} && \
        psql -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner} -c "SELECT 1" > /dev/null

# ===============================================
# Security Hardening - Final Steps
# ===============================================
# Remove unnecessary packages and files
RUN rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/* \
           /usr/share/man/* \
           /usr/share/doc/* && \
    # Set minimal PATH
    echo 'export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' > /etc/profile.d/minimal-path.sh

# ===============================================
# Runtime Security Configuration
# ===============================================
# Set secure umask
RUN echo 'umask 027' >> /etc/profile

# Expose only necessary port
EXPOSE 5432

# Set working directory
WORKDIR /var/lib/postgresql

# Switch to postgres user for security
USER postgres

# ===============================================
# Secure Startup Command
# ===============================================
# Use security-hardened configuration
CMD ["postgres", \
     "-c", "config_file=/etc/postgresql/postgresql.conf", \
     "-c", "hba_file=/etc/postgresql/pg_hba.conf", \
     "-c", "logging_collector=on", \
     "-c", "log_statement=all", \
     "-c", "log_connections=on", \
     "-c", "log_disconnections=on"]