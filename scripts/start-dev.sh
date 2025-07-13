#!/bin/bash
# Start development environment for Cognitive Coding Partner

set -e

echo "🚀 Starting Cognitive Coding Partner Development Environment..."
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  No .env file found. Using default values."
fi

# Copy migration files to where Docker can access them
echo "📁 Preparing database migrations..."
docker-compose run --rm -v $(pwd)/migrations:/migrations postgres echo "Migrations mounted"

# Start PostgreSQL
echo "🐘 Starting PostgreSQL with pgvector..."
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
MAX_TRIES=30
TRIES=0
while ! docker-compose exec postgres pg_isready -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner} > /dev/null 2>&1; do
    TRIES=$((TRIES+1))
    if [ $TRIES -gt $MAX_TRIES ]; then
        echo "❌ PostgreSQL failed to start after $MAX_TRIES attempts"
        docker-compose logs postgres
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""
echo "✅ PostgreSQL is ready!"

# Check if pgvector is installed
echo "🔍 Verifying pgvector installation..."
docker-compose exec postgres psql -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner} -c "SELECT * FROM pg_extension WHERE extname = 'vector';" | grep vector > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ pgvector is installed"
else
    echo "❌ pgvector is not installed"
    exit 1
fi

# Check safety schema
echo "🛡️ Checking safety schema..."
TABLES=$(docker-compose exec postgres psql -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner} -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'safety';")
TABLES=$(echo $TABLES | xargs)  # Trim whitespace
if [ "$TABLES" -gt "0" ]; then
    echo "✅ Safety schema found with $TABLES tables"
else
    echo "⚠️  Safety schema not found. Run database migrations."
fi

echo ""
echo "🎉 Development environment is ready!"
echo "=================================================="
echo "PostgreSQL URL: postgresql://${POSTGRES_USER:-ccp_user}:${POSTGRES_PASSWORD:-ccp_dev_password}@localhost:5432/${POSTGRES_DB:-cognitive_coding_partner}"
echo ""
echo "To stop the environment: ./scripts/stop-dev.sh"
echo "To view logs: docker-compose logs -f postgres"
echo "To connect to PostgreSQL: docker-compose exec postgres psql -U ${POSTGRES_USER:-ccp_user} -d ${POSTGRES_DB:-cognitive_coding_partner}"
echo ""