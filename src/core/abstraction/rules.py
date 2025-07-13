"""
Abstraction rules for different types of references.
Defines specific transformation rules for converting concrete references to safe abstractions.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

from src.core.safety.models import Reference, ReferenceType


logger = logging.getLogger(__name__)


@dataclass
class AbstractionRule:
    """A rule for abstracting a specific type of reference."""
    name: str
    description: str
    reference_type: ReferenceType
    pattern: Optional[re.Pattern] = None
    transformer: Optional[Callable[[str, Dict[str, Any]], str]] = None
    examples: List[tuple[str, str]] = None  # (original, abstracted) pairs


class AbstractionRules:
    """
    Collection of abstraction rules for different reference types.
    Each rule defines how to transform a concrete reference into a safe abstraction.
    """
    
    def __init__(self):
        """Initialize the abstraction rules."""
        self.rules = self._initialize_rules()
        logger.info(f"Initialized {len(self.rules)} abstraction rules")
    
    def _initialize_rules(self) -> Dict[str, List[AbstractionRule]]:
        """Initialize all abstraction rules."""
        return {
            'variables': self._get_variable_rules(),
            'database': self._get_database_rules(),
            'api': self._get_api_rules(),
            'cloud': self._get_cloud_rules(),
            'personal': self._get_personal_rules(),
            'system': self._get_system_rules(),
        }
    
    def _get_variable_rules(self) -> List[AbstractionRule]:
        """Rules for abstracting variable names and code references."""
        return [
            AbstractionRule(
                name="user_variable",
                description="User-related variable names",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(current_?user|user_?obj|user_?instance|active_?user)\b', re.IGNORECASE),
                transformer=lambda val, ctx: '<user_reference>',
                examples=[
                    ('current_user', '<user_reference>'),
                    ('userObj', '<user_reference>'),
                    ('active_user', '<user_reference>'),
                ]
            ),
            AbstractionRule(
                name="auth_variable",
                description="Authentication-related variables",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(auth_?token|session_?id|auth_?header|bearer_?token)\b', re.IGNORECASE),
                transformer=lambda val, ctx: '<auth_variable>',
                examples=[
                    ('auth_token', '<auth_variable>'),
                    ('sessionId', '<auth_variable>'),
                    ('bearerToken', '<auth_variable>'),
                ]
            ),
            AbstractionRule(
                name="config_variable",
                description="Configuration variables",
                reference_type=ReferenceType.CONFIG_VALUE,
                pattern=re.compile(r'\b(config|settings|options|params|env)\[["\']([^"\']+)["\']\]'),
                transformer=self._transform_config_variable,
                examples=[
                    ('config["database_url"]', 'config["<db_config>"]'),
                    ('settings["api_key"]', 'settings["<api_config>"]'),
                    ('env["NODE_ENV"]', 'env["<env_var>"]'),
                ]
            ),
            AbstractionRule(
                name="class_instance",
                description="Class instance variables with concrete names",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(self|this)\.([\w_]+)_?(client|service|manager|handler)\b'),
                transformer=self._transform_class_instance,
                examples=[
                    ('self.database_client', 'self.<db_service>'),
                    ('this.userService', 'this.<user_service>'),
                    ('self.cache_manager', 'self.<cache_service>'),
                ]
            ),
            AbstractionRule(
                name="function_name",
                description="Function names with concrete references",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(get|set|update|delete|create)_([a-zA-Z0-9]+)_?(by_id|by_name|by_email)\b'),
                transformer=self._transform_function_name,
                examples=[
                    ('get_user_by_id', 'get_<entity>_by_id'),
                    ('update_product_by_name', 'update_<entity>_by_name'),
                    ('delete_order_by_id', 'delete_<entity>_by_id'),
                ]
            ),
        ]
    
    def _get_database_rules(self) -> List[AbstractionRule]:
        """Rules for database-related abstractions."""
        return [
            AbstractionRule(
                name="table_name",
                description="Database table names",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', re.IGNORECASE),
                transformer=self._transform_table_name,
                examples=[
                    ('FROM users', 'FROM <users_table>'),
                    ('JOIN orders', 'JOIN <orders_table>'),
                    ('UPDATE products', 'UPDATE <products_table>'),
                ]
            ),
            AbstractionRule(
                name="column_name",
                description="Database column names",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(SELECT|WHERE|ORDER BY|GROUP BY)\s+([a-zA-Z_][a-zA-Z0-9_,\s]*)\b', re.IGNORECASE),
                transformer=self._transform_column_names,
                examples=[
                    ('SELECT user_id, email', 'SELECT <id_column>, <email_column>'),
                    ('WHERE created_at > ?', 'WHERE <timestamp_column> > ?'),
                ]
            ),
            AbstractionRule(
                name="connection_string",
                description="Database connection strings",
                reference_type=ReferenceType.URL,
                pattern=re.compile(r'(postgresql|mysql|mongodb|redis)://([^:\s]+):([^@\s]+)@([^:/\s]+)(?::(\d+))?/([^\s?]+)'),
                transformer=lambda val, ctx: '<database_connection_string>',
                examples=[
                    ('postgresql://user:pass@localhost:5432/mydb', '<database_connection_string>'),
                    ('mysql://root:secret@db.example.com/app', '<database_connection_string>'),
                ]
            ),
        ]
    
    def _get_api_rules(self) -> List[AbstractionRule]:
        """Rules for API-related abstractions."""
        return [
            AbstractionRule(
                name="api_endpoint",
                description="API endpoint paths",
                reference_type=ReferenceType.URL,
                pattern=re.compile(r'/api/v\d+/([a-zA-Z]+)/(\d+|[a-zA-Z0-9-]+)'),
                transformer=self._transform_api_endpoint,
                examples=[
                    ('/api/v1/users/123', '/api/v1/users/<id>'),
                    ('/api/v2/products/abc-def', '/api/v2/products/<identifier>'),
                ]
            ),
            AbstractionRule(
                name="api_key_header",
                description="API key in headers",
                reference_type=ReferenceType.TOKEN,
                pattern=re.compile(r'["\']?(X-API-Key|Authorization|API-Key)["\']?\s*:\s*["\']?([^"\']+)["\']?', re.IGNORECASE),
                transformer=lambda val, ctx: f'{val.split(":")[0]}: <api_key>',
                examples=[
                    ('X-API-Key: abc123def456', 'X-API-Key: <api_key>'),
                    ('Authorization: Bearer token123', 'Authorization: Bearer <auth_token>'),
                ]
            ),
        ]
    
    def _get_cloud_rules(self) -> List[AbstractionRule]:
        """Rules for cloud service abstractions."""
        return [
            AbstractionRule(
                name="aws_resource",
                description="AWS resource identifiers",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'arn:aws:([^:]+):([^:]+):([^:]+):([^:]+)'),
                transformer=lambda val, ctx: 'arn:aws:<service>:<region>:<account>:<resource>',
                examples=[
                    ('arn:aws:s3:::my-bucket', 'arn:aws:<service>:<region>:<account>:<resource>'),
                    ('arn:aws:lambda:us-east-1:123456:function:myFunc', 'arn:aws:<service>:<region>:<account>:<resource>'),
                ]
            ),
            AbstractionRule(
                name="s3_bucket",
                description="S3 bucket names",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r's3://([a-zA-Z0-9\-\.]+)/'),
                transformer=lambda val, ctx: 's3://<bucket_name>/',
                examples=[
                    ('s3://my-app-bucket/', 's3://<bucket_name>/'),
                    ('s3://prod.data.bucket/', 's3://<bucket_name>/'),
                ]
            ),
            AbstractionRule(
                name="azure_resource",
                description="Azure resource paths",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'/subscriptions/([^/]+)/resourceGroups/([^/]+)/'),
                transformer=lambda val, ctx: '/subscriptions/<subscription_id>/resourceGroups/<resource_group>/',
                examples=[
                    ('/subscriptions/12345/resourceGroups/mygroup/', '/subscriptions/<subscription_id>/resourceGroups/<resource_group>/'),
                ]
            ),
        ]
    
    def _get_personal_rules(self) -> List[AbstractionRule]:
        """Rules for personal information abstractions."""
        return [
            AbstractionRule(
                name="email_address",
                description="Email addresses",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
                transformer=lambda val, ctx: '<email_address>',
                examples=[
                    ('user@example.com', '<email_address>'),
                    ('john.doe@company.org', '<email_address>'),
                ]
            ),
            AbstractionRule(
                name="phone_number",
                description="Phone numbers",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
                transformer=lambda val, ctx: '<phone_number>',
                examples=[
                    ('+1-555-123-4567', '<phone_number>'),
                    ('(555) 123-4567', '<phone_number>'),
                ]
            ),
            AbstractionRule(
                name="social_security",
                description="Social Security Numbers",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
                transformer=lambda val, ctx: '<ssn>',
                examples=[
                    ('123-45-6789', '<ssn>'),
                ]
            ),
        ]
    
    def _get_system_rules(self) -> List[AbstractionRule]:
        """Rules for system-related abstractions."""
        return [
            AbstractionRule(
                name="process_id",
                description="Process IDs",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b(pid|PID|process_id)\s*[=:]\s*(\d+)\b'),
                transformer=lambda val, ctx: val.split('=')[0].strip() + ' = <process_id>',
                examples=[
                    ('pid = 12345', 'pid = <process_id>'),
                    ('PID: 67890', 'PID: <process_id>'),
                ]
            ),
            AbstractionRule(
                name="mac_address",
                description="MAC addresses",
                reference_type=ReferenceType.IDENTIFIER,
                pattern=re.compile(r'\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'),
                transformer=lambda val, ctx: '<mac_address>',
                examples=[
                    ('00:11:22:33:44:55', '<mac_address>'),
                    ('AA-BB-CC-DD-EE-FF', '<mac_address>'),
                ]
            ),
        ]
    
    def _transform_config_variable(self, value: str, context: Dict[str, Any]) -> str:
        """Transform configuration variable access."""
        match = re.search(r'\[["\'](.*?)["\']\]', value)
        if match:
            key = match.group(1).lower()
            if 'database' in key or 'db' in key:
                return value.replace(match.group(0), '["<db_config>"]')
            elif 'api' in key:
                return value.replace(match.group(0), '["<api_config>"]')
            elif 'env' in key:
                return value.replace(match.group(0), '["<env_var>"]')
            else:
                return value.replace(match.group(0), '["<config_key>"]')
        return value
    
    def _transform_class_instance(self, value: str, context: Dict[str, Any]) -> str:
        """Transform class instance variables."""
        parts = value.split('.')
        if len(parts) >= 2:
            prefix = parts[0]  # self/this
            service_name = parts[1].lower()
            
            if 'database' in service_name or 'db' in service_name:
                return f'{prefix}.<db_service>'
            elif 'user' in service_name:
                return f'{prefix}.<user_service>'
            elif 'cache' in service_name:
                return f'{prefix}.<cache_service>'
            elif 'auth' in service_name:
                return f'{prefix}.<auth_service>'
            else:
                return f'{prefix}.<service>'
        return value
    
    def _transform_function_name(self, value: str, context: Dict[str, Any]) -> str:
        """Transform function names with concrete references."""
        # Pattern: action_entity_suffix
        parts = value.split('_')
        if len(parts) >= 2:
            action = parts[0]
            suffix = '_'.join(parts[-2:]) if len(parts) > 2 and parts[-2] == 'by' else ''
            if suffix:
                return f'{action}_<entity>_{suffix}'
            else:
                return f'{action}_<entity>'
        return value
    
    def _transform_table_name(self, value: str, context: Dict[str, Any]) -> str:
        """Transform database table names."""
        match = re.search(r'\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', value, re.IGNORECASE)
        if match:
            keyword = match.group(1)
            table = match.group(2)
            return f'{keyword} <{table}_table>'
        return value
    
    def _transform_column_names(self, value: str, context: Dict[str, Any]) -> str:
        """Transform database column names."""
        # This is simplified - in practice would need more sophisticated parsing
        if 'SELECT' in value.upper():
            # Replace common column patterns
            value = re.sub(r'\b(\w+_id)\b', '<id_column>', value)
            value = re.sub(r'\bemail\b', '<email_column>', value)
            value = re.sub(r'\b(created_at|updated_at)\b', '<timestamp_column>', value)
            value = re.sub(r'\bname\b', '<name_column>', value)
        return value
    
    def _transform_api_endpoint(self, value: str, context: Dict[str, Any]) -> str:
        """Transform API endpoint paths."""
        # Replace numeric IDs
        value = re.sub(r'/(\d+)(?=/|$)', '/<id>', value)
        # Replace UUIDs
        value = re.sub(r'/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', '/<uuid>', value)
        # Replace other identifiers
        value = re.sub(r'/([a-zA-Z0-9]{6,})(?=/|$)', '/<identifier>', value)
        return value
    
    def get_rules_for_type(self, reference_type: ReferenceType) -> List[AbstractionRule]:
        """Get all rules applicable to a specific reference type."""
        applicable_rules = []
        for category_rules in self.rules.values():
            for rule in category_rules:
                if rule.reference_type == reference_type:
                    applicable_rules.append(rule)
        return applicable_rules
    
    def apply_rules(self, reference: Reference, context: Dict[str, Any]) -> Optional[str]:
        """
        Apply abstraction rules to a reference.
        
        Args:
            reference: The reference to abstract
            context: Additional context
            
        Returns:
            Abstracted value or None if no rule applies
        """
        applicable_rules = self.get_rules_for_type(reference.type)
        
        for rule in applicable_rules:
            if rule.pattern and rule.pattern.search(reference.value):
                if rule.transformer:
                    try:
                        abstracted = rule.transformer(reference.value, context)
                        logger.debug(f"Applied rule '{rule.name}' to abstract '{reference.value}' -> '{abstracted}'")
                        return abstracted
                    except Exception as e:
                        logger.warning(f"Failed to apply rule '{rule.name}': {e}")
        
        return None
    
    def get_examples(self) -> Dict[str, List[tuple[str, str]]]:
        """Get all examples organized by category."""
        examples = {}
        for category, rules in self.rules.items():
            category_examples = []
            for rule in rules:
                if rule.examples:
                    category_examples.extend(rule.examples)
            if category_examples:
                examples[category] = category_examples
        return examples