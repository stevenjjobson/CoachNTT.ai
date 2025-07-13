-- ===============================================
-- Comprehensive Abstraction Enforcement Test Suite
-- ===============================================
-- Tests all aspects of safety-first database schema
-- Validates rejection of concrete references
-- ===============================================

\set ON_ERROR_STOP on
\timing on

-- Test configuration
\set EXPECTED_FAILURES 50
\set EXPECTED_SUCCESSES 25

-- Start transaction for test isolation
BEGIN;

-- ===============================================
-- Test Setup
-- ===============================================

-- Create test results table
CREATE TEMP TABLE test_results (
    test_id SERIAL PRIMARY KEY,
    test_category VARCHAR(50),
    test_name VARCHAR(200),
    test_type VARCHAR(20) CHECK (test_type IN ('positive', 'negative')),
    expected_result VARCHAR(20) CHECK (expected_result IN ('pass', 'fail')),
    actual_result VARCHAR(20) CHECK (actual_result IN ('pass', 'fail')),
    error_message TEXT,
    execution_time_ms INTEGER,
    test_timestamp TIMESTAMP DEFAULT NOW()
);

-- Helper function to run tests
CREATE OR REPLACE FUNCTION run_test(
    p_category VARCHAR(50),
    p_name VARCHAR(200),
    p_sql TEXT,
    p_should_fail BOOLEAN DEFAULT true
) RETURNS VOID AS $$
DECLARE
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_error_msg TEXT;
    v_success BOOLEAN := false;
BEGIN
    v_start_time := clock_timestamp();
    
    BEGIN
        EXECUTE p_sql;
        v_success := true;
    EXCEPTION WHEN OTHERS THEN
        v_error_msg := SQLERRM;
        v_success := false;
    END;
    
    v_end_time := clock_timestamp();
    
    INSERT INTO test_results (
        test_category,
        test_name,
        test_type,
        expected_result,
        actual_result,
        error_message,
        execution_time_ms
    ) VALUES (
        p_category,
        p_name,
        CASE WHEN p_should_fail THEN 'negative' ELSE 'positive' END,
        CASE WHEN p_should_fail THEN 'fail' ELSE 'pass' END,
        CASE 
            WHEN p_should_fail AND NOT v_success THEN 'fail'
            WHEN NOT p_should_fail AND v_success THEN 'pass'
            ELSE CASE WHEN v_success THEN 'pass' ELSE 'fail' END
        END,
        v_error_msg,
        EXTRACT(MILLISECONDS FROM (v_end_time - v_start_time))::INTEGER
    );
END;
$$ LANGUAGE plpgsql;

-- ===============================================
-- Category 1: File Path Rejection Tests
-- ===============================================

SELECT 'Testing file path rejections...' as test_category;

-- Test 1: Unix home directory path
PERFORM run_test(
    'file_paths',
    'Reject Unix home directory path',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "/home/username/documents/file.txt"}', '{}', 0.9)$$,
    true
);

-- Test 2: Unix system paths
PERFORM run_test(
    'file_paths',
    'Reject Unix system paths (/etc)',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "/etc/passwd"}', '{}', 0.9)$$,
    true
);

-- Test 3: Windows user directory
PERFORM run_test(
    'file_paths',
    'Reject Windows user directory',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "C:\\Users\\Alice\\Desktop\\project"}', '{}', 0.9)$$,
    true
);

-- Test 4: Windows system paths
PERFORM run_test(
    'file_paths',
    'Reject Windows system paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "C:\\Windows\\System32\\config"}', '{}', 0.9)$$,
    true
);

-- Test 5: Mac user paths
PERFORM run_test(
    'file_paths',
    'Reject Mac user paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "/Users/john/Library/Application Support/"}', '{}', 0.9)$$,
    true
);

-- Test 6: Relative paths with parent directory traversal
PERFORM run_test(
    'file_paths',
    'Reject relative paths with traversal',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "../../etc/shadow"}', '{}', 0.9)$$,
    true
);

-- Test 7: Hidden file paths
PERFORM run_test(
    'file_paths',
    'Reject hidden file paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "/home/user/.ssh/id_rsa"}', '{}', 0.9)$$,
    true
);

