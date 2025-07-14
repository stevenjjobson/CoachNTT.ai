"""
Safety validation test fixtures for comprehensive testing.

Provides test cases for all safety edge cases and validation scenarios.
"""

from typing import Dict, List, Any, Tuple
import re


class SafetyFixtures:
    """Comprehensive safety validation test fixtures."""
    
    @staticmethod
    def get_unsafe_patterns() -> Dict[str, List[str]]:
        """Get comprehensive list of unsafe patterns to test."""
        return {
            "file_paths": [
                "/home/user/secret.txt",
                "C:\\Users\\Admin\\Documents\\passwords.xlsx",
                "/etc/passwd",
                "/var/log/system.log",
                "../../../etc/shadow",
                "~/Desktop/private/data.json",
                "D:\\Projects\\CompanyName\\src\\main.py",
                "/opt/application/config/database.yml",
            ],
            "urls": [
                "https://api.company.com/v1/users",
                "http://localhost:3000/admin",
                "ftp://files.example.com/backup.tar.gz", 
                "https://github.com/username/private-repo.git",
                "postgresql://user:pass@db.example.com:5432/database",
                "redis://password@cache.internal:6379/0",
                "mongodb+srv://admin:secret@cluster.mongodb.net/mydb",
            ],
            "emails": [
                "john.doe@company.com",
                "admin@example.org",
                "support+tag@service.io",
                "user.name+filter@gmail.com",
                "firstname.lastname@company.co.uk",
                "test_email.123@sub.domain.com",
            ],
            "credentials": [
                "API_KEY=sk-1234567890abcdef",
                "password: 'MySecretPass123!'",
                "token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'",
                "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
                "private_key = '-----BEGIN RSA PRIVATE KEY-----'",
                "client_secret: 'a1b2c3d4e5f6g7h8i9j0'",
                '"api_token": "ghp_xxxxxxxxxxxxxxxxxxxx"',
            ],
            "ip_addresses": [
                "192.168.1.100",
                "10.0.0.1",
                "172.16.254.1",
                "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
                "::1",
                "255.255.255.0",
                "Server IP: 203.0.113.45",
            ],
            "sensitive_data": [
                "SSN: 123-45-6789",
                "Credit Card: 4111-1111-1111-1111",
                "Phone: +1-555-123-4567",
                "DOB: 01/15/1985",
                "Account #: 12345678",
                "Patient ID: MRN-2023-0001",
                "Employee ID: EMP-123456",
            ],
        }
    
    @staticmethod
    def get_safe_abstractions() -> Dict[str, List[Tuple[str, str]]]:
        """Get expected safe abstractions for unsafe patterns."""
        return {
            "file_paths": [
                ("/home/user/secret.txt", "<user_home>/<sensitive_file>"),
                ("C:\\Users\\Admin\\Documents\\passwords.xlsx", "<system_drive>\\<user_directory>\\<documents>\\<sensitive_file>"),
                ("/etc/passwd", "<system_config>/<auth_file>"),
                ("../../../etc/shadow", "<path_traversal>/<system_config>/<auth_file>"),
            ],
            "urls": [
                ("https://api.company.com/v1/users", "<api_endpoint>"),
                ("postgresql://user:pass@db.example.com:5432/database", "<database_connection>"),
                ("https://github.com/username/private-repo.git", "<git_repository>"),
            ],
            "emails": [
                ("john.doe@company.com", "<user_email>"),
                ("admin@example.org", "<admin_email>"),
                ("support+tag@service.io", "<support_email>"),
            ],
            "credentials": [
                ("API_KEY=sk-1234567890abcdef", "API_KEY=<api_credential>"),
                ("password: 'MySecretPass123!'", "password: '<password_value>'"),
                ("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE", "AWS_ACCESS_KEY_ID=<aws_credential>"),
            ],
        }
    
    @staticmethod
    def get_edge_cases() -> List[Dict[str, Any]]:
        """Get edge cases for safety validation testing."""
        return [
            # Mixed content
            {
                "input": "Check the file at /home/user/data.csv and email results to admin@company.com",
                "expected_abstract": "Check the file at <user_home>/<data_file> and email results to <admin_email>",
                "safety_score_min": 0.8,
            },
            # Nested paths
            {
                "input": "Config located at /opt/app/config/subdir/../../secret/keys.json",
                "expected_contains": ["<application_path>", "<config_file>"],
                "safety_score_min": 0.85,
            },
            # Multiple occurrences
            {
                "input": "Copy /src/main.py to /dst/main.py and /src/test.py to /dst/test.py",
                "expected_abstract": "Copy <source_path>/<file> to <destination_path>/<file> and <source_path>/<file> to <destination_path>/<file>",
                "safety_score_min": 0.8,
            },
            # Code snippets
            {
                "input": 'const apiUrl = "https://api.example.com/v1"; const key = "sk-abc123";',
                "expected_contains": ["<api_endpoint>", "<api_credential>"],
                "safety_score_min": 0.9,
            },
            # False positives
            {
                "input": "The pattern /[a-z]+/ matches lowercase letters",
                "expected_abstract": "The pattern /[a-z]+/ matches lowercase letters",
                "safety_score_min": 0.95,
                "note": "Regex pattern should not be abstracted",
            },
            # Unicode and special chars
            {
                "input": "File: /home/użytkownik/文档/données.txt",
                "expected_contains": ["<user_home>", "<file>"],
                "safety_score_min": 0.85,
            },
            # Empty and null cases
            {
                "input": "",
                "expected_abstract": "",
                "safety_score_min": 1.0,
            },
            {
                "input": None,
                "expected_abstract": "",
                "safety_score_min": 1.0,
            },
            # Very long content
            {
                "input": f"Start content {' normal text ' * 1000} /etc/passwd {' more text ' * 1000} end",
                "expected_contains": ["<system_config>/<auth_file>"],
                "safety_score_min": 0.8,
                "note": "Should handle long content efficiently",
            },
        ]
    
    @staticmethod
    def get_validation_test_cases() -> List[Dict[str, Any]]:
        """Get comprehensive validation test cases."""
        return [
            # Structure validation
            {
                "test_name": "valid_memory_structure",
                "data": {
                    "memory_type": "learning",
                    "prompt": "Test prompt",
                    "content": "Safe content",
                    "metadata": {},
                },
                "expected_valid": True,
                "stage": "structure",
            },
            {
                "test_name": "missing_required_field",
                "data": {
                    "memory_type": "learning",
                    "content": "Safe content",
                    # Missing 'prompt'
                },
                "expected_valid": False,
                "expected_error": "missing required field",
                "stage": "structure",
            },
            # Type validation
            {
                "test_name": "invalid_memory_type",
                "data": {
                    "memory_type": "invalid_type",
                    "prompt": "Test",
                    "content": "Content",
                },
                "expected_valid": False,
                "expected_error": "invalid memory type",
                "stage": "structure",
            },
            # Safety validation
            {
                "test_name": "unsafe_content",
                "data": {
                    "memory_type": "debug",
                    "prompt": "Debug error",
                    "content": "Error in /home/user/app.py line 42",
                    "metadata": {},
                },
                "expected_valid": False,
                "expected_error": "safety validation failed",
                "stage": "safety",
            },
            # Metadata validation
            {
                "test_name": "invalid_metadata_type",
                "data": {
                    "memory_type": "context",
                    "prompt": "Test",
                    "content": "Content",
                    "metadata": "string instead of dict",
                },
                "expected_valid": False,
                "expected_error": "metadata must be dict",
                "stage": "structure",
            },
            # Length validation
            {
                "test_name": "content_too_long",
                "data": {
                    "memory_type": "learning",
                    "prompt": "Test",
                    "content": "x" * 100000,  # 100k chars
                    "metadata": {},
                },
                "expected_valid": False,
                "expected_error": "content too long",
                "stage": "structure",
            },
            # Injection attempts
            {
                "test_name": "sql_injection_attempt",
                "data": {
                    "memory_type": "debug",
                    "prompt": "'; DROP TABLE memories; --",
                    "content": "Safe content",
                },
                "expected_valid": True,  # Should be safe after abstraction
                "expected_abstracted": True,
                "stage": "safety",
            },
            # Special characters
            {
                "test_name": "special_unicode_chars",
                "data": {
                    "memory_type": "learning",
                    "prompt": "Testing émojis 🚀 and ñ",
                    "content": "Unicode content with 中文 and عربي",
                    "metadata": {"lang": "multi"},
                },
                "expected_valid": True,
                "stage": "all",
            },
        ]
    
    @staticmethod
    def get_safety_scoring_cases() -> List[Dict[str, Any]]:
        """Get test cases for safety scoring accuracy."""
        return [
            {
                "content": "Completely safe content with no sensitive information",
                "expected_score_range": (0.95, 1.0),
            },
            {
                "content": "The <file_path> contains <abstracted_content>",
                "expected_score_range": (0.90, 0.99),
            },
            {
                "content": "Mixed: Check /etc/config but abstracted to <system_config>",
                "expected_score_range": (0.7, 0.85),
            },
            {
                "content": "admin@company.com sent email about project",
                "expected_score_range": (0.0, 0.5),
            },
            {
                "content": "/home/user/secret.key with API_KEY=abc123",
                "expected_score_range": (0.0, 0.3),
            },
        ]
    
    @staticmethod
    def get_performance_test_data() -> Dict[str, Any]:
        """Get data for safety validation performance testing."""
        return {
            "small_content": "Simple test content",
            "medium_content": "Test content " * 100,  # ~1.2KB
            "large_content": "Test content " * 5000,  # ~60KB
            "many_patterns": " ".join([
                f"/path/to/file{i}.txt" for i in range(100)
            ]),
            "complex_patterns": """
                Server config at /etc/nginx/nginx.conf with upstream servers:
                - 192.168.1.10:8080 (web1.internal)
                - 192.168.1.11:8080 (web2.internal)
                Database: postgresql://user:pass@10.0.0.5:5432/myapp
                Admin emails: admin@company.com, ops@company.com
                API endpoints: https://api.company.com/v1/users, https://api.company.com/v1/posts
                Credentials stored in environment: API_KEY, DB_PASSWORD, JWT_SECRET
            """,
            "performance_targets": {
                "small_content_ms": 10,
                "medium_content_ms": 50,
                "large_content_ms": 200,
                "many_patterns_ms": 300,
                "complex_patterns_ms": 100,
            },
        }