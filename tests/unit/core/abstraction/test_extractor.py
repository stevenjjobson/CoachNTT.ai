"""
Tests for the ReferenceExtractor.
Validates detection of concrete references in code and text.
"""
import pytest
from src.core.abstraction.extractor import ReferenceExtractor
from src.core.safety.models import ReferenceType


class TestReferenceExtractor:
    """Test the reference extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create a reference extractor instance."""
        return ReferenceExtractor()
    
    def test_file_path_detection(self, extractor):
        """Test detection of various file path formats."""
        test_cases = [
            ('/home/user/file.txt', ReferenceType.FILE_PATH),
            ('C:\\Users\\Admin\\Documents\\data.csv', ReferenceType.FILE_PATH),
            ('~/projects/myapp/config.yaml', ReferenceType.FILE_PATH),
            ('./relative/path/file.py', ReferenceType.FILE_PATH),
            ('../parent/directory/script.sh', ReferenceType.FILE_PATH),
        ]
        
        for path, expected_type in test_cases:
            content = f'Open the file: {path}'
            refs = extractor.extract_references(content)
            
            assert len(refs) >= 1
            assert any(ref.value == path and ref.type == expected_type for ref in refs)
    
    def test_identifier_detection(self, extractor):
        """Test detection of various identifier formats."""
        content = '''
        user_id = 12345
        order_id: 98765
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        DELETE FROM posts WHERE id = 456
        '''
        
        refs = extractor.extract_references(content)
        id_refs = [ref for ref in refs if ref.type == ReferenceType.IDENTIFIER]
        
        assert len(id_refs) >= 4
        values = [ref.value for ref in id_refs]
        assert '12345' in values
        assert '98765' in values
        assert '550e8400-e29b-41d4-a716-446655440000' in values
        assert '456' in values
    
    def test_url_detection(self, extractor):
        """Test detection of URLs."""
        content = '''
        api_endpoint = "https://api.example.com/v1/users"
        database_url = "postgresql://user:pass@localhost:5432/mydb"
        file_url = "file:///home/user/document.pdf"
        webhook = "http://webhook.site/unique-id"
        '''
        
        refs = extractor.extract_references(content)
        url_refs = [ref for ref in refs if ref.type == ReferenceType.URL]
        
        assert len(url_refs) >= 4
        urls = [ref.value for ref in url_refs]
        assert 'https://api.example.com/v1/users' in urls
        assert 'postgresql://user:pass@localhost:5432/mydb' in urls
        assert 'file:///home/user/document.pdf' in urls
        assert 'http://webhook.site/unique-id' in urls
    
    def test_ip_address_detection(self, extractor):
        """Test detection of IP addresses."""
        content = '''
        server_ip = "192.168.1.100"
        public_dns = "8.8.8.8"
        localhost = "127.0.0.1"
        ipv6_addr = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        '''
        
        refs = extractor.extract_references(content)
        ip_refs = [ref for ref in refs if ref.type == ReferenceType.IP_ADDRESS]
        
        assert len(ip_refs) >= 3  # IPv6 pattern might not be in simplified extractor
        ips = [ref.value for ref in ip_refs]
        assert '192.168.1.100' in ips
        assert '8.8.8.8' in ips
        assert '127.0.0.1' in ips
    
    def test_container_detection(self, extractor):
        """Test detection of container-related references."""
        content = '''
        docker run --name myapp-web-prod -d nginx:latest
        container_name: redis-cache-staging
        CONTAINER_ID=64d6f7439c8a
        image: postgres:13.4-alpine
        '''
        
        refs = extractor.extract_references(content)
        container_refs = [ref for ref in refs if ref.type == ReferenceType.CONTAINER]
        
        assert len(container_refs) >= 2
        values = [ref.value for ref in container_refs]
        # At minimum, should detect container names and IDs
        assert any('myapp-web-prod' in v for v in values)
        assert any('64d6f7439c8a' in v for v in values)
    
    def test_token_detection(self, extractor):
        """Test detection of tokens and secrets."""
        content = '''
        API_KEY = "sk_live_4nX8yKJ5kPQR3mNZ9vTW2hL6"
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        password = "MySecretPassword123!"
        SECRET_KEY=abcdef123456789
        '''
        
        refs = extractor.extract_references(content)
        token_refs = [ref for ref in refs if ref.type == ReferenceType.TOKEN]
        
        assert len(token_refs) >= 3
        # Should detect API keys, JWTs, and passwords
        values = [ref.value for ref in token_refs]
        assert any('sk_live_' in v for v in values)
        assert any(v.startswith('eyJ') for v in values)
    
    def test_timestamp_detection(self, extractor):
        """Test detection of timestamps."""
        content = '''
        created_at = "2024-01-15T10:30:00Z"
        expires = 1705315800
        last_modified: "2024-01-15"
        '''
        
        refs = extractor.extract_references(content)
        time_refs = [ref for ref in refs if ref.type == ReferenceType.TIMESTAMP]
        
        assert len(time_refs) >= 2
        values = [ref.value for ref in time_refs]
        assert '2024-01-15T10:30:00Z' in values
        assert '1705315800' in values
    
    def test_config_value_detection(self, extractor):
        """Test detection of configuration values."""
        content = '''
        DATABASE_HOST = "db.production.example.com"
        PORT = 8080
        DEBUG = true
        MAX_CONNECTIONS = 100
        '''
        
        refs = extractor.extract_references(content)
        config_refs = [ref for ref in refs if ref.type == ReferenceType.CONFIG_VALUE]
        
        assert len(config_refs) >= 1
        # Should at least detect the hostname
        values = [ref.value for ref in config_refs]
        assert any('db.production.example.com' in v for v in values)
    
    def test_overlapping_reference_handling(self, extractor):
        """Test handling of overlapping references."""
        content = 'File at /home/user/project/config.yaml:123'
        
        refs = extractor.extract_references(content)
        
        # Should not have overlapping references
        positions = [(ref.position[0], ref.position[1]) for ref in refs]
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i+1:], i+1):
                # No overlap
                assert pos1[1] <= pos2[0] or pos2[1] <= pos1[0]
    
    def test_context_extraction(self, extractor):
        """Test that context is properly extracted around references."""
        content = 'The user with id = 12345 has been created successfully'
        
        refs = extractor.extract_references(content)
        id_refs = [ref for ref in refs if ref.value == '12345']
        
        assert len(id_refs) == 1
        ref = id_refs[0]
        assert ref.context  # Should have context
        assert 'user' in ref.context.lower()
        assert 'created' in ref.context.lower()
    
    def test_custom_pattern_addition(self, extractor):
        """Test adding custom extraction patterns."""
        # Add pattern for custom ID format
        extractor.add_custom_pattern(
            name='ticket_id',
            pattern=r'TICKET-\d{6}',
            reference_type=ReferenceType.IDENTIFIER,
            confidence=0.95
        )
        
        content = 'Working on TICKET-123456 for the customer'
        refs = extractor.extract_references(content)
        
        ticket_refs = [ref for ref in refs if 'TICKET-' in ref.value]
        assert len(ticket_refs) == 1
        assert ticket_refs[0].value == 'TICKET-123456'
        assert ticket_refs[0].type == ReferenceType.IDENTIFIER
        assert ticket_refs[0].confidence == 0.95
    
    def test_pattern_stats(self, extractor):
        """Test pattern statistics retrieval."""
        stats = extractor.get_pattern_stats()
        
        assert 'total' in stats
        assert stats['total'] > 0
        assert 'file_paths' in stats
        assert 'identifiers' in stats
        assert 'urls' in stats
    
    def test_no_false_positives(self, extractor):
        """Test that common text doesn't trigger false positives."""
        content = '''
        This is a normal sentence with no references.
        The temperature is 25 degrees.
        Email me at john@example.com for more info.
        '''
        
        refs = extractor.extract_references(content)
        
        # Should only detect the email, not random numbers
        assert len(refs) <= 1  # Maybe email, but not the temperature
        
        # Temperature (25) should not be detected as an ID
        id_refs = [ref for ref in refs if ref.type == ReferenceType.IDENTIFIER]
        assert not any(ref.value == '25' for ref in id_refs)