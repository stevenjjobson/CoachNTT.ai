#!/bin/bash

# ===============================================
# Safety Enforcement Testing Script
# ===============================================
# Comprehensive testing of safety validation system
# Verifies that concrete references are properly rejected
# ===============================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ===============================================
# Configuration and Constants
# ===============================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TEST_LOG="/tmp/safety_test_$(date +%s).log"
readonly RESULTS_FILE="/tmp/safety_test_results_$(date +%s).json"

# Database configuration
readonly DB_NAME="${POSTGRES_DB:-cognitive_coding_partner}"
readonly DB_USER="${POSTGRES_USER:-ccp_user}"
readonly DB_HOST="${POSTGRES_HOST:-localhost}"
readonly DB_PORT="${POSTGRES_PORT:-5432}"

# Test configuration
readonly TOTAL_TESTS=25
readonly EXPECTED_FAILURES=15  # Tests that should fail (safety rejections)
readonly EXPECTED_SUCCESSES=10  # Tests that should succeed (valid abstractions)

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
SAFETY_REJECTIONS=0
UNEXPECTED_FAILURES=0

# ===============================================
# Logging Functions
# ===============================================
log_info() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $message" | tee -a "$TEST_LOG"
}

log_error() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $message" | tee -a "$TEST_LOG" >&2
}

log_test() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [TEST] $message" | tee -a "$TEST_LOG"
}

log_success() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [PASS] $message" | tee -a "$TEST_LOG"
}

log_failure() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [FAIL] $message" | tee -a "$TEST_LOG"
}

# ===============================================
# Test Helper Functions
# ===============================================
run_test() {
    local test_name="$1"
    local sql_command="$2"
    local should_succeed="$3"  # true if test should succeed, false if should fail
    
    ((TESTS_RUN++))
    log_test "Running test $TESTS_RUN/$TOTAL_TESTS: $test_name"
    
    local result=0
    local output
    output=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql_command" 2>&1) || result=$?
    
    if [[ $result -eq 0 ]]; then
        # SQL command succeeded
        if [[ "$should_succeed" == "true" ]]; then
            log_success "✓ $test_name - Valid data accepted as expected"
            ((TESTS_PASSED++))
        else
            log_failure "✗ $test_name - SECURITY ISSUE: Invalid data was accepted!"
            log_failure "  SQL: $sql_command"
            log_failure "  Output: $output"
            ((UNEXPECTED_FAILURES++))
        fi
    else
        # SQL command failed
        if [[ "$should_succeed" == "false" ]]; then
            log_success "✓ $test_name - Invalid data rejected as expected"
            log_success "  Rejection reason: $(echo "$output" | grep -o 'ERROR:.*' | head -1)"
            ((TESTS_PASSED++))
            ((SAFETY_REJECTIONS++))
        else
            log_failure "✗ $test_name - Valid data was unexpectedly rejected"
            log_failure "  SQL: $sql_command"
            log_failure "  Error: $output"
            ((TESTS_FAILED++))
        fi
    fi
    
    # Clean up any test data that might have been inserted
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        DELETE FROM safety.memory_abstractions WHERE abstracted_content::text LIKE '%TEST_%';
        DELETE FROM public.cognitive_memory WHERE metadata::text LIKE '%TEST_%';
    " >/dev/null 2>&1 || true
}

# ===============================================
# Database Connection Test
# ===============================================
test_database_connection() {
    log_info "Testing database connection..."
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        log_error "Database connection failed"
        exit 1
    fi
    
    # Test basic query
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        log_error "Database query test failed"
        exit 1
    fi
    
    log_info "Database connection test passed"
}

# ===============================================
# Safety Infrastructure Tests
# ===============================================
test_safety_schema_exists() {
    log_info "Verifying safety schema infrastructure..."
    
    # Check safety schema exists
    local schema_exists
    schema_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name='safety');" | xargs)
    
    if [[ "$schema_exists" != "t" ]]; then
        log_error "Safety schema does not exist"
        exit 1
    fi
    
    # Check required tables exist
    local required_tables=("memory_abstractions" "abstraction_patterns" "reference_validation_rules" "abstraction_quality_metrics")
    for table in "${required_tables[@]}"; do
        local table_exists
        table_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='safety' AND table_name='$table');" | xargs)
        
        if [[ "$table_exists" != "t" ]]; then
            log_error "Required safety table missing: safety.$table"
            exit 1
        fi
    done
    
    # Check triggers exist
    local trigger_exists
    trigger_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS(SELECT 1 FROM information_schema.triggers WHERE trigger_name='trigger_validate_memory_abstraction');" | xargs)
    
    if [[ "$trigger_exists" != "t" ]]; then
        log_error "Critical safety trigger missing: trigger_validate_memory_abstraction"
        exit 1
    fi
    
    log_info "Safety schema infrastructure verified"
}

