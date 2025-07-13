"""
Tests for the ConcreteAbstractionEngine.
Validates safety-first abstraction of concrete references.
"""
import pytest
from src.core.abstraction.concrete_engine import ConcreteAbstractionEngine
from src.core.safety.models import ReferenceType


class TestConcreteAbstractionEngine:
    """Test the concrete abstraction engine implementation."""
    
    @pytest.fixture
    def engine(self):
        """Create an abstraction engine instance."""
        return ConcreteAbstractionEngine()
    
    def test_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine is not None
        assert hasattr(engine, 'extractor')
        assert hasattr(engine, 'generator')
        assert hasattr(engine, 'validator')
    
    def test_simple_file_path_abstraction(self, engine):
        """Test abstraction of simple file paths."""
        content = 'Read the file at /home/user/project/config.yaml'
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert '<' in result.abstracted_content
        assert '>' in result.abstracted_content
        assert '/home/user/project/config.yaml' not in result.abstracted_content
        assert result.validation.safety_score >= 0.8
    
    def test_multiple_references_abstraction(self, engine):
        """Test abstraction of content with multiple reference types."""
        content = '''
        user_id = 12345
        api_url = "https://api.example.com/v1/users/12345"
        config_file = "/etc/myapp/config.json"
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert '12345' not in result.abstracted_content
        assert 'https://api.example.com' not in result.abstracted_content
        assert '/etc/myapp/config.json' not in result.abstracted_content
        assert len(result.abstractions) >= 3
    
    def test_code_snippet_abstraction(self, engine):
        """Test abstraction of code snippets."""
        code = '''
        def get_user_data(user_id=98765):
            db_url = "postgresql://user:pass@localhost:5432/mydb"
            file_path = "/home/admin/data/users.csv"
            api_key = "sk_live_abcd1234efgh5678"
            return fetch_data(db_url, file_path, api_key)
        '''
        
        result = engine.abstract(code)
        
        assert result.is_safe
        assert '98765' not in result.abstracted_content
        assert 'postgresql://user:pass@localhost:5432/mydb' not in result.abstracted_content
        assert '/home/admin/data/users.csv' not in result.abstracted_content
        assert 'sk_live_abcd1234efgh5678' not in result.abstracted_content
        
        # Check that structure is preserved
        assert 'def get_user_data' in result.abstracted_content
        assert 'return fetch_data' in result.abstracted_content
    
    def test_docker_references_abstraction(self, engine):
        """Test abstraction of Docker-related references."""
        content = '''
        docker run -d --name myapp-prod-v1.2.3 \\
            -p 8080:80 \\
            mycompany/webapp:1.2.3
        
        container_id = "64d6f7439c8a"
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert 'myapp-prod-v1.2.3' not in result.abstracted_content
        assert '8080:80' in result.abstracted_content  # Port mappings might be preserved
        assert 'mycompany/webapp:1.2.3' not in result.abstracted_content
        assert '64d6f7439c8a' not in result.abstracted_content
    
    def test_sensitive_data_abstraction(self, engine):
        """Test abstraction of sensitive data like tokens and secrets."""
        content = '''
        API_KEY = "sk_live_4242424242424242"
        JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        password = "SuperSecret123!"
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert 'sk_live_4242424242424242' not in result.abstracted_content
        assert 'eyJ' not in result.abstracted_content  # JWT prefix should be abstracted
        assert 'SuperSecret123!' not in result.abstracted_content
        assert result.validation.safety_score >= 0.8
    
    def test_url_with_ids_abstraction(self, engine):
        """Test abstraction of URLs containing IDs."""
        content = '''
        user_profile = "https://api.example.com/users/12345/profile"
        order_details = "https://shop.example.com/orders/abc-123-def/details"
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert '12345' not in result.abstracted_content
        assert 'abc-123-def' not in result.abstracted_content
        # The API structure should be preserved
        assert 'users' in result.abstracted_content
        assert 'profile' in result.abstracted_content
    
    def test_failed_abstraction_handling(self, engine):
        """Test handling of abstraction failures."""
        # Use content that might cause issues
        content = None
        
        result = engine.abstract("")
        
        # Should handle gracefully
        assert result is not None
        assert result.validation.safety_score >= 0.8  # Empty content is safe
    
    def test_partial_abstraction_detection(self, engine):
        """Test detection of incomplete abstractions."""
        # Manually create partially abstracted content
        content = '''
        file1 = "<project_root>/config.yaml"  # Already abstracted
        file2 = "/home/user/data.json"        # Concrete reference
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        assert '/home/user/data.json' not in result.abstracted_content
        # Should preserve already abstracted content
        assert '<project_root>/config.yaml' in result.abstracted_content
    
    def test_consistency_validation(self, engine):
        """Test that similar references are abstracted consistently."""
        content = '''
        user_id = 123
        fetch_user(user_id=123)
        DELETE FROM users WHERE user_id = 123
        '''
        
        result = engine.abstract(content)
        
        assert result.is_safe
        # All instances of 123 should be abstracted the same way
        abstracted_refs = [a.abstracted for a in result.abstractions if a.original == '123']
        assert len(set(abstracted_refs)) == 1  # All should be identical
    
    def test_custom_pattern_addition(self, engine):
        """Test adding custom extraction patterns."""
        # Add custom pattern for project-specific IDs
        engine.add_custom_pattern(
            name='project_id',
            pattern=r'PROJ-\d{4}',
            reference_type='identifier',
            confidence=0.9
        )
        
        content = 'Working on project PROJ-1234 today'
        result = engine.abstract(content)
        
        assert result.is_safe
        assert 'PROJ-1234' not in result.abstracted_content
    
    def test_memory_entry_validation(self, engine):
        """Test validation of memory entries for storage."""
        memory_data = {
            'prompt': 'Read file /home/user/data.txt',
            'code': 'with open("/home/user/data.txt") as f: data = f.read()',
            'language': 'python'
        }
        
        result = engine.validate_memory_entry(memory_data)
        
        assert result.valid
        assert 'abstracted_prompt' in memory_data
        assert 'abstracted_code' in memory_data
        assert memory_data['safety_score'] >= 0.8
    
    def test_abstraction_stats(self, engine):
        """Test retrieval of abstraction statistics."""
        stats = engine.get_abstraction_stats()
        
        assert 'engine_type' in stats
        assert stats['engine_type'] == 'ConcreteAbstractionEngine'
        assert 'extractor_patterns' in stats
        assert 'minimum_safety_score' in stats
        assert stats['minimum_safety_score'] == 0.8