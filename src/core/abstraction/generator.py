"""
PatternGenerator: Creates appropriate abstractions for concrete references.
Transforms concrete values into safe, reusable patterns.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from src.core.safety.models import (
    Reference,
    Abstraction,
    ReferenceType
)
from src.core.abstraction.rules import AbstractionRules


logger = logging.getLogger(__name__)


class PatternGenerator:
    """
    Generates safe abstractions for concrete references.
    Each abstraction preserves semantic meaning while removing concrete values.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pattern generator.
        
        Args:
            config: Configuration for pattern generation
        """
        self.config = config or {}
        self.generators = self._initialize_generators()
        self.placeholder_format = self.config.get('placeholder_format', '<{}>')
        self.abstraction_rules = AbstractionRules()
        logger.info("Initialized PatternGenerator")
    
    def _initialize_generators(self) -> Dict[ReferenceType, callable]:
        """Initialize generation functions for each reference type."""
        return {
            ReferenceType.FILE_PATH: self._generate_file_path_abstraction,
            ReferenceType.IDENTIFIER: self._generate_identifier_abstraction,
            ReferenceType.URL: self._generate_url_abstraction,
            ReferenceType.IP_ADDRESS: self._generate_ip_abstraction,
            ReferenceType.CONTAINER: self._generate_container_abstraction,
            ReferenceType.CONFIG_VALUE: self._generate_config_abstraction,
            ReferenceType.TIMESTAMP: self._generate_timestamp_abstraction,
            ReferenceType.TOKEN: self._generate_token_abstraction,
            ReferenceType.UNKNOWN: self._generate_generic_abstraction,
        }
    
    def generate_abstraction(
        self, reference: Reference, context: Optional[Dict[str, Any]] = None
    ) -> Abstraction:
        """
        Generate an appropriate abstraction for a reference.
        
        Args:
            reference: The concrete reference to abstract
            context: Additional context for generation
            
        Returns:
            An abstraction for the reference
        """
        context = context or {}
        
        # Get the appropriate generator
        generator = self.generators.get(
            reference.type,
            self._generate_generic_abstraction
        )
        
        try:
            # First try to apply specific abstraction rules
            rule_based_abstraction = self.abstraction_rules.apply_rules(reference, context)
            if rule_based_abstraction:
                abstracted_value = rule_based_abstraction
            else:
                # Fall back to type-specific generators
                abstracted_value = generator(reference, context)
            
            # Create unique mapping key
            mapping_key = self._create_mapping_key(reference, abstracted_value)
            
            abstraction = Abstraction(
                original=reference.value,
                abstracted=abstracted_value,
                reference_type=reference.type,
                mapping_key=mapping_key,
                metadata={
                    'confidence': reference.confidence,
                    'detection_rule': reference.detection_rule,
                    'context_snippet': reference.context[:100] if reference.context else None
                }
            )
            
            return abstraction
            
        except Exception as e:
            logger.error(f"Failed to generate abstraction for {reference.value}: {e}")
            # Fallback to generic abstraction
            return self._create_generic_abstraction(reference)
    
    def _generate_file_path_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for file paths."""
        path = reference.value
        
        # Handle home directory
        if path.startswith('~'):
            remaining = path[1:].lstrip('/')
            return self._format_placeholder('user_home') + '/' + remaining
        
        # Handle absolute paths
        if os.path.isabs(path):
            # Try to identify semantic roots
            path_lower = path.lower()
            
            # Common system directories
            if '/home/' in path or '/users/' in path:
                # Extract path after username
                parts = Path(path).parts
                for i, part in enumerate(parts):
                    if part in ('home', 'users') and i + 1 < len(parts):
                        remaining = '/'.join(parts[i+2:])
                        return self._format_placeholder('user_home') + '/' + remaining
            
            # Project paths
            if any(marker in path_lower for marker in ['project', 'workspace', 'src', 'app']):
                # Find the project root
                parts = Path(path).parts
                for i, part in enumerate(parts):
                    if part.lower() in ['project', 'projects', 'workspace', 'src', 'app']:
                        remaining = '/'.join(parts[i:])
                        return self._format_placeholder('project_root') + '/' + remaining
            
            # System paths
            if path.startswith('/etc/'):
                return self._format_placeholder('system_config') + path[4:]
            if path.startswith('/var/log/'):
                return self._format_placeholder('log_directory') + path[8:]
            if path.startswith('/tmp/') or path.startswith('/var/tmp/'):
                # Generalize temp file names
                filename = os.path.basename(path)
                if re.search(r'[0-9a-f]{6,}', filename):
                    filename = re.sub(r'[0-9a-f]{6,}', '*', filename)
                return self._format_placeholder('temp_dir') + '/' + filename
            
            # Generic absolute path
            return self._format_placeholder('absolute_path')
        
        # Relative paths
        if path.startswith('./'):
            return self._format_placeholder('current_dir') + path[1:]
        if path.startswith('../'):
            return self._format_placeholder('parent_dir') + path[2:]
        
        # Paths without clear indicators
        return self._format_placeholder('path')
    
    def _generate_identifier_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for identifiers."""
        value = reference.value
        
        # UUID pattern
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value.lower()):
            # Try to determine UUID type from context
            context_lower = reference.context.lower() if reference.context else ""
            if 'session' in context_lower:
                return self._format_placeholder('session_uuid')
            if 'user' in context_lower:
                return self._format_placeholder('user_uuid')
            return self._format_placeholder('uuid')
        
        # Numeric IDs - try to infer type from context
        if value.isdigit():
            context_lower = reference.context.lower() if reference.context else ""
            
            # Common ID types
            id_types = {
                'user': 'user_id',
                'order': 'order_id',
                'product': 'product_id',
                'customer': 'customer_id',
                'session': 'session_id',
                'transaction': 'transaction_id',
                'post': 'post_id',
                'comment': 'comment_id',
            }
            
            for keyword, placeholder in id_types.items():
                if keyword in context_lower:
                    return self._format_placeholder(placeholder)
            
            # Generic numeric ID
            return self._format_placeholder('id')
        
        # Hash-like identifiers
        if re.match(r'^[a-f0-9]{6,}$', value.lower()):
            if len(value) == 12:
                return self._format_placeholder('container_id')
            if len(value) == 40:
                return self._format_placeholder('git_hash')
            return self._format_placeholder('hash_id')
        
        # Generic identifier
        return self._format_placeholder('identifier')
    
    def _generate_url_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for URLs."""
        url = reference.value
        
        try:
            parsed = urlparse(url)
            
            # Database URLs
            if parsed.scheme in ['postgresql', 'mysql', 'mongodb', 'redis']:
                return self._format_placeholder('database_url')
            
            # File URLs
            if parsed.scheme == 'file':
                return self._format_placeholder('file_url')
            
            # HTTP(S) URLs
            if parsed.scheme in ['http', 'https']:
                # Localhost/development URLs
                if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                    path = parsed.path.rstrip('/')
                    if not path:
                        return self._format_placeholder('local_service')
                    return self._format_placeholder('local_service') + path
                
                # API URLs
                if 'api' in parsed.hostname or '/api' in parsed.path:
                    # Extract API path after version
                    path_parts = parsed.path.strip('/').split('/')
                    api_path = []
                    for i, part in enumerate(path_parts):
                        if part.startswith('v') and part[1:].isdigit():
                            # Found version, keep rest of path but abstract IDs
                            api_path = path_parts[i+1:]
                            break
                    
                    # Abstract numeric parts in path
                    abstracted_path = []
                    for part in api_path:
                        if part.isdigit():
                            abstracted_path.append(self._format_placeholder('id'))
                        elif re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}', part):
                            abstracted_path.append(self._format_placeholder('uuid'))
                        else:
                            abstracted_path.append(part)
                    
                    if abstracted_path:
                        return self._format_placeholder('api_base_url') + '/' + '/'.join(abstracted_path)
                    return self._format_placeholder('api_base_url')
                
                # Environment-specific URLs
                if any(env in parsed.hostname for env in ['staging', 'stage', 'dev', 'development']):
                    return self._format_placeholder('staging_url') + parsed.path
                if any(env in parsed.hostname for env in ['prod', 'production']):
                    return self._format_placeholder('prod_url') + parsed.path
                
                # Generic HTTP URL
                return self._format_placeholder('service_url')
            
            # Other schemes
            return self._format_placeholder(f'{parsed.scheme}_url')
            
        except Exception as e:
            logger.warning(f"Failed to parse URL {url}: {e}")
            return self._format_placeholder('url')
    
    def _generate_ip_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for IP addresses."""
        ip = reference.value
        
        # Check if IPv4
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            parts = ip.split('.')
            first_octet = int(parts[0])
            
            # Private IP ranges
            if first_octet == 10:
                return self._format_placeholder('private_ip')
            if first_octet == 172 and 16 <= int(parts[1]) <= 31:
                return self._format_placeholder('private_ip')
            if first_octet == 192 and int(parts[1]) == 168:
                return self._format_placeholder('local_ip')
            
            # Localhost
            if ip == '127.0.0.1':
                return self._format_placeholder('localhost')
            
            # Public DNS servers
            if ip in ['8.8.8.8', '8.8.4.4', '1.1.1.1']:
                return self._format_placeholder('public_dns')
            
            # Generic public IP
            return self._format_placeholder('public_ip')
        
        # IPv6
        if ':' in ip:
            if ip == '::1':
                return self._format_placeholder('localhost_ipv6')
            return self._format_placeholder('ipv6_address')
        
        return self._format_placeholder('ip_address')
    
    def _generate_container_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for container references."""
        value = reference.value
        
        # Container IDs (12-char hex)
        if re.match(r'^[0-9a-f]{12}$', value):
            return self._format_placeholder('container_id')
        
        # Image with tag
        if ':' in value and '/' in value:
            # e.g., myapp/web:1.2.3
            parts = value.rsplit(':', 1)
            if len(parts) == 2:
                image, tag = parts
                if re.match(r'^\d+\.\d+', tag):
                    return f"{image}:{self._format_placeholder('version')}"
                return f"{image}:{self._format_placeholder('tag')}"
        
        # Container names with environment/version
        if any(env in value.lower() for env in ['prod', 'staging', 'dev']):
            # Try to identify the service name
            parts = value.split('-')
            if len(parts) > 1:
                # Keep first part as service name
                return self._format_placeholder(f'{parts[0]}_container')
        
        # Generic container name
        return self._format_placeholder('container')
    
    def _generate_config_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for configuration values."""
        value = reference.value
        context_lower = reference.context.lower() if reference.context else ""
        
        # Port numbers
        if value.isdigit() and 1 <= int(value) <= 65535:
            port = int(value)
            # Common ports
            if port == 3000:
                return self._format_placeholder('app_port')
            if port in [80, 8080]:
                return self._format_placeholder('http_port')
            if port == 443:
                return self._format_placeholder('https_port')
            if port == 5432:
                return self._format_placeholder('postgres_port')
            if port == 3306:
                return self._format_placeholder('mysql_port')
            if port == 6379:
                return self._format_placeholder('redis_port')
            return self._format_placeholder('port')
        
        # Boolean values
        if value.lower() in ['true', 'false', 'yes', 'no', '1', '0']:
            if 'debug' in context_lower:
                return self._format_placeholder('debug_flag')
            if 'enable' in context_lower:
                return self._format_placeholder('feature_flag')
            return self._format_placeholder('boolean_flag')
        
        # Environment names
        if value.lower() in ['development', 'staging', 'production', 'test']:
            return self._format_placeholder('environment')
        
        # Hostnames
        if '.' in value and not value.replace('.', '').isdigit():
            if 'database' in context_lower or 'db' in context_lower:
                return self._format_placeholder('database_host')
            return self._format_placeholder('hostname')
        
        # Generic config value
        return self._format_placeholder('config_value')
    
    def _generate_timestamp_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for timestamps."""
        value = reference.value
        
        # ISO 8601 format
        if 'T' in value and any(char in value for char in [':', '-']):
            return self._format_placeholder('timestamp')
        
        # Unix timestamp (10 digits)
        if value.isdigit() and len(value) == 10:
            return self._format_placeholder('unix_timestamp')
        
        # Date only
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return self._format_placeholder('date')
        
        # HTTP date format
        if any(day in value for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
            return self._format_placeholder('http_date')
        
        return self._format_placeholder('timestamp')
    
    def _generate_token_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate abstraction for tokens and secrets."""
        value = reference.value
        context_lower = reference.context.lower() if reference.context else ""
        
        # JWT token
        if value.startswith('eyJ'):
            return self._format_placeholder('jwt_token')
        
        # API key patterns
        if 'api' in context_lower and 'key' in context_lower:
            return self._format_placeholder('api_key')
        
        # AWS patterns
        if value.startswith('AKIA'):
            return self._format_placeholder('aws_access_key')
        if len(value) == 40 and 'aws' in context_lower:
            return self._format_placeholder('aws_secret')
        
        # Password
        if 'password' in context_lower:
            return self._format_placeholder('password')
        
        # Generic token/secret
        if 'token' in context_lower:
            return self._format_placeholder('auth_token')
        if 'secret' in context_lower:
            return self._format_placeholder('secret')
        
        return self._format_placeholder('token')
    
    def _generate_generic_abstraction(
        self, reference: Reference, context: Dict[str, Any]
    ) -> str:
        """Generate generic abstraction when type-specific generation fails."""
        # Try to infer from context
        if reference.context:
            context_lower = reference.context.lower()
            
            # Common patterns
            patterns = {
                'file': 'file_reference',
                'path': 'path_reference',
                'url': 'url_reference',
                'id': 'id_reference',
                'key': 'key_reference',
                'name': 'name_reference',
                'value': 'value_reference',
            }
            
            for keyword, placeholder in patterns.items():
                if keyword in context_lower:
                    return self._format_placeholder(placeholder)
        
        # Ultimate fallback
        return self._format_placeholder('reference')
    
    def _create_generic_abstraction(self, reference: Reference) -> Abstraction:
        """Create a generic abstraction as fallback."""
        abstracted = self._format_placeholder(reference.type.value)
        mapping_key = f"{reference.type.value}_{abs(hash(reference.value))}"
        
        return Abstraction(
            original=reference.value,
            abstracted=abstracted,
            reference_type=reference.type,
            mapping_key=mapping_key,
            metadata={'fallback': True}
        )
    
    def _format_placeholder(self, name: str) -> str:
        """Format a placeholder name according to configuration."""
        return self.placeholder_format.format(name)
    
    def _create_mapping_key(self, reference: Reference, abstracted: str) -> str:
        """Create a unique key for the abstraction mapping."""
        # Use type, abstracted form, and hash of original
        return f"{reference.type.value}:{abstracted}:{abs(hash(reference.value))}"