# ===============================================
# Concrete Reference Rejection Tests
# ===============================================
test_concrete_file_path_rejection() {
    # Test 1: Absolute Unix path
    run_test "Reject Unix absolute path" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"file at /home/user/document.txt\"}', '{}', 0.9);" \
        false
    
    # Test 2: Windows path
    run_test "Reject Windows file path" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"file at C:\\\\Users\\\\Test\\\\file.txt\"}', '{}', 0.9);" \
        false
    
    # Test 3: Mac user path
    run_test "Reject Mac user path" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"/Users/testuser/Documents/test.pdf\"}', '{}', 0.9);" \
        false
}

test_concrete_network_rejection() {
    # Test 4: IP address
    run_test "Reject IP address" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"server at 192.168.1.100\"}', '{}', 0.9);" \
        false
    
    # Test 5: Localhost with port
    run_test "Reject localhost with port" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"localhost:5432\"}', '{}', 0.9);" \
        false
    
    # Test 6: Concrete URL
    run_test "Reject concrete URL" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"https://api.example.com/endpoint\"}', '{}', 0.9);" \
        false
}

test_credential_rejection() {
    # Test 7: Password value
    run_test "Reject password value" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"password=\\\"secret123\\\"\"}', '{}', 0.9);" \
        false
    
    # Test 8: API key
    run_test "Reject API key" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"api_key: sk-1234567890abcdef\"}', '{}', 0.9);" \
        false
    
    # Test 9: Secret token
    run_test "Reject secret token" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"token=\\\"ghp_abcdefghijk\\\"\"}', '{}', 0.9);" \
        false
}

test_low_safety_score_rejection() {
    # Test 10: Low safety score
    run_test "Reject low safety score (0.5)" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"test with <placeholder>\"}', '{\"test\": \"<placeholder>\"}', 0.5);" \
        false
    
    # Test 11: Zero safety score
    run_test "Reject zero safety score" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"test content\"}', '{}', 0.0);" \
        false
    
    # Test 12: Below minimum threshold
    run_test "Reject below minimum threshold (0.7)" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"<placeholder> content\"}', '{\"test\": \"<placeholder>\"}', 0.7);" \
        false
}

test_database_connection_rejection() {
    # Test 13: PostgreSQL connection string
    run_test "Reject PostgreSQL connection string" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"postgresql://user:pass@localhost:5432/db\"}', '{}', 0.9);" \
        false
    
    # Test 14: MongoDB connection string
    run_test "Reject MongoDB connection string" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"mongodb://user:pass@server:27017/database\"}', '{}', 0.9);" \
        false
    
    # Test 15: Email address
    run_test "Reject email address" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"contact user@example.com for help\"}', '{}', 0.9);" \
        false
}

# ===============================================
# Valid Abstraction Acceptance Tests
# ===============================================
test_valid_abstraction_acceptance() {
    # Test 16: Valid abstraction with placeholders
    run_test "Accept valid abstraction with placeholders" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"file at <file_path>\"}', '{\"file_path\": \"/actual/path\"}', 0.9);" \
        true
    
    # Test 17: Multiple placeholders
    run_test "Accept multiple placeholders" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"connect to <server_host>:<server_port>\"}', '{\"server_host\": \"host\", \"server_port\": \"port\"}', 0.95);" \
        true
    
    # Test 18: High safety score
    run_test "Accept high safety score (0.99)" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"<action> performed on <resource>\"}', '{\"action\": \"action\", \"resource\": \"resource\"}', 0.99);" \
        true
    
    # Test 19: Abstract credentials
    run_test "Accept abstracted credentials" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"login with <username> and <password>\"}', '{\"username\": \"user\", \"password\": \"pass\"}', 0.92);" \
        true
    
    # Test 20: Abstract API reference
    run_test "Accept abstracted API reference" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"call <api_endpoint> with <api_key>\"}', '{\"api_endpoint\": \"endpoint\", \"api_key\": \"key\"}', 0.88);" \
        true
}