-- Test 8: Network share paths
PERFORM run_test(
    'file_paths',
    'Reject network share paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "\\\\server\\share\\file.doc"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 2: Network Address Rejection Tests
-- ===============================================

SELECT 'Testing network address rejections...' as test_category;

-- Test 9: IPv4 addresses
PERFORM run_test(
    'network',
    'Reject IPv4 addresses',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Connect to server at 192.168.1.100"}', '{}', 0.9)$$,
    true
);

-- Test 10: IPv6 addresses
PERFORM run_test(
    'network',
    'Reject IPv6 addresses',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Server: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"}', '{}', 0.9)$$,
    true
);

-- Test 11: Localhost references
PERFORM run_test(
    'network',
    'Reject localhost references',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "API endpoint: localhost:8080/api/v1"}', '{}', 0.9)$$,
    true
);

-- Test 12: Domain names with ports
PERFORM run_test(
    'network',
    'Reject domain names with ports',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "api.example.com:443"}', '{}', 0.9)$$,
    true
);

-- Test 13: Internal network addresses
PERFORM run_test(
    'network',
    'Reject internal network addresses',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "10.0.0.1"}', '{}', 0.9)$$,
    true
);

-- Test 14: URLs with specific endpoints
PERFORM run_test(
    'network',
    'Reject URLs with specific endpoints',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "https://api.stripe.com/v1/charges"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 3: Credential Rejection Tests
-- ===============================================

SELECT 'Testing credential rejections...' as test_category;

-- Test 15: Hardcoded passwords
PERFORM run_test(
    'credentials',
    'Reject hardcoded passwords',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "password=\"secretPass123!\""}', '{}', 0.9)$$,
    true
);

-- Test 16: API keys
PERFORM run_test(
    'credentials',
    'Reject API keys',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "api_key: sk_test_4eC39HqLyjWDarjtT1zdp7dc"}', '{}', 0.9)$$,
    true
);

-- Test 17: JWT tokens
PERFORM run_test(
    'credentials',
    'Reject JWT tokens',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"}', '{}', 0.9)$$,
    true
);

-- Test 18: Database connection strings
PERFORM run_test(
    'credentials',
    'Reject database connection strings',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "postgresql://admin:password123@localhost:5432/mydb"}', '{}', 0.9)$$,
    true
);

-- Test 19: AWS access keys
PERFORM run_test(
    'credentials',
    'Reject AWS access keys',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"}', '{}', 0.9)$$,
    true
);

-- Test 20: SSH keys
PERFORM run_test(
    'credentials',
    'Reject SSH private key content',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA..."}', '{}', 0.9)$$,
    true
);

-- Test 21: OAuth tokens
PERFORM run_test(
    'credentials',
    'Reject OAuth tokens',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "oauth_token=1/fFAGRNJru1FTz70BzhT3Zg"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 4: Personal Data Rejection Tests
-- ===============================================

SELECT 'Testing personal data rejections...' as test_category;

-- Test 22: Email addresses
PERFORM run_test(
    'personal_data',
    'Reject email addresses',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Contact: john.doe@example.com"}', '{}', 0.9)$$,
    true
);

-- Test 23: Phone numbers
PERFORM run_test(
    'personal_data',
    'Reject phone numbers',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Call me at +1-555-123-4567"}', '{}', 0.9)$$,
    true
);

-- Test 24: Social Security Numbers
PERFORM run_test(
    'personal_data',
    'Reject SSN patterns',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "SSN: 123-45-6789"}', '{}', 0.9)$$,
    true
);

-- Test 25: Credit card numbers
PERFORM run_test(
    'personal_data',
    'Reject credit card patterns',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Card: 4532-1234-5678-9012"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 5: Low Safety Score Rejection Tests
-- ===============================================

SELECT 'Testing low safety score rejections...' as test_category;

-- Test 26: Score below minimum (0.5)
PERFORM run_test(
    'safety_scores',
    'Reject safety score 0.5',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "test <placeholder>"}', '{}', 0.5)$$,
    true
);

-- Test 27: Score at threshold boundary (0.79)
PERFORM run_test(
    'safety_scores',
    'Reject safety score 0.79',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "test <placeholder>"}', '{}', 0.79)$$,
    true
);

-- Test 28: Zero safety score
PERFORM run_test(
    'safety_scores',
    'Reject zero safety score',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "test"}', '{}', 0.0)$$,
    true
);

-- ===============================================
-- Category 6: Complex Pattern Rejection Tests
-- ===============================================

SELECT 'Testing complex pattern rejections...' as test_category;

-- Test 29: Mixed concrete references
PERFORM run_test(
    'complex',
    'Reject mixed concrete references',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Server at 192.168.1.1 with password=admin123"}', '{}', 0.9)$$,
    true
);

