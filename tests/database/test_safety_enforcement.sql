-- Test suite for safety enforcement mechanisms
-- Run these tests after applying 001_safety_enforcement.sql migration
-- Purpose: Validate that all safety constraints, triggers, and RLS policies work correctly

-- Set up test environment
SET search_path TO safety, public;

-- Create test helper function
CREATE OR REPLACE FUNCTION test_safety.run_test(
    p_test_name TEXT,
    p_test_sql TEXT,
    p_should_fail BOOLEAN DEFAULT FALSE
) RETURNS TABLE(test_name TEXT, passed BOOLEAN, details TEXT) AS $$
DECLARE
    v_error_message TEXT;
    v_error_code TEXT;
BEGIN
    BEGIN
        EXECUTE p_test_sql;
        
        IF p_should_fail THEN
            RETURN QUERY SELECT p_test_name, FALSE, 'Expected failure but succeeded';
        ELSE
            RETURN QUERY SELECT p_test_name, TRUE, 'Success';
        END IF;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS 
            v_error_message = MESSAGE_TEXT,
            v_error_code = RETURNED_SQLSTATE;
            
        IF p_should_fail THEN
            RETURN QUERY SELECT p_test_name, TRUE, format('Failed as expected: %s (%s)', v_error_message, v_error_code);
        ELSE
            RETURN QUERY SELECT p_test_name, FALSE, format('Unexpected error: %s (%s)', v_error_message, v_error_code);
        END IF;
    END;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TEST SUITE 1: VALIDATION TRIGGERS
-- =====================================================

DO $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_test_results RECORD;
BEGIN
    RAISE NOTICE '=== TEST SUITE 1: VALIDATION TRIGGERS ===';
    
    -- Test 1.1: Reject concrete reference without abstraction
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'reject_concrete_without_abstraction',
            format($SQL$
                INSERT INTO safety.memory_references (
                    memory_id, reference_type, concrete_value, abstracted_value
                ) VALUES (
                    '%s', 'file_path', '/home/user/secret.txt', NULL
                )
            $SQL$, v_test_memory_id),
            TRUE
        )
    LOOP
        RAISE NOTICE 'Test 1.1 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
        IF NOT v_test_results.passed THEN
            RAISE NOTICE '  Details: %', v_test_results.details;
        END IF;
    END LOOP;
    
    -- Test 1.2: Reject abstracted value containing concrete references
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'reject_concrete_in_abstraction',
            format($SQL$
                INSERT INTO safety.memory_references (
                    memory_id, reference_type, concrete_value, abstracted_value
                ) VALUES (
                    '%s', 'file_path', '/home/user/file.txt', '/home/user/abstracted.txt'
                )
            $SQL$, v_test_memory_id),
            TRUE
        )
    LOOP
        RAISE NOTICE 'Test 1.2 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
        IF NOT v_test_results.passed THEN
            RAISE NOTICE '  Details: %', v_test_results.details;
        END IF;
    END LOOP;
    
    -- Test 1.3: Accept properly abstracted reference
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'accept_proper_abstraction',
            format($SQL$
                INSERT INTO safety.memory_references (
                    memory_id, reference_type, concrete_value, abstracted_value
                ) VALUES (
                    '%s', 'file_path', '/home/user/file.txt', '<user_home>/file.txt'
                )
            $SQL$, v_test_memory_id),
            FALSE
        )
    LOOP
        RAISE NOTICE 'Test 1.3 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
        IF NOT v_test_results.passed THEN
            RAISE NOTICE '  Details: %', v_test_results.details;
        END IF;
    END LOOP;
    
    -- Clean up
    DELETE FROM safety.memory_references WHERE memory_id = v_test_memory_id;
END $$;

-- =====================================================
-- TEST SUITE 2: CHECK CONSTRAINTS
-- =====================================================

DO $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_test_results RECORD;
BEGIN
    RAISE NOTICE '=== TEST SUITE 2: CHECK CONSTRAINTS ===';
    
    -- Test 2.1: Reject abstraction metrics below threshold without violations
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'reject_low_abstraction_score',
            format($SQL$
                INSERT INTO safety.abstraction_metrics (
                    memory_id, abstraction_score, abstracted_ref_count
                ) VALUES (
                    '%s', 0.5, 5
                )
            $SQL$, v_test_memory_id),
            TRUE
        )
    LOOP
        RAISE NOTICE 'Test 2.1 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
    END LOOP;
    
    -- Test 2.2: Accept low score with safety violations documented
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'accept_low_score_with_violations',
            format($SQL$
                INSERT INTO safety.abstraction_metrics (
                    memory_id, abstraction_score, abstracted_ref_count, safety_violations
                ) VALUES (
                    '%s', 0.5, 5, ARRAY['concrete_reference_detected']
                )
            $SQL$, v_test_memory_id),
            FALSE
        )
    LOOP
        RAISE NOTICE 'Test 2.2 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
    END LOOP;
    
    -- Test 2.3: Validation log consistency check
    FOR v_test_results IN 
        SELECT * FROM test_safety.run_test(
            'reject_inconsistent_validation',
            format($SQL$
                INSERT INTO safety.validation_log (
                    memory_id, validation_type, validation_result, error_count
                ) VALUES (
                    '%s', 'abstraction', TRUE, 5
                )
            $SQL$, v_test_memory_id),
            TRUE
        )
    LOOP
        RAISE NOTICE 'Test 2.3 - %: %', v_test_results.test_name, 
            CASE WHEN v_test_results.passed THEN 'PASSED' ELSE 'FAILED' END;
    END LOOP;
    
    -- Clean up
    DELETE FROM safety.abstraction_metrics WHERE memory_id = v_test_memory_id;
    DELETE FROM safety.validation_log WHERE memory_id = v_test_memory_id;
END $$;

-- =====================================================
-- TEST SUITE 3: TEMPORAL SAFETY FUNCTIONS
-- =====================================================

DO $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_stale_refs RECORD;
    v_reference_id UUID;
BEGIN
    RAISE NOTICE '=== TEST SUITE 3: TEMPORAL SAFETY FUNCTIONS ===';
    
    -- Set up test data with old timestamp
    INSERT INTO safety.memory_references (
        id, memory_id, reference_type, abstracted_value, validation_timestamp
    ) VALUES (
        uuid_generate_v4(), v_test_memory_id, 'file_path', '<project>/old.txt', 
        NOW() - INTERVAL '45 days'
    ) RETURNING id INTO v_reference_id;
    
    -- Test 3.1: Identify stale references
    RAISE NOTICE 'Test 3.1 - identify_stale_references:';
    FOR v_stale_refs IN 
        SELECT * FROM safety.identify_stale_references(30)
        WHERE memory_id = v_test_memory_id
    LOOP
        RAISE NOTICE '  Found stale reference: % (%.2f days old)', 
            v_stale_refs.reference_id, v_stale_refs.age_days;
    END LOOP;
    
    -- Test 3.2: Check temporal safety
    RAISE NOTICE 'Test 3.2 - check_temporal_safety:';
    FOR v_stale_refs IN 
        SELECT * FROM safety.check_temporal_safety(v_test_memory_id, 24)
    LOOP
        RAISE NOTICE '  Is stale: %, Age: %.2f hours', 
            v_stale_refs.is_stale, v_stale_refs.age_hours;
    END LOOP;
    
    -- Clean up
    DELETE FROM safety.memory_references WHERE memory_id = v_test_memory_id;
END $$;

-- =====================================================
-- TEST SUITE 4: AUDIT LOGGING
-- =====================================================

DO $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_audit_count INTEGER;
    v_ref_id UUID;
BEGIN
    RAISE NOTICE '=== TEST SUITE 4: AUDIT LOGGING ===';
    
    -- Test 4.1: Verify audit logging on insert
    INSERT INTO safety.memory_references (
        memory_id, reference_type, abstracted_value
    ) VALUES (
        v_test_memory_id, 'identifier', '<user_id>'
    ) RETURNING id INTO v_ref_id;
    
    SELECT COUNT(*) INTO v_audit_count
    FROM safety.audit_log
    WHERE event_type = 'DATA_CHANGE'
        AND action = 'INSERT'
        AND memory_id = v_test_memory_id
        AND created_at > NOW() - INTERVAL '1 minute';
    
    RAISE NOTICE 'Test 4.1 - audit_on_insert: %', 
        CASE WHEN v_audit_count > 0 THEN 'PASSED' ELSE 'FAILED' END;
    
    -- Test 4.2: Verify audit logging on update
    UPDATE safety.memory_references
    SET abstracted_value = '<updated_user_id>'
    WHERE id = v_ref_id;
    
    SELECT COUNT(*) INTO v_audit_count
    FROM safety.audit_log
    WHERE event_type = 'DATA_CHANGE'
        AND action = 'UPDATE'
        AND memory_id = v_test_memory_id
        AND created_at > NOW() - INTERVAL '1 minute';
    
    RAISE NOTICE 'Test 4.2 - audit_on_update: %', 
        CASE WHEN v_audit_count > 0 THEN 'PASSED' ELSE 'FAILED' END;
    
    -- Test 4.3: Verify safety violation logging
    BEGIN
        INSERT INTO safety.memory_references (
            memory_id, reference_type, concrete_value, abstracted_value
        ) VALUES (
            v_test_memory_id, 'file_path', '/etc/passwd', NULL
        );
    EXCEPTION WHEN OTHERS THEN
        -- Expected to fail, check if it was logged
        NULL;
    END;
    
    SELECT COUNT(*) INTO v_audit_count
    FROM safety.validation_log
    WHERE validation_type = 'concrete_exposure'
        AND validation_result = FALSE
        AND created_at > NOW() - INTERVAL '1 minute';
    
    RAISE NOTICE 'Test 4.3 - safety_violation_logging: %', 
        CASE WHEN v_audit_count > 0 THEN 'PASSED' ELSE 'FAILED' END;
    
    -- Clean up
    DELETE FROM safety.memory_references WHERE memory_id = v_test_memory_id;
END $$;

-- =====================================================
-- TEST SUITE 5: ROW LEVEL SECURITY
-- =====================================================

-- Note: RLS tests require different database users to test properly
-- These tests demonstrate the expected behavior

DO $$
BEGIN
    RAISE NOTICE '=== TEST SUITE 5: ROW LEVEL SECURITY ===';
    RAISE NOTICE 'RLS Policy Tests (requires multiple users for full testing):';
    RAISE NOTICE '  - readonly_failed_validations: Users can only SELECT failed validations';
    RAISE NOTICE '  - no_update_validated_abstractions: Cannot UPDATE validated references';
    RAISE NOTICE '  - no_delete_audit: Cannot DELETE audit log entries';
    RAISE NOTICE '  - safety_score_access: Only access abstractions with score >= 0.8';
    RAISE NOTICE 'Note: Full RLS testing requires connecting as different users';
END $$;

-- =====================================================
-- TEST SUITE 6: COMPREHENSIVE SAFETY TEST
-- =====================================================

DO $$
DECLARE
    v_test_memory_id UUID := uuid_generate_v4();
    v_test_passed BOOLEAN := TRUE;
    v_test_results RECORD;
BEGIN
    RAISE NOTICE '=== TEST SUITE 6: COMPREHENSIVE SAFETY TEST ===';
    
    -- Run the built-in test function
    FOR v_test_results IN 
        SELECT * FROM safety.test_safety_constraints()
    LOOP
        RAISE NOTICE 'Test: % - %', v_test_results.test_name,
            CASE WHEN v_test_results.test_passed THEN 'PASSED' ELSE 'FAILED' END;
        IF v_test_results.error_message IS NOT NULL THEN
            RAISE NOTICE '  Error: %', v_test_results.error_message;
        END IF;
        
        IF NOT v_test_results.test_passed THEN
            v_test_passed := FALSE;
        END IF;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Overall Test Suite Result: %', 
        CASE WHEN v_test_passed THEN 'ALL TESTS PASSED' ELSE 'SOME TESTS FAILED' END;
END $$;

-- =====================================================
-- CLEANUP
-- =====================================================

-- Drop test helper function
DROP FUNCTION IF EXISTS test_safety.run_test(TEXT, TEXT, BOOLEAN);

-- Final summary
DO $$
DECLARE
    v_trigger_count INTEGER;
    v_policy_count INTEGER;
    v_constraint_count INTEGER;
BEGIN
    -- Count triggers
    SELECT COUNT(*) INTO v_trigger_count
    FROM pg_trigger
    WHERE tgrelid IN (
        SELECT oid FROM pg_class 
        WHERE relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'safety')
    );
    
    -- Count policies
    SELECT COUNT(*) INTO v_policy_count
    FROM pg_policies
    WHERE schemaname = 'safety';
    
    -- Count constraints
    SELECT COUNT(*) INTO v_constraint_count
    FROM pg_constraint
    WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'safety')
        AND conname LIKE 'chk_%';
    
    RAISE NOTICE '';
    RAISE NOTICE '=== SAFETY ENFORCEMENT SUMMARY ===';
    RAISE NOTICE 'Triggers installed: %', v_trigger_count;
    RAISE NOTICE 'RLS policies active: %', v_policy_count;
    RAISE NOTICE 'Check constraints: %', v_constraint_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Safety enforcement is now active at the database level.';
END $$;