test_cognitive_memory_validation() {
    # First, create a valid abstraction for reference
    local abstraction_id
    abstraction_id=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score, validation_status) 
        VALUES (gen_random_uuid(), '{\"content\": \"test with <placeholder>\"}', '{\"test\": \"<placeholder>\"}', 0.9, 'validated') 
        RETURNING memory_id;" | xargs)
    
    # Test 21: Valid cognitive memory with valid abstraction
    run_test "Accept cognitive memory with valid abstraction" \
        "INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id, weight) VALUES (gen_random_uuid(), gen_random_uuid(), 'test', '$abstraction_id', 1.0);" \
        true
    
    # Test 22: Reject cognitive memory with non-existent abstraction
    run_test "Reject cognitive memory with invalid abstraction ID" \
        "INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id, weight) VALUES (gen_random_uuid(), gen_random_uuid(), 'test', gen_random_uuid(), 1.0);" \
        false
    
    # Test 23: Reject cognitive memory metadata with concrete references
    run_test "Reject cognitive memory with concrete metadata" \
        "INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id, metadata, weight) VALUES (gen_random_uuid(), gen_random_uuid(), 'test', '$abstraction_id', '{\"path\": \"/home/user/file.txt\"}', 1.0);" \
        false
}

test_edge_cases() {
    # Test 24: Empty content (should fail)
    run_test "Reject empty content" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{}', '{}', 0.9);" \
        false
    
    # Test 25: Valid minimal abstraction
    run_test "Accept minimal valid abstraction" \
        "INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) VALUES (gen_random_uuid(), '{\"content\": \"action on <resource>\"}', '{\"resource\": \"item\"}', 0.85);" \
        true
}

# ===============================================
# Test Result Analysis
# ===============================================
analyze_results() {
    log_info "Analyzing test results..."
    
    local safety_effectiveness=0
    if [[ $SAFETY_REJECTIONS -gt 0 ]]; then
        safety_effectiveness=$((SAFETY_REJECTIONS * 100 / EXPECTED_FAILURES))
    fi
    
    local overall_success_rate=0
    if [[ $TESTS_RUN -gt 0 ]]; then
        overall_success_rate=$((TESTS_PASSED * 100 / TESTS_RUN))
    fi
    
    # Generate JSON results
    cat > "$RESULTS_FILE" << EOF
{
    "test_summary": {
        "total_tests": $TESTS_RUN,
        "tests_passed": $TESTS_PASSED,
        "tests_failed": $TESTS_FAILED,
        "safety_rejections": $SAFETY_REJECTIONS,
        "unexpected_failures": $UNEXPECTED_FAILURES,
        "overall_success_rate": $overall_success_rate,
        "safety_effectiveness": $safety_effectiveness
    },
    "expected_vs_actual": {
        "expected_total": $TOTAL_TESTS,
        "expected_failures": $EXPECTED_FAILURES,
        "expected_successes": $EXPECTED_SUCCESSES,
        "actual_total": $TESTS_RUN,
        "actual_safety_rejections": $SAFETY_REJECTIONS,
        "actual_successes": $((TESTS_PASSED - SAFETY_REJECTIONS))
    },
    "safety_assessment": {
        "concrete_reference_detection": "$(if [[ $SAFETY_REJECTIONS -ge 12 ]]; then echo "EXCELLENT"; elif [[ $SAFETY_REJECTIONS -ge 10 ]]; then echo "GOOD"; elif [[ $SAFETY_REJECTIONS -ge 8 ]]; then echo "ADEQUATE"; else echo "INADEQUATE"; fi)",
        "abstraction_validation": "$(if [[ $((TESTS_PASSED - SAFETY_REJECTIONS)) -ge 8 ]]; then echo "EXCELLENT"; elif [[ $((TESTS_PASSED - SAFETY_REJECTIONS)) -ge 6 ]]; then echo "GOOD"; else echo "NEEDS_IMPROVEMENT"; fi)",
        "overall_security_posture": "$(if [[ $UNEXPECTED_FAILURES -eq 0 && $SAFETY_REJECTIONS -ge 12 ]]; then echo "SECURE"; elif [[ $UNEXPECTED_FAILURES -le 1 && $SAFETY_REJECTIONS -ge 10 ]]; then echo "MOSTLY_SECURE"; else echo "REQUIRES_ATTENTION"; fi)"
    },
    "timestamp": "$(date -Iseconds)",
    "test_environment": {
        "database": "$DB_NAME",
        "host": "$DB_HOST",
        "port": $DB_PORT,
        "user": "$DB_USER"
    }
}
EOF
    
    log_info "Test results saved to: $RESULTS_FILE"
}

