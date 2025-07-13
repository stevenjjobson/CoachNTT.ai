"""
Tests for the SafetyValidator.
Validates that abstractions meet safety requirements.
"""
import pytest
from src.core.validation.validator import SafetyValidator
from src.core.safety.models import (
    Abstraction,
    Reference,
    ReferenceType,
    ValidationSeverity
)


class TestSafetyValidator:
    """Test the safety validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create a safety validator instance."""
        return SafetyValidator()
    
    def test_valid_abstraction_passes(self, validator):
        """Test that properly abstracted content passes validation."""
        original = 'File at /home/user/data.txt'
        abstracted = 'File at <user_home>/data.txt'
        
        abstractions = [
            Abstraction(
                original='/home/user/data.txt',
                abstracted='<user_home>/data.txt',
                reference_type=ReferenceType.FILE_PATH,
                mapping_key='file_path_1'
            )
        ]
        
        mappings = {'/home/user/data.txt': '<user_home>/data.txt'}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert result.valid
        assert result.safety_score >= 0.8
        assert len(result.errors) == 0
    
    def test_missing_abstraction_fails(self, validator):
        """Test that missing abstractions are detected."""
        original = 'File at /home/user/data.txt and config at /etc/app/config.json'
        abstracted = 'File at <user_home>/data.txt and config at /etc/app/config.json'
        
        # Only one abstraction provided
        abstractions = [
            Abstraction(
                original='/home/user/data.txt',
                abstracted='<user_home>/data.txt',
                reference_type=ReferenceType.FILE_PATH,
                mapping_key='file_path_1'
            )
        ]
        
        mappings = {'/home/user/data.txt': '<user_home>/data.txt'}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert not result.valid
        assert result.safety_score < 0.8
        assert any(error.code == 'E001' for error in result.errors)
    
    def test_inconsistent_abstraction_detected(self, validator):
        """Test detection of inconsistent abstractions."""
        original = 'User 123 and user 123 are the same'
        abstracted = 'User <user_id> and user <id> are the same'
        
        abstractions = [
            Abstraction(
                original='123',
                abstracted='<user_id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            ),
            Abstraction(
                original='123',
                abstracted='<id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_2'
            )
        ]
        
        mappings = {'123': '<user_id>'}  # Inconsistent!
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert len(result.errors) > 0
        assert any(error.code == 'E006' for error in result.errors)
    
    def test_invalid_placeholder_format(self, validator):
        """Test detection of invalid placeholder formats."""
        original = 'File at /home/user/data.txt'
        abstracted = 'File at <<nested>>/data.txt'
        
        abstractions = [
            Abstraction(
                original='/home/user/data.txt',
                abstracted='<<nested>>/data.txt',
                reference_type=ReferenceType.FILE_PATH,
                mapping_key='file_1'
            )
        ]
        
        mappings = {'/home/user/data.txt': '<<nested>>/data.txt'}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert len(result.errors) > 0
        assert any(error.code == 'E008' for error in result.errors)
    
    def test_security_warnings(self, validator):
        """Test detection of security issues."""
        original = 'password = "secret123"'
        abstracted = 'password = "secret123"'  # Not abstracted!
        
        abstractions = []  # No abstractions
        mappings = {}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert not result.valid
        assert any(
            error.code == 'E005' and error.severity == ValidationSeverity.CRITICAL
            for error in result.errors
        )
    
    def test_safety_score_calculation(self, validator):
        """Test safety score calculation."""
        # Perfect abstraction
        original = 'id = 123'
        abstracted = 'id = <id>'
        abstractions = [
            Abstraction(
                original='123',
                abstracted='<id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            )
        ]
        mappings = {'123': '<id>'}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert result.safety_score > 0.9  # Should be very high
        
        # Partial abstraction
        original2 = 'id = 123 and path = /home/user'
        abstracted2 = 'id = <id> and path = /home/user'  # Path not abstracted
        abstractions2 = [
            Abstraction(
                original='123',
                abstracted='<id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            )
        ]
        mappings2 = {'123': '<id>'}
        
        result2 = validator.validate(original2, abstracted2, abstractions2, mappings2)
        
        assert result2.safety_score < result.safety_score  # Lower score
        assert result2.safety_score < 0.8  # Below threshold
    
    def test_storage_validation(self, validator):
        """Test validation for storage readiness."""
        # Valid data
        valid_data = {
            'abstracted_prompt': 'Read the file',
            'abstracted_code': 'open(<file_path>)',
            'abstraction_mappings': {'/home/user/file.txt': '<file_path>'},
            'safety_score': 0.85,
            'validation_timestamp': '2024-01-15T10:00:00'
        }
        
        result = validator.validate_storage_ready(valid_data)
        assert result.valid
        
        # Missing required field
        invalid_data = {
            'abstracted_prompt': 'Read the file',
            # Missing abstracted_code
            'abstraction_mappings': {},
            'safety_score': 0.85,
            'validation_timestamp': '2024-01-15T10:00:00'
        }
        
        result2 = validator.validate_storage_ready(invalid_data)
        assert not result2.valid
        assert any(error.code == 'E007' for error in result2.errors)
        
        # Low safety score
        low_score_data = {
            'abstracted_prompt': 'Read the file',
            'abstracted_code': 'open("/home/user/file.txt")',  # Not abstracted!
            'abstraction_mappings': {},
            'safety_score': 0.5,  # Too low
            'validation_timestamp': '2024-01-15T10:00:00'
        }
        
        result3 = validator.validate_storage_ready(low_score_data)
        assert not result3.valid
        assert any(error.code == 'E002' for error in result3.errors)
    
    def test_completeness_validation(self, validator):
        """Test validation of abstraction completeness."""
        original = '''
        user_id = 12345
        file_path = "/home/user/data.csv"
        api_url = "https://api.example.com/users/12345"
        '''
        
        # Only partial abstractions
        abstracted = '''
        user_id = <user_id>
        file_path = "/home/user/data.csv"
        api_url = "https://api.example.com/users/12345"
        '''
        
        abstractions = [
            Abstraction(
                original='12345',
                abstracted='<user_id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            )
        ]
        
        mappings = {'12345': '<user_id>'}
        
        result = validator.validate(original, abstracted, abstractions, mappings)
        
        assert not result.valid
        errors = result.errors
        assert any(error.code == 'E010' for error in errors)  # Incomplete coverage
        assert result.metadata['coverage'] < 1.0
    
    def test_quality_abstraction_scoring(self, validator):
        """Test that quality abstractions get better scores."""
        original = 'user_id = 123'
        
        # High quality abstraction
        abstracted1 = 'user_id = <user_id>'
        abstractions1 = [
            Abstraction(
                original='123',
                abstracted='<user_id>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            )
        ]
        
        # Low quality abstraction
        abstracted2 = 'user_id = <value>'
        abstractions2 = [
            Abstraction(
                original='123',
                abstracted='<value>',
                reference_type=ReferenceType.IDENTIFIER,
                mapping_key='id_1'
            )
        ]
        
        result1 = validator.validate(
            original, abstracted1, abstractions1, {'123': '<user_id>'}
        )
        result2 = validator.validate(
            original, abstracted2, abstractions2, {'123': '<value>'}
        )
        
        # Specific abstraction should score higher
        assert result1.safety_score > result2.safety_score