-- Test 30: Embedded paths in JSON
PERFORM run_test(
    'complex',
    'Reject embedded paths in JSON',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"config": {"path": "/home/user/config.json"}}', '{}', 0.9)$$,
    true
);

-- Test 31: Base64 encoded credentials
PERFORM run_test(
    'complex',
    'Reject base64 encoded credentials',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "auth: YWRtaW46cGFzc3dvcmQxMjM="}', '{}', 0.9)$$,
    true
);

-- Test 32: Container IDs
PERFORM run_test(
    'complex',
    'Reject container IDs',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "container_id: webapp_a1b2c3d4e5f6"}', '{}', 0.9)$$,
    true
);

-- Test 33: Git repository URLs
PERFORM run_test(
    'complex',
    'Reject Git repository URLs',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "git@github.com:username/repository.git"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 7: JSON Validation Tests
-- ===============================================

SELECT 'Testing JSON content validation...' as test_category;

-- Test 34: Nested JSON with paths
PERFORM run_test(
    'json',
    'Reject nested JSON with file paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"data": {"config": {"file": "/etc/app/config.yml"}}}', '{}', 0.9)$$,
    true
);

-- Test 35: JSON array with IPs
PERFORM run_test(
    'json',
    'Reject JSON array with IP addresses',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"servers": ["192.168.1.1", "192.168.1.2"]}', '{}', 0.9)$$,
    true
);

-- Test 36: JSON with sensitive keys
PERFORM run_test(
    'json',
    'Reject JSON with password field',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"username": "admin", "password": "secret123"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 8: Code Content Validation Tests
-- ===============================================

SELECT 'Testing code content validation...' as test_category;

-- Test 37: Hardcoded file paths in code
PERFORM run_test(
    'code',
    'Reject hardcoded paths in code',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"code": "const CONFIG_PATH = \"/home/app/config.json\";"}', '{}', 0.9)$$,
    true
);

-- Test 38: Hardcoded credentials in code
PERFORM run_test(
    'code',
    'Reject hardcoded credentials in code',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"code": "db.connect(\"admin\", \"password123\");"}', '{}', 0.9)$$,
    true
);

-- Test 39: Import statements with paths
PERFORM run_test(
    'code',
    'Reject import statements with concrete paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"code": "import config from \"/Users/dev/project/config\";"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 9: Edge Case Tests
-- ===============================================

SELECT 'Testing edge cases...' as test_category;

-- Test 40: Empty content
PERFORM run_test(
    'edge_cases',
    'Reject empty content',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{}', '{}', 0.9)$$,
    true
);

-- Test 41: Null values
PERFORM run_test(
    'edge_cases',
    'Reject null abstracted_prompt',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, abstracted_prompt, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "test"}', NULL, '{}', 0.9)$$,
    true
);

-- Test 42: Very long content with concrete refs
PERFORM run_test(
    'edge_cases',
    'Reject long content with embedded path',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "' || repeat('safe text ', 1000) || '/home/user/file.txt' || repeat(' more text', 100) || '"}', '{}', 0.9)$$,
    true
);

-- Test 43: Unicode paths
PERFORM run_test(
    'edge_cases',
    'Reject unicode paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "/home/用户/文档/file.txt"}', '{}', 0.9)$$,
    true
);

-- Test 44: Encoded slashes
PERFORM run_test(
    'edge_cases',
    'Reject encoded slashes in paths',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "%2Fhome%2Fuser%2Ffile.txt"}', '{}', 0.9)$$,
    true
);

-- Test 45: Case variations
PERFORM run_test(
    'edge_cases',
    'Reject case variations of sensitive data',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "PASSWORD=Secret123"}', '{}', 0.9)$$,
    true
);

-- ===============================================
-- Category 10: Metadata and Relationship Tests
-- ===============================================

SELECT 'Testing metadata and relationships...' as test_category;

-- Test 46: Cognitive memory with concrete metadata
PERFORM run_test(
    'metadata',
    'Reject cognitive memory with path in metadata',
    $$INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id, metadata) 
      VALUES (gen_random_uuid(), gen_random_uuid(), 'code_generation', 
              (SELECT memory_id FROM safety.memory_abstractions WHERE validation_status = 'validated' LIMIT 1),
              '{"source": "/home/user/project.py"}')$$,
    true
);

-- Test 47: Invalid abstraction reference
PERFORM run_test(
    'relationships',
    'Reject cognitive memory with non-existent abstraction',
    $$INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id) 
      VALUES (gen_random_uuid(), gen_random_uuid(), 'conversation', gen_random_uuid())$$,
    true
);

-- Test 48: Low-scored abstraction reference
PERFORM run_test(
    'relationships',
    'Reject reference to quarantined abstraction',
    $$WITH quarantined AS (
        INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score, validation_status) 
        VALUES (gen_random_uuid(), '{"content": "<placeholder>"}', '{}', 0.7, 'quarantined')
        RETURNING memory_id
      )
      INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id) 
      VALUES (gen_random_uuid(), gen_random_uuid(), 'conversation', (SELECT memory_id FROM quarantined))$$,
    true
);

-- Test 49: Circular reference attempt
PERFORM run_test(
    'relationships',
    'Reject circular memory relationship',
    $$WITH mem AS (
        INSERT INTO public.cognitive_memory (id, session_id, interaction_type, abstraction_id)
        VALUES (gen_random_uuid(), gen_random_uuid(), 'conversation',
                (SELECT memory_id FROM safety.memory_abstractions WHERE validation_status = 'validated' LIMIT 1))
        RETURNING id
      )
      INSERT INTO public.memory_relationships (source_memory_id, target_memory_id, relationship_type)
      SELECT id, id, 'continuation' FROM mem$$,
    true
);

-- Test 50: Cascade validation trigger
PERFORM run_test(
    'triggers',
    'Test cascade validation on abstraction update',
    $$UPDATE safety.memory_abstractions 
      SET safety_score = 0.5 
      WHERE memory_id = (SELECT abstraction_id FROM public.cognitive_memory LIMIT 1)$$,
    true
);

-- ===============================================
-- POSITIVE TESTS: Valid Abstractions
-- ===============================================

SELECT 'Testing valid abstraction acceptance...' as test_category;

-- Test 51: Simple placeholder abstraction
PERFORM run_test(
    'valid',
    'Accept simple placeholder abstraction',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "File located at <file_path>"}', '{"file_path": "/actual/path"}', 0.9)$$,
    false
);

-- Test 52: Multiple placeholders
PERFORM run_test(
    'valid',
    'Accept multiple placeholders',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Connect to <server_host>:<server_port> with <credentials>"}', 
              '{"server_host": "example.com", "server_port": "5432", "credentials": "auth_token"}', 0.95)$$,
    false
);

-- Test 53: Code with abstractions
PERFORM run_test(
    'valid',
    'Accept code with proper abstractions',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"code": "const API_URL = \"<api_endpoint>\"; const KEY = \"<api_key>\";"}', 
              '{"api_endpoint": "https://api.example.com", "api_key": "secret123"}', 0.92)$$,
    false
);

-- Test 54: URL pattern abstraction
PERFORM run_test(
    'valid',
    'Accept URL pattern abstraction',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "API endpoint: <protocol>://<domain>/<path>"}', 
              '{"protocol": "https", "domain": "api.service.com", "path": "v1/users"}', 0.88)$$,
    false
);

-- Test 55: Configuration abstraction
PERFORM run_test(
    'valid',
    'Accept configuration abstraction',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"config": {"database": "<db_connection>", "cache": "<cache_server>"}}', 
              '{"db_connection": "postgres://localhost", "cache_server": "redis://localhost"}', 0.91)$$,
    false
);

-- Test 56: High safety score
PERFORM run_test(
    'valid',
    'Accept high safety score (0.99)',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Abstract content with <placeholder1> and <placeholder2>"}', 
              '{"placeholder1": "value1", "placeholder2": "value2"}', 0.99)$$,
    false
);

-- Test 57: Exact threshold score
PERFORM run_test(
    'valid',
    'Accept exact threshold score (0.80)',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Content with <abstraction>"}', '{"abstraction": "concrete"}', 0.80)$$,
    false
);

-- Test 58: Complex nested abstraction
PERFORM run_test(
    'valid',
    'Accept complex nested abstraction',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), 
              '{"data": {"config": {"paths": ["<path1>", "<path2>"], "servers": {"main": "<server>", "backup": "<backup_server>"}}}', 
              '{"path1": "/var/log", "path2": "/tmp", "server": "main.example.com", "backup_server": "backup.example.com"}', 
              0.93)$$,
    false
);

-- Test 59: Abstracted personal data
PERFORM run_test(
    'valid',
    'Accept abstracted personal data',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "User <user_email> called from <phone_number>"}', 
              '{"user_email": "user@example.com", "phone_number": "+1-555-0123"}', 0.87)$$,
    false
);