# ===============================================
# Test Report Generation
# ===============================================
generate_report() {
    echo
    echo "==============================================="
    echo "SAFETY ENFORCEMENT TEST RESULTS"
    echo "==============================================="
    echo "Total Tests Run: $TESTS_RUN/$TOTAL_TESTS"
    echo "Tests Passed: $TESTS_PASSED"
    echo "Tests Failed: $TESTS_FAILED"
    echo
    echo "Safety Performance:"
    echo "  Safety Rejections: $SAFETY_REJECTIONS/$EXPECTED_FAILURES expected"
    echo "  Valid Acceptances: $((TESTS_PASSED - SAFETY_REJECTIONS))/$EXPECTED_SUCCESSES expected"
    echo "  Unexpected Failures: $UNEXPECTED_FAILURES"
    echo
    echo "Success Rate: $((TESTS_PASSED * 100 / TESTS_RUN))%"
    echo "Safety Effectiveness: $((SAFETY_REJECTIONS * 100 / EXPECTED_FAILURES))%"
    echo
    
    if [[ $UNEXPECTED_FAILURES -eq 0 && $SAFETY_REJECTIONS -ge 12 ]]; then
        echo "🔒 SECURITY STATUS: SECURE"
        echo "   ✓ All concrete references properly rejected"
        echo "   ✓ Valid abstractions properly accepted"
        echo "   ✓ No security vulnerabilities detected"
    elif [[ $UNEXPECTED_FAILURES -le 1 && $SAFETY_REJECTIONS -ge 10 ]]; then
        echo "⚠️  SECURITY STATUS: MOSTLY SECURE"
        echo "   ✓ Most concrete references rejected"
        echo "   ⚠️  Minor issues detected"
    else
        echo "🚨 SECURITY STATUS: REQUIRES ATTENTION"
        echo "   ❌ Security vulnerabilities detected"
        echo "   ❌ Safety enforcement insufficient"
    fi
    
    echo
    echo "Detailed Results: $RESULTS_FILE"
    echo "Test Log: $TEST_LOG"
    echo "==============================================="
}

# ===============================================
# Main Test Execution
# ===============================================
main() {
    echo "==============================================="
    echo "CoachNTT.ai Safety Enforcement Testing"
    echo "==============================================="
    echo "Testing safety validation and concrete reference rejection"
    echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    echo "Expected tests: $TOTAL_TESTS (${EXPECTED_FAILURES} rejections, ${EXPECTED_SUCCESSES} acceptances)"
    echo
    
    log_info "Starting safety enforcement tests..."
    
    # Step 1: Test database connection
    test_database_connection
    
    # Step 2: Verify safety infrastructure
    test_safety_schema_exists
    
    echo "Running safety enforcement tests..."
    echo
    
    # Step 3: Run concrete reference rejection tests
    log_info "Testing concrete reference rejection..."
    test_concrete_file_path_rejection
    test_concrete_network_rejection
    test_credential_rejection
    test_low_safety_score_rejection
    test_database_connection_rejection
    
    # Step 4: Run valid abstraction acceptance tests
    log_info "Testing valid abstraction acceptance..."
    test_valid_abstraction_acceptance
    test_cognitive_memory_validation
    test_edge_cases
    
    # Step 5: Analyze results
    analyze_results
    
    # Step 6: Generate report
    generate_report
    
    # Step 7: Exit with appropriate code
    if [[ $UNEXPECTED_FAILURES -eq 0 && $SAFETY_REJECTIONS -ge 12 ]]; then
        log_info "All safety tests passed successfully"
        exit 0
    else
        log_error "Safety tests revealed security issues"
        exit 1
    fi
}

# ===============================================
# Script Execution
# ===============================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi