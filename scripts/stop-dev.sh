#!/bin/bash
# Stop development environment for Cognitive Coding Partner

set -e

echo "🛑 Stopping Cognitive Coding Partner Development Environment..."
echo "=================================================="

# Stop all services
docker-compose down

echo "✅ Development environment stopped"
echo ""
echo "To completely remove volumes and data: docker-compose down -v"
echo "To start again: ./scripts/start-dev.sh"