-- Test 60: Empty placeholders (edge case)
PERFORM run_test(
    'valid',
    'Accept content with empty concrete refs but placeholders',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score) 
      VALUES (gen_random_uuid(), '{"content": "Template with <placeholder>"}', '{}', 0.85)$$,
    false
);

-- ===============================================
-- Category 11: Trigger and Function Tests
-- ===============================================

SELECT 'Testing triggers and functions...' as test_category;

-- Test 61: Real-time safety score calculation
PERFORM run_test(
    'functions',
    'Test composite safety score function',
    $$SELECT safety.calculate_composite_safety_score(
        'Password is secretPass123!',
        'credential'
      )$$,
    false
);

-- Test 62: JSON validation function
PERFORM run_test(
    'functions',
    'Test JSON content validation',
    $$SELECT safety.validate_json_content(
        '{"path": "/home/user/file.txt"}'::jsonb
      )$$,
    false
);

-- Test 63: Code validation function
PERFORM run_test(
    'functions',
    'Test code abstraction validation',
    $$SELECT safety.validate_code_abstractions(
        'const password = "admin123";'
      )$$,
    false
);

-- Test 64: URL validation function
PERFORM run_test(
    'functions',
    'Test URL abstraction validation',
    $$SELECT safety.validate_url_abstractions(
        'https://api.example.com/v1/users?api_key=secret123'
      )$$,
    false
);

-- Test 65: Placeholder density check
PERFORM run_test(
    'functions',
    'Test placeholder density function',
    $$SELECT safety.check_placeholder_density(
        'Text with <placeholder1> and <placeholder2>',
        0.1
      )$$,
    false
);

-- Test 66: Pattern consistency check
PERFORM run_test(
    'functions',
    'Test pattern consistency function',
    $$SELECT safety.check_pattern_consistency(
        'Mixed <placeholder> and {placeholder} styles'
      )$$,
    false
);

-- Test 67: Batch validation
PERFORM run_test(
    'functions',
    'Test batch validation function',
    $$SELECT safety.batch_validate_contents(
        '[{"content": "/home/user/file.txt", "type": "path"}, 
          {"content": "password=123", "type": "credential"}]'::jsonb
      )$$,
    false
);

-- Test 68: Abstraction quality assessment
PERFORM run_test(
    'functions',
    'Test quality assessment on valid abstraction',
    $$SELECT safety.assess_abstraction_quality(
        (SELECT memory_id FROM safety.memory_abstractions 
         WHERE validation_status = 'validated' 
         LIMIT 1)
      )$$,
    false
);

-- Test 69: Memory decay calculation
PERFORM run_test(
    'functions',
    'Test memory decay calculation',
    $$SELECT public.calculate_memory_decay(
        0.9::decimal(5,4),
        NOW() - INTERVAL '30 days',
        'conversation',
        10
      )$$,
    false
);

-- Test 70: Find related memories
PERFORM run_test(
    'functions',
    'Test find related memories function',
    $$SELECT * FROM public.find_related_memories(
        (SELECT id FROM public.cognitive_memory LIMIT 1),
        0.7,
        5
      )$$,
    false
);

-- ===============================================
-- Category 12: Performance Tests
-- ===============================================

SELECT 'Testing performance constraints...' as test_category;

-- Test 71: Large batch insert attempt
PERFORM run_test(
    'performance',
    'Reject large batch with concrete refs',
    $$INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score)
      SELECT 
        gen_random_uuid(),
        '{"content": "/home/user' || i || '/file.txt"}',
        '{}',
        0.9
      FROM generate_series(1, 100) i$$,
    true
);

-- Test 72: Complex nested JSON validation
PERFORM run_test(
    'performance',
    'Test deep JSON validation performance',
    $$SELECT safety.validate_json_content(
        ('{"level1": {"level2": {"level3": {"level4": {"level5": ' ||
         '{"level6": {"level7": {"level8": {"level9": {"level10": ' ||
         '{"path": "/home/user/file.txt"}' ||
         repeat('}', 10) || '}')::jsonb,
        10
      )$$,
    false
);

-- Test 73: High entropy detection
PERFORM run_test(
    'performance',
    'Test entropy calculation performance',
    $$SELECT safety.calculate_shannon_entropy(
        encode(gen_random_bytes(1000), 'base64')
      )$$,
    false
);

-- Test 74: Concurrent safety validation
PERFORM run_test(
    'performance',
    'Test concurrent insert validation',
    $$WITH concurrent_inserts AS (
        SELECT gen_random_uuid() as id, 
               '{"content": "Safe content with <placeholder' || i || '>"}' as content,
               ('{"placeholder' || i || '": "value' || i || '"}')::jsonb as refs
        FROM generate_series(1, 10) i
      )
      INSERT INTO safety.memory_abstractions (memory_id, abstracted_content, concrete_references, safety_score)
      SELECT id, content, refs, 0.85 FROM concurrent_inserts$$,
    false
);

-- Test 75: Materialized view refresh
PERFORM run_test(
    'performance',
    'Test materialized view refresh',
    $$REFRESH MATERIALIZED VIEW CONCURRENTLY public.validated_memories$$,
    false
);

-- ===============================================
-- Test Results Summary
-- ===============================================

-- Calculate test results
WITH test_summary AS (
    SELECT 
        test_type,
        expected_result,
        actual_result,
        COUNT(*) as count
    FROM test_results
    GROUP BY test_type, expected_result, actual_result
),
overall_results AS (
    SELECT 
        SUM(CASE WHEN expected_result = actual_result THEN count ELSE 0 END) as passed,
        SUM(CASE WHEN expected_result != actual_result THEN count ELSE 0 END) as failed,
        SUM(count) as total
    FROM test_summary
)
SELECT 
    '===============================================' as separator UNION ALL
SELECT 'ABSTRACTION ENFORCEMENT TEST RESULTS' UNION ALL
SELECT '===============================================' UNION ALL
SELECT 'Total Tests: ' || total FROM overall_results UNION ALL
SELECT 'Passed: ' || passed || ' (' || ROUND(passed::numeric / total * 100, 1) || '%)' FROM overall_results UNION ALL
SELECT 'Failed: ' || failed || ' (' || ROUND(failed::numeric / total * 100, 1) || '%)' FROM overall_results UNION ALL
SELECT '===============================================' UNION ALL
SELECT '' UNION ALL
SELECT 'Category Breakdown:' UNION ALL
SELECT '-------------------';

-- Category breakdown
SELECT 
    test_category || ': ' || 
    SUM(CASE WHEN expected_result = actual_result THEN 1 ELSE 0 END) || '/' || 
    COUNT(*) || ' passed'
FROM test_results
GROUP BY test_category
ORDER BY test_category;

-- Failed test details
SELECT '' UNION ALL
SELECT 'Failed Tests:' UNION ALL
SELECT '-------------';

SELECT 
    test_category || ' - ' || test_name || ': ' || 
    COALESCE(error_message, 'Unexpected success')
FROM test_results
WHERE expected_result != actual_result
ORDER BY test_id;

-- Performance metrics
SELECT '' UNION ALL
SELECT 'Performance Metrics:' UNION ALL
SELECT '-------------------';

SELECT 
    'Average execution time: ' || ROUND(AVG(execution_time_ms), 2) || 'ms' UNION ALL
SELECT 
    'Max execution time: ' || MAX(execution_time_ms) || 'ms' UNION ALL
SELECT 
    'Min execution time: ' || MIN(execution_time_ms) || 'ms'
FROM test_results;

-- Security posture assessment
SELECT '' UNION ALL
SELECT 'Security Posture Assessment:' UNION ALL
SELECT '----------------------------';

WITH security_metrics AS (
    SELECT 
        SUM(CASE WHEN test_type = 'negative' AND expected_result = actual_result THEN 1 ELSE 0 END) as rejections_working,
        SUM(CASE WHEN test_type = 'negative' THEN 1 ELSE 0 END) as total_rejection_tests,
        SUM(CASE WHEN test_type = 'positive' AND expected_result = actual_result THEN 1 ELSE 0 END) as acceptances_working,
        SUM(CASE WHEN test_type = 'positive' THEN 1 ELSE 0 END) as total_acceptance_tests
    FROM test_results
)
SELECT 
    CASE 
        WHEN rejections_working = total_rejection_tests AND acceptances_working = total_acceptance_tests THEN
            '🔒 SECURITY STATUS: EXCELLENT - All safety validations working correctly'
        WHEN rejections_working >= total_rejection_tests * 0.95 THEN
            '✅ SECURITY STATUS: GOOD - Most safety validations working'
        WHEN rejections_working >= total_rejection_tests * 0.8 THEN
            '⚠️  SECURITY STATUS: FAIR - Some safety gaps detected'
        ELSE
            '🚨 SECURITY STATUS: CRITICAL - Major safety failures detected'
    END
FROM security_metrics;

-- Cleanup
ROLLBACK;