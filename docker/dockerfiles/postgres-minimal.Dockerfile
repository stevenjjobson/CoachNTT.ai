# ===============================================
# Minimal PostgreSQL for Memory Testing
# ===============================================
# Lightweight PostgreSQL 15 with pgvector for VPS testing
# Used to validate memory usage under 8GB constraint
# ===============================================

FROM pgvector/pgvector:pg15

# ===============================================
# Minimal Labels
# ===============================================
LABEL org.opencontainers.image.title="CoachNTT.ai Minimal PostgreSQL Test"
LABEL org.opencontainers.image.description="Minimal PostgreSQL for memory testing"
LABEL org.opencontainers.image.version="1.0.0-minimal"

# ===============================================
# Skip pgvector for baseline memory testing
# ===============================================
# We'll test just PostgreSQL base memory usage first
# pgvector can be added later if needed

# ===============================================
# Minimal Configuration
# ===============================================
# Create minimal config for memory testing
RUN mkdir -p /etc/postgresql && \
    echo "# Minimal PostgreSQL Configuration" > /etc/postgresql/postgresql-minimal.conf && \
    echo "listen_addresses = '*'" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "max_connections = 20" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "shared_buffers = 128MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "effective_cache_size = 512MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "work_mem = 2MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "maintenance_work_mem = 32MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "wal_buffers = 4MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "max_wal_size = 256MB" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "checkpoint_completion_target = 0.7" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "random_page_cost = 1.1" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "logging_collector = off" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "log_statement = 'none'" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "autovacuum = on" >> /etc/postgresql/postgresql-minimal.conf && \
    echo "autovacuum_max_workers = 2" >> /etc/postgresql/postgresql-minimal.conf

# ===============================================
# Extensions Setup
# ===============================================
RUN echo "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" > /docker-entrypoint-initdb.d/00-extensions.sql && \
    echo "CREATE EXTENSION IF NOT EXISTS vector;" >> /docker-entrypoint-initdb.d/00-extensions.sql

# Expose port
EXPOSE 5432

# Use minimal config
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql-minimal.conf"]