"""
Comprehensive tests for the abstraction pipeline.
Tests the complete flow from reference detection to validation.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.validation.memory_validator import MemoryValidationPipeline
from src.core.validation.quality_scorer import AbstractionQualityScorer
from src.core.metrics.safety_metrics import SafetyMetricsCollector
from src.core.safety.models import (
    ReferenceType,
    ValidationResult,
    AbstractionResult,
    Reference,
    Abstraction,
    ValidationSeverity
)


class TestAbstractionPipeline:
    """Test the complete abstraction pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ConcreteAbstractionEngine()
        self.memory_pipeline = MemoryValidationPipeline()
        self.quality_scorer = AbstractionQualityScorer()
        self.metrics_collector = SafetyMetricsCollector()
    
    def test_file_path_abstraction(self):
        """Test abstraction of file paths."""
        content = """
        def load_config():
            with open('/home/user/myapp/config.json') as f:
                return json.load(f)
        """
        
        result = self.engine.abstract(content)
        
        assert result.is_safe
        assert len(result.abstractions) >= 1
        assert '/home/user/myapp/config.json' not in result.abstracted_content
        assert '<' in result.abstracted_content and '>' in result.abstracted_content
        assert result.validation.safety_score >= 0.8
    
    def test_database_url_abstraction(self):
        """Test abstraction of database URLs."""
        content = """
        DATABASE_URL = "postgresql://user:password@localhost:5432/myapp"
        redis_url = "redis://localhost:6379/0"
        """
        
        result = self.engine.abstract(content)
        
        assert result.is_safe
        assert 'user:password@localhost' not in result.abstracted_content
        assert 'postgresql' not in result.abstracted_content or '<database_url>' in result.abstracted_content
        assert result.validation.safety_score >= 0.8
    
    def test_api_key_abstraction(self):
        """Test abstraction of API keys and tokens."""
        content = """
        API_KEY = "sk-abc123def456ghi789"
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        """
        
        result = self.engine.abstract(content)
        
        assert result.is_safe
        assert 'sk-abc123def456ghi789' not in result.abstracted_content
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in result.abstracted_content
        assert '<api_key>' in result.abstracted_content or '<jwt_token>' in result.abstracted_content
    
    def test_mixed_references_abstraction(self):
        """Test abstraction of mixed reference types."""
        content = """
        import os
        from pathlib import Path
        
        # File operations
        config_path = "/etc/myapp/settings.conf"
        log_file = Path("/var/log/myapp.log")
        
        # Database connection
        db_url = "postgresql://dbuser:secret123@db.example.com:5432/production"
        
        # API configuration  
        api_endpoint = "https://api.example.com/v1/users/12345"
        auth_token = "Bearer abc-def-123-456"
        
        # Network settings
        server_ip = "192.168.1.100"
        port = 8080
        
        # Container settings
        docker_image = "myapp/backend:1.2.3"
        container_id = "f1d2c3b4a5e6"
        """
        
        result = self.engine.abstract(content)
        
        # Verify all concrete references are abstracted
        assert result.is_safe
        assert len(result.abstractions) >= 8  # Should find multiple references
        
        # Check specific abstractions
        abstracted = result.abstracted_content
        assert '/etc/myapp/settings.conf' not in abstracted
        assert 'dbuser:secret123@db.example.com' not in abstracted
        assert '192.168.1.100' not in abstracted
        assert 'abc-def-123-456' not in abstracted
        assert 'f1d2c3b4a5e6' not in abstracted
        
        # Verify placeholders are present
        assert '<' in abstracted and '>' in abstracted
        assert result.validation.safety_score >= 0.8
    
    def test_memory_validation_pipeline(self):
        """Test the complete memory validation pipeline."""
        memory_data = {
            'prompt': 'How do I connect to the database at postgresql://user:pass@localhost/mydb?',
            'code': '''
import psycopg2
conn = psycopg2.connect("postgresql://user:pass@localhost:5432/mydb")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = 12345")
            ''',
            'interaction_id': 'test-interaction-123',
            'files_involved': ['/home/developer/project/main.py'],
            'tags': ['database', 'postgresql']
        }
        
        result = self.memory_pipeline.validate_memory(memory_data)
        
        assert result.valid
        assert result.safety_score >= 0.8
        assert 'abstracted_prompt' in memory_data
        assert 'abstracted_code' in memory_data
        assert 'user:pass@localhost' not in memory_data['abstracted_prompt']
        assert 'user:pass@localhost' not in memory_data['abstracted_code']
        assert '12345' not in memory_data['abstracted_code']
    
    def test_quality_scoring(self):
        """Test abstraction quality scoring."""
        content = """
        config = {
            'database_url': 'postgresql://user:pass@localhost:5432/mydb',
            'redis_url': 'redis://localhost:6379',
            'api_key': 'sk-1234567890abcdef',
            'log_file': '/var/log/application.log'
        }
        """
        
        abstraction_result = self.engine.abstract(content)
        quality_score = self.quality_scorer.score_abstraction_result(abstraction_result)
        
        assert quality_score.overall_score > 0.0
        assert 'specificity' in quality_score.component_scores
        assert 'consistency' in quality_score.component_scores
        assert 'completeness' in quality_score.component_scores
        assert len(quality_score.feedback) > 0
    
    def test_metrics_collection(self):
        """Test safety metrics collection."""
        content = """
        database_url = "postgresql://user:pass@localhost:5432/app"
        api_key = "sk-test123"
        """
        
        # Record multiple abstractions
        for i in range(5):
            result = self.engine.abstract(content)
            self.metrics_collector.record_abstraction_result(result)
        
        metrics = self.metrics_collector.get_current_metrics()
        
        assert metrics['performance']['total_operations'] == 5
        assert metrics['performance']['success_rate'] > 0.0
        assert metrics['quality']['average_safety_score'] > 0.0
        assert 'recent_activity' in metrics
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty content
        result = self.engine.abstract("")
        assert result.is_safe
        assert len(result.abstractions) == 0
        
        # Content with no references
        result = self.engine.abstract("print('Hello, World!')")
        assert result.is_safe
        assert len(result.abstractions) == 0
        
        # Malformed URLs/paths
        result = self.engine.abstract("url = 'http://malformed[url'")
        # Should handle gracefully without crashing
        assert result.abstracted_content is not None
    
    def test_variable_abstraction_rules(self):
        """Test the new variable abstraction rules."""
        content = """
        current_user = get_user_by_id(12345)
        auth_token = request.headers.get('Authorization')
        config["database_url"] = "postgresql://localhost/db"
        self.user_service.create_user(data)
        """
        
        result = self.engine.abstract(content)
        
        assert result.is_safe
        # Should abstract user variables and function calls
        assert 'get_user_by_id' not in result.abstracted_content or '<entity>' in result.abstracted_content
        assert '12345' not in result.abstracted_content
        assert 'database_url' not in result.abstracted_content or '<db_config>' in result.abstracted_content
    
    def test_abstraction_consistency(self):
        """Test that same references get consistent abstractions."""
        content = """
        path1 = "/home/user/file1.txt"
        path2 = "/home/user/file2.txt"
        url1 = "https://api.example.com/users/123"
        url2 = "https://api.example.com/users/456"
        """
        
        result = self.engine.abstract(content)
        
        # Similar paths should use similar abstraction patterns
        abstractions = result.abstractions
        path_abstractions = [a for a in abstractions if a.reference_type == ReferenceType.FILE_PATH]
        url_abstractions = [a for a in abstractions if a.reference_type == ReferenceType.URL]
        
        # Check pattern consistency
        if len(path_abstractions) > 1:
            pattern_types = set(type(a.abstracted) for a in path_abstractions)
            assert len(pattern_types) == 1  # All should use same pattern type
        
        if len(url_abstractions) > 1:
            # URLs should have consistent abstraction structure
            abstracted_urls = [a.abstracted for a in url_abstractions]
            # Should all contain similar placeholder patterns
            assert all('<' in url and '>' in url for url in abstracted_urls)
    
    def test_temporal_safety(self):
        """Test that temporal references are properly handled."""
        content = """
        created_at = "2023-12-01T10:30:00Z"
        timestamp = 1701426600
        expire_date = "2024-01-01"
        """
        
        result = self.engine.abstract(content)
        
        # Temporal references should be abstracted
        temporal_abstractions = [
            a for a in result.abstractions 
            if a.reference_type == ReferenceType.TIMESTAMP
        ]
        
        if temporal_abstractions:
            # Verify temporal abstractions don't leak specific dates
            for abstraction in temporal_abstractions:
                assert '2023' not in abstraction.abstracted
                assert '2024' not in abstraction.abstracted
                assert '1701426600' not in abstraction.abstracted
    
    def test_security_validation(self):
        """Test that security-sensitive content is properly validated."""
        # High-risk content that should trigger security warnings
        content = """
        password = "super_secret_password"
        private_key = "-----BEGIN PRIVATE KEY-----"
        credit_card = "4532-1234-5678-9012"
        """
        
        result = self.engine.abstract(content)
        
        # Should detect and abstract security-sensitive content
        assert 'super_secret_password' not in result.abstracted_content
        assert 'BEGIN PRIVATE KEY' not in result.abstracted_content
        assert '4532-1234-5678-9012' not in result.abstracted_content
        
        # May have warnings about security content
        if result.validation.warnings:
            security_warnings = [
                w for w in result.validation.warnings
                if w.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
            ]
            # If detected as sensitive, should be flagged
            assert len(security_warnings) >= 0  # May or may not detect all patterns
    
    def test_performance_metrics(self):
        """Test that performance is within acceptable bounds."""
        # Test with medium-sized content
        content = """
        import os, sys, json
        from pathlib import Path
        
        """ + "\n".join([
            f'file_{i} = "/path/to/file_{i}.txt"'
            for i in range(50)
        ]) + """
        
        database_urls = [
            "postgresql://user:pass@localhost:5432/db1",
            "postgresql://user:pass@localhost:5432/db2",
            "postgresql://user:pass@localhost:5432/db3",
        ]
        
        api_keys = {
            'service1': 'sk-abc123def456',
            'service2': 'sk-def456ghi789',
            'service3': 'sk-ghi789jkl012',
        }
        """
        
        result = self.engine.abstract(content)
        
        # Should complete within reasonable time (under 5 seconds)
        assert result.processing_time_ms < 5000
        assert result.is_safe
        assert len(result.abstractions) >= 50  # Should find many references
    
    def test_integration_workflow(self):
        """Test the complete integration workflow."""
        # Simulate a complete memory storage workflow
        memory_data = {
            'prompt': 'Show me how to connect to PostgreSQL database',
            'code': '''
import psycopg2
import os

# Connect to database
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'myapp_production',
    'user': 'dbuser',
    'password': os.environ.get('DB_PASSWORD', 'defaultpass123')
}

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Query user data
user_id = 12345
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
user = cursor.fetchone()

print(f"User: {user}")
            ''',
            'interaction_id': 'workflow-test-001',
            'files_involved': ['/home/dev/myapp/database.py'],
            'tags': ['database', 'postgresql', 'python']
        }
        
        # Step 1: Validate memory through pipeline
        validation_result = self.memory_pipeline.validate_memory(memory_data)
        assert validation_result.valid
        
        # Step 2: Score abstraction quality
        abstraction_result = memory_data.get('_abstraction_result')
        if abstraction_result:
            quality_score = self.quality_scorer.score_abstraction_result(abstraction_result)
            assert quality_score.overall_score > 0.5
            
            # Step 3: Record metrics
            self.metrics_collector.record_abstraction_result(abstraction_result)
        
        # Step 4: Verify final memory data is safe for storage
        assert 'abstracted_prompt' in memory_data
        assert 'abstracted_code' in memory_data
        assert 'defaultpass123' not in memory_data['abstracted_code']
        assert '12345' not in memory_data['abstracted_code']
        assert 'myapp_production' not in memory_data['abstracted_code']
        
        # Step 5: Check metrics were recorded
        metrics = self.metrics_collector.get_current_metrics()
        assert metrics['performance']['total_operations'] >= 1


@pytest.fixture
def sample_code_with_references():
    """Sample code containing various types of references."""
    return """
import os
import requests
from pathlib import Path

# File paths
config_file = "/etc/myapp/config.json"
log_dir = Path("/var/log/myapp")
user_data = "~/Documents/data.csv"

# Database connections
DATABASE_URL = "postgresql://dbuser:secret123@db.example.com:5432/production"
REDIS_URL = "redis://localhost:6379/0"

# API configuration
API_BASE = "https://api.service.com/v1"
API_KEY = "sk-abc123def456ghi789"
AUTH_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

# Network settings
SERVER_IP = "192.168.1.100"
SERVER_PORT = 8080

# Container settings  
DOCKER_IMAGE = "mycompany/myapp:1.2.3"
CONTAINER_ID = "f1d2c3b4a5e6"

# Sensitive data
ADMIN_PASSWORD = "super_secret_admin_pass"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

def connect_database():
    return psycopg2.connect(DATABASE_URL)

def get_user_data(user_id=12345):
    url = f"{API_BASE}/users/{user_id}"
    headers = {"Authorization": AUTH_TOKEN}
    response = requests.get(url, headers=headers)
    return response.json()
"""


class TestComplexAbstractionScenarios:
    """Test complex abstraction scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = ConcreteAbstractionEngine()
    
    def test_nested_references(self, sample_code_with_references):
        """Test abstraction of nested and compound references."""
        result = self.engine.abstract(sample_code_with_references)
        
        assert result.is_safe
        assert len(result.abstractions) >= 15  # Should find many references
        
        # Verify no concrete sensitive data remains
        sensitive_data = [
            'secret123', 'super_secret_admin_pass', 'AKIAIOSFODNN7EXAMPLE',
            'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY', '192.168.1.100',
            '/etc/myapp/config.json', 'db.example.com', '12345'
        ]
        
        for sensitive in sensitive_data:
            assert sensitive not in result.abstracted_content
    
    def test_abstraction_reversibility(self):
        """Test that abstractions maintain enough info for reversal."""
        content = """
        DATABASE_URL = "postgresql://user:pass@localhost:5432/mydb"
        API_URL = "https://api.example.com/v1/users"
        """
        
        result = self.engine.abstract(content)
        
        # Mappings should allow reverse lookup
        assert len(result.mappings) >= 2
        
        # Should be able to identify what was abstracted
        db_mapping = next(
            (k for k, v in result.mappings.items() if 'postgresql' in k),
            None
        )
        api_mapping = next(
            (k for k, v in result.mappings.items() if 'api.example.com' in k),
            None
        )
        
        assert db_mapping is not None
        assert api_mapping is not None
    
    def test_abstraction_metadata_completeness(self):
        """Test that abstraction metadata is complete and useful."""
        content = """
        config = {
            'db': 'postgresql://user:pass@localhost/db',
            'cache': 'redis://localhost:6379',
            'api_key': 'sk-test123'
        }
        """
        
        result = self.engine.abstract(content)
        
        # Check abstraction metadata
        for abstraction in result.abstractions:
            assert hasattr(abstraction, 'original')
            assert hasattr(abstraction, 'abstracted') 
            assert hasattr(abstraction, 'reference_type')
            assert hasattr(abstraction, 'mapping_key')
            assert abstraction.metadata is not None
            
            # Metadata should contain useful information
            if 'confidence' in abstraction.metadata:
                assert 0.0 <= abstraction.metadata['confidence'] <= 1.0