#!/bin/bash
# ===============================================
# Memory Monitoring Script for PostgreSQL Testing
# ===============================================
# Monitors memory usage during migration phases
# Alerts if memory exceeds thresholds
# ===============================================

set -euo pipefail

# Configuration
CONTAINER_NAME="${1:-ccp_postgres_minimal}"
INTERVAL="${2:-5}"  # Monitoring interval in seconds
MEMORY_WARNING_GB="3"
MEMORY_CRITICAL_GB="4"
LOG_FILE="memory-test-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_memory_usage() {
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}" "$CONTAINER_NAME" 2>/dev/null || echo "Container not running"
}

get_memory_mb() {
    docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME" 2>/dev/null | awk -F'/' '{print $1}' | sed 's/[^0-9.]//g' || echo "0"
}

convert_to_gb() {
    local mb=$1
    echo "scale=2; $mb / 1024" | bc
}

# Start monitoring
log "Starting memory monitoring for container: $CONTAINER_NAME"
log "Interval: ${INTERVAL}s | Warning: ${MEMORY_WARNING_GB}GB | Critical: ${MEMORY_CRITICAL_GB}GB"
log "============================================="

# Initial baseline
log "Waiting for container to start..."
sleep 5

# Monitor loop
while true; do
    # Get current stats
    STATS=$(get_memory_usage)
    MEMORY_MB=$(get_memory_mb)
    
    if [ "$MEMORY_MB" == "0" ]; then
        log "Container not running or not found"
        sleep "$INTERVAL"
        continue
    fi
    
    MEMORY_GB=$(convert_to_gb "$MEMORY_MB")
    
    # Log current usage
    echo -e "\n${STATS}"
    log "Memory usage: ${MEMORY_GB}GB"
    
    # Check thresholds
    if (( $(echo "$MEMORY_GB > $MEMORY_CRITICAL_GB" | bc -l) )); then
        echo -e "${RED}CRITICAL: Memory usage (${MEMORY_GB}GB) exceeds ${MEMORY_CRITICAL_GB}GB limit!${NC}"
        log "CRITICAL: Memory threshold exceeded!"
        
        # Get detailed container info
        echo -e "\nDetailed container inspection:"
        docker inspect "$CONTAINER_NAME" | jq '.[] | {State: .State, HostConfig: {Memory: .HostConfig.Memory, MemorySwap: .HostConfig.MemorySwap}}'
        
        # Get PostgreSQL specific info if possible
        echo -e "\nPostgreSQL memory settings:"
        docker exec "$CONTAINER_NAME" psql -U test_user -d test_db -c "SHOW shared_buffers;" 2>/dev/null || true
        docker exec "$CONTAINER_NAME" psql -U test_user -d test_db -c "SHOW effective_cache_size;" 2>/dev/null || true
        docker exec "$CONTAINER_NAME" psql -U test_user -d test_db -c "SHOW work_mem;" 2>/dev/null || true
        
        exit 1
    elif (( $(echo "$MEMORY_GB > $MEMORY_WARNING_GB" | bc -l) )); then
        echo -e "${YELLOW}WARNING: Memory usage (${MEMORY_GB}GB) approaching limit${NC}"
        log "WARNING: Memory usage high"
    else
        echo -e "${GREEN}OK: Memory usage within limits${NC}"
    fi
    
    sleep "$INTERVAL"
done