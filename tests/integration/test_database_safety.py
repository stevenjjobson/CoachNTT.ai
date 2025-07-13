#!/usr/bin/env python3
"""
Integration tests for database-level safety enforcement.
Tests the triggers, constraints, and RLS policies from 001_safety_enforcement.sql
"""
import os
import sys
import psycopg2
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDatabaseSafety:
    """Test database-level safety enforcement mechanisms."""
    
    @pytest.fixture
    def db_connection(self):
        """Create a database connection for testing."""
        # Get connection details from environment
        db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://ccp_user:ccp_dev_password@localhost:5432/cognitive_coding_partner'
        )
        
        # Parse connection string
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        
        yield conn
        
        # Cleanup
        conn.rollback()
        conn.close()
    
    def test_reject_concrete_without_abstraction(self, db_connection):
        """Test that concrete references without abstraction are rejected."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # This should fail
        with pytest.raises(psycopg2.Error) as exc_info:
            cursor.execute("""
                INSERT INTO safety.memory_references 
                (memory_id, reference_type, concrete_value, abstracted_value)
                VALUES (%s, %s, %s, %s)
            """, (memory_id, 'file_path', '/home/user/secret.txt', None))
            db_connection.commit()
        
        assert 'SA002' in str(exc_info.value) or 'Concrete reference' in str(exc_info.value)
        db_connection.rollback()
    
    def test_reject_concrete_in_abstraction(self, db_connection):
        """Test that abstracted values containing concrete references are rejected."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # This should fail
        with pytest.raises(psycopg2.Error) as exc_info:
            cursor.execute("""
                INSERT INTO safety.memory_references 
                (memory_id, reference_type, concrete_value, abstracted_value)
                VALUES (%s, %s, %s, %s)
            """, (memory_id, 'file_path', '/home/user/file.txt', '/home/user/abstracted.txt'))
            db_connection.commit()
        
        assert 'SA003' in str(exc_info.value) or 'concrete references' in str(exc_info.value)
        db_connection.rollback()
    
    def test_accept_proper_abstraction(self, db_connection):
        """Test that properly abstracted references are accepted."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # This should succeed
        cursor.execute("""
            INSERT INTO safety.memory_references 
            (memory_id, reference_type, concrete_value, abstracted_value)
            VALUES (%s, %s, %s, %s)
        """, (memory_id, 'file_path', '/home/user/file.txt', '<user_home>/file.txt'))
        
        # Verify it was inserted
        cursor.execute("""
            SELECT id, is_valid FROM safety.memory_references 
            WHERE memory_id = %s
        """, (memory_id,))
        
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == True  # is_valid should be True
        
        # Cleanup
        cursor.execute("DELETE FROM safety.memory_references WHERE memory_id = %s", (memory_id,))
        db_connection.commit()
    
    def test_abstraction_metric_constraints(self, db_connection):
        """Test that abstraction metrics enforce minimum safety score."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # Test 1: Low score without violations - should fail
        with pytest.raises(psycopg2.Error):
            cursor.execute("""
                INSERT INTO safety.abstraction_metrics 
                (memory_id, abstraction_score, abstracted_ref_count)
                VALUES (%s, %s, %s)
            """, (memory_id, 0.5, 5))
            db_connection.commit()
        
        db_connection.rollback()
        
        # Test 2: Low score with violations documented - should succeed
        cursor.execute("""
            INSERT INTO safety.abstraction_metrics 
            (memory_id, abstraction_score, abstracted_ref_count, safety_violations)
            VALUES (%s, %s, %s, %s)
        """, (memory_id, 0.5, 5, ['concrete_reference_detected']))
        
        # Cleanup
        cursor.execute("DELETE FROM safety.abstraction_metrics WHERE memory_id = %s", (memory_id,))
        db_connection.commit()
    
    def test_validation_log_consistency(self, db_connection):
        """Test validation log consistency constraints."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # Test: validation_result=TRUE with error_count > 0 should fail
        with pytest.raises(psycopg2.Error):
            cursor.execute("""
                INSERT INTO safety.validation_log 
                (memory_id, validation_type, validation_result, error_count)
                VALUES (%s, %s, %s, %s)
            """, (memory_id, 'abstraction', True, 5))
            db_connection.commit()
        
        db_connection.rollback()
    
    def test_audit_logging(self, db_connection):
        """Test that audit logging captures all operations."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # Insert a reference
        cursor.execute("""
            INSERT INTO safety.memory_references 
            (memory_id, reference_type, abstracted_value)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (memory_id, 'identifier', '<user_id>'))
        
        ref_id = cursor.fetchone()[0]
        
        # Check audit log for INSERT
        cursor.execute("""
            SELECT COUNT(*) FROM safety.audit_log
            WHERE event_type = 'DATA_CHANGE'
            AND action = 'INSERT'
            AND memory_id = %s
            AND created_at > NOW() - INTERVAL '1 minute'
        """, (memory_id,))
        
        assert cursor.fetchone()[0] > 0
        
        # Update the reference
        cursor.execute("""
            UPDATE safety.memory_references
            SET abstracted_value = '<updated_user_id>'
            WHERE id = %s
        """, (ref_id,))
        
        # Check audit log for UPDATE
        cursor.execute("""
            SELECT COUNT(*) FROM safety.audit_log
            WHERE event_type = 'DATA_CHANGE'
            AND action = 'UPDATE'
            AND memory_id = %s
            AND created_at > NOW() - INTERVAL '1 minute'
        """, (memory_id,))
        
        assert cursor.fetchone()[0] > 0
        
        # Cleanup
        cursor.execute("DELETE FROM safety.memory_references WHERE memory_id = %s", (memory_id,))
        db_connection.commit()
    
    def test_temporal_safety_functions(self, db_connection):
        """Test temporal safety checking functions."""
        cursor = db_connection.cursor()
        memory_id = str(uuid4())
        
        # Insert old reference
        old_timestamp = datetime.now() - timedelta(days=45)
        cursor.execute("""
            INSERT INTO safety.memory_references 
            (memory_id, reference_type, abstracted_value, validation_timestamp)
            VALUES (%s, %s, %s, %s)
        """, (memory_id, 'file_path', '<project>/old.txt', old_timestamp))
        
        # Test identify_stale_references
        cursor.execute("""
            SELECT * FROM safety.identify_stale_references(30)
            WHERE memory_id = %s
        """, (memory_id,))
        
        result = cursor.fetchone()
        assert result is not None
        assert float(result[3]) > 30  # age_days > 30
        
        # Cleanup
        cursor.execute("DELETE FROM safety.memory_references WHERE memory_id = %s", (memory_id,))
        db_connection.commit()
    
    def test_safety_validation_helpers(self, db_connection):
        """Test safety validation helper functions."""
        cursor = db_connection.cursor()
        
        # Test contains_concrete_references function
        test_cases = [
            ("/home/user/file.txt", True),
            ("C:\\Users\\john\\document.doc", True),
            ("user_id = 12345", True),
            ("192.168.1.1", True),
            ("https://example.com/api", True),
            ("sk_live_abcd1234efgh5678", True),
            ("john@example.com", True),
            ("<user_home>/file.txt", False),
            ("<project_root>/src/main.py", False),
            ("<api_base_url>/users/<user_id>", False),
        ]
        
        for content, expected in test_cases:
            cursor.execute(
                "SELECT safety.contains_concrete_references(%s)",
                (content,)
            )
            result = cursor.fetchone()[0]
            assert result == expected, f"Failed for: {content}"
        
        db_connection.rollback()
    
    def test_comprehensive_safety(self, db_connection):
        """Run the built-in comprehensive safety test."""
        cursor = db_connection.cursor()
        
        # Run the built-in test function
        cursor.execute("SELECT * FROM safety.test_safety_constraints()")
        
        results = cursor.fetchall()
        all_passed = True
        
        for test_name, passed, error_msg in results:
            if not passed:
                all_passed = False
                print(f"Failed: {test_name} - {error_msg}")
        
        assert all_passed, "Some safety constraint tests failed"
        
        db_connection.rollback()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])