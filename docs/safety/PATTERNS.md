# 🔄 Cognitive Coding Partner: Abstraction Pattern Catalog

---
**Document**: Abstraction Patterns and Templates  
**Version**: 1.0  
**Date**: 2025-01-13  
**Purpose**: Comprehensive catalog of abstraction patterns for all reference types  
**Usage**: Reference guide for implementing abstraction in CCP components  

---

## 📋 Pattern Overview

This catalog defines standard abstraction patterns for converting concrete references into safe, reusable abstractions. Each pattern includes detection rules, transformation templates, and validation criteria.

## 🗂️ Pattern Categories

### 1. File System Patterns
Abstractions for file paths, directories, and file operations.

### 2. Identifier Patterns  
Abstractions for IDs, keys, tokens, and unique identifiers.

### 3. Network Patterns
Abstractions for URLs, endpoints, hostnames, and network resources.

### 4. Container Patterns
Abstractions for Docker containers, Kubernetes pods, and service names.

### 5. Configuration Patterns
Abstractions for environment variables, config values, and settings.

### 6. Temporal Patterns
Abstractions for timestamps, dates, and time-based references.

---

## 📁 File System Patterns

### Pattern: Absolute Path Abstraction
**Detects**: Absolute file paths starting with `/` or drive letters  
**Transforms**: To relative paths with semantic placeholders

#### Examples:
```python
# Input → Output
"/home/user/projects/myapp/src/main.py" → "<project_root>/src/main.py"
"/usr/local/lib/python3.9/site-packages/" → "<python_packages>/"
"C:\\Users\\John\\Documents\\project\\config.json" → "<project_root>/config.json"
"/etc/nginx/sites-enabled/myapp" → "<nginx_config>/myapp"
"/var/log/application/error.log" → "<log_directory>/error.log"
```

#### Detection Regex:
```python
ABSOLUTE_PATH_PATTERNS = [
    r'^/[a-zA-Z0-9/_.\-]+',  # Unix absolute paths
    r'^[A-Z]:\\',             # Windows paths
    r'^\\\\',                 # UNC paths
]
```

#### Transformation Rules:
1. Identify semantic root (project, home, system)
2. Replace with appropriate placeholder
3. Preserve relative structure
4. Maintain file extensions

### Pattern: User Directory Abstraction
**Detects**: User-specific directory references  
**Transforms**: To generic user placeholders

#### Examples:
```python
# Input → Output
"/home/alice/documents/" → "<user_home>/documents/"
"/Users/bob/Desktop/" → "<user_home>/Desktop/"
"~/.config/myapp/" → "<user_config>/myapp/"
"$HOME/.ssh/id_rsa" → "<user_home>/.ssh/id_rsa"
```

### Pattern: Temporary Path Abstraction
**Detects**: Temporary file and directory paths  
**Transforms**: To generic temporary placeholders

#### Examples:
```python
# Input → Output
"/tmp/build-12345/" → "<temp_dir>/build-*/"
"/var/tmp/cache_abcd/" → "<temp_cache>/*/"
"C:\\Temp\\processing_567.tmp" → "<temp_dir>/processing_*.tmp"
```

---

## 🔑 Identifier Patterns

### Pattern: Numeric ID Abstraction
**Detects**: Numeric identifiers in code  
**Transforms**: To semantic type placeholders

#### Examples:
```python
# Input → Output
"user_id = 12345" → "user_id = <user_id>"
"order.id == 98765" → "order.id == <order_id>"
"DELETE FROM posts WHERE id = 456" → "DELETE FROM posts WHERE id = <post_id>"
"customer_ids = [111, 222, 333]" → "customer_ids = [<customer_id>, ...]"
```

#### Context-Aware Detection:
```python
ID_CONTEXTS = {
    'user_id': '<user_id>',
    'order_id': '<order_id>',
    'product_id': '<product_id>',
    'session_id': '<session_id>',
    'transaction_id': '<transaction_id>',
}
```

### Pattern: UUID Abstraction
**Detects**: UUID format strings  
**Transforms**: To typed UUID placeholders

#### Examples:
```python
# Input → Output
"id = 'a4d7e9f2-8b3c-4e6d-9f2a-1b3c5d7e9f2a'" → "id = '<uuid>'"
"session = '550e8400-e29b-41d4-a716-446655440000'" → "session = '<session_uuid>'"
```

### Pattern: Token/Secret Abstraction
**Detects**: Authentication tokens, API keys, secrets  
**Transforms**: To security placeholders

#### Examples:
```python
# Input → Output
"api_key = 'sk_live_abcd1234...'" → "api_key = '<api_key>'"
"token = 'eyJhbGciOiJIUzI1NiIs...'" → "token = '<jwt_token>'"
"password = 'SuperSecret123!'" → "password = '<password>'"
"AWS_SECRET_KEY = 'wJalrXUtnFEMI...'" → "AWS_SECRET_KEY = '<aws_secret>'"
```

---

## 🌐 Network Patterns

### Pattern: URL Abstraction
**Detects**: HTTP/HTTPS URLs  
**Transforms**: To service-based placeholders

#### Examples:
```python
# Input → Output
"https://api.example.com/v1/users/123" → "<api_base_url>/users/<user_id>"
"http://localhost:8080/debug" → "<local_service>/debug"
"https://staging.myapp.com/auth/login" → "<staging_url>/auth/login"
"postgresql://user:pass@db.example.com:5432/mydb" → "<database_url>"
```

#### URL Components:
```python
URL_ABSTRACTIONS = {
    'protocol': {'http://', 'https://', 'ftp://', 'ssh://'},
    'localhost': '<local_service>',
    'staging': '<staging_url>',
    'production': '<prod_url>',
    'api': '<api_base_url>',
}
```

### Pattern: IP Address Abstraction
**Detects**: IPv4 and IPv6 addresses  
**Transforms**: To network placeholders

#### Examples:
```python
# Input → Output
"192.168.1.100" → "<local_ip>"
"10.0.0.5" → "<private_ip>"
"8.8.8.8" → "<public_dns>"
"2001:0db8:85a3::8a2e:0370:7334" → "<ipv6_address>"
```

### Pattern: Port Abstraction
**Detects**: Network ports in configurations  
**Transforms**: To service type placeholders

#### Examples:
```python
# Input → Output
"localhost:3000" → "localhost:<app_port>"
"0.0.0.0:8080" → "0.0.0.0:<http_port>"
"db.example.com:5432" → "db.example.com:<postgres_port>"
```

---

## 🐳 Container Patterns

### Pattern: Container Name Abstraction
**Detects**: Docker container names and IDs  
**Transforms**: To service-based placeholders

#### Examples:
```python
# Input → Output
"myapp-web-prod-v1.2.3" → "<app_container>"
"redis-cache-5f4dcc3b" → "<redis_container>"
"nginx-proxy-staging" → "<proxy_container>"
"64d6f7439c8a" → "<container_id>"
```

### Pattern: Image Tag Abstraction
**Detects**: Docker image names with tags  
**Transforms**: To versioned placeholders

#### Examples:
```python
# Input → Output
"myapp/web:1.2.3" → "myapp/web:<version>"
"postgres:13.4-alpine" → "postgres:<postgres_version>-alpine"
"node:16-slim" → "node:<node_version>-slim"
```

### Pattern: Kubernetes Resource Abstraction
**Detects**: K8s resource names  
**Transforms**: To resource type placeholders

#### Examples:
```python
# Input → Output
"deployment/myapp-web-prod" → "deployment/<app_deployment>"
"pod/myapp-web-7d4b9c8f5-x2n4m" → "pod/<app_pod>"
"service/myapp-api" → "service/<api_service>"
```

---

## ⚙️ Configuration Patterns

### Pattern: Environment Variable Abstraction
**Detects**: Environment variable values  
**Transforms**: To configuration placeholders

#### Examples:
```python
# Input → Output
"DATABASE_URL=postgres://..." → "DATABASE_URL=<database_url>"
"API_KEY=sk_live_..." → "API_KEY=<api_key>"
"NODE_ENV=production" → "NODE_ENV=<environment>"
"DEBUG=true" → "DEBUG=<debug_flag>"
```

### Pattern: Configuration Value Abstraction
**Detects**: Configuration file values  
**Transforms**: To setting placeholders

#### Examples:
```yaml
# Input → Output
host: "db.production.example.com" → host: "<database_host>"
port: 5432 → port: <database_port>
max_connections: 100 → max_connections: <connection_limit>
cache_ttl: 3600 → cache_ttl: <cache_duration>
```

---

## ⏰ Temporal Patterns

### Pattern: Timestamp Abstraction
**Detects**: Timestamps and dates  
**Transforms**: To temporal placeholders

#### Examples:
```python
# Input → Output
"2024-01-15T10:30:00Z" → "<timestamp>"
"created_at = '2024-01-15'" → "created_at = '<date>'"
"expires = 1642248600" → "expires = <unix_timestamp>"
"last_modified: 'Mon, 15 Jan 2024'" → "last_modified: '<http_date>'"
```

### Pattern: Duration Abstraction
**Detects**: Time durations and intervals  
**Transforms**: To duration placeholders

#### Examples:
```python
# Input → Output
"timeout = 30" → "timeout = <timeout_seconds>"
"cache_for = '1 hour'" → "cache_for = '<cache_duration>'"
"retry_after = 5000" → "retry_after = <retry_delay_ms>"
```

---

## 🔧 Implementation Guide

### Abstraction Engine Structure
```python
class AbstractionEngine:
    def __init__(self):
        self.patterns = self._load_patterns()
        self.validators = self._load_validators()
    
    def abstract(self, content: str, context: Dict) -> AbstractionResult:
        # 1. Detect reference type
        references = self.detect_references(content)
        
        # 2. Apply appropriate pattern
        abstractions = []
        for ref in references:
            pattern = self.patterns.get_pattern(ref.type)
            abstraction = pattern.transform(ref, context)
            abstractions.append(abstraction)
        
        # 3. Validate abstractions
        validation = self.validate_abstractions(abstractions)
        
        return AbstractionResult(
            original=content,
            abstracted=self.apply_abstractions(content, abstractions),
            mappings=abstractions,
            validation=validation
        )
```

### Pattern Matching Priority
1. **Exact Match**: Specific patterns (e.g., known API endpoints)
2. **Context Match**: Based on variable names and usage
3. **Format Match**: Based on data format (UUID, URL, etc.)
4. **Heuristic Match**: Best guess based on structure

### Validation Rules
Each abstraction must:
1. Preserve semantic meaning
2. Be reversible (can map back to type)
3. Not lose critical information
4. Be consistent across similar references
5. Pass safety score threshold (≥ 0.8)

---

## 📊 Pattern Metrics

### Quality Indicators
- **Coverage**: Percentage of references abstracted
- **Accuracy**: Correct pattern selection rate
- **Consistency**: Same reference → same abstraction
- **Reversibility**: Can determine original type
- **Safety Score**: Abstraction quality rating

### Pattern Evolution
Patterns should be:
1. Reviewed monthly
2. Updated based on new reference types
3. Tested against real data
4. Validated by security team
5. Documented with examples

---

## 🚨 Anti-Patterns

### ❌ Over-Abstraction
```python
# Too abstract - loses meaning
"SELECT * FROM users WHERE age > 18" → "SELECT * FROM <table> WHERE <column> > <value>"

# Better - preserves intent
"SELECT * FROM users WHERE age > 18" → "SELECT * FROM users WHERE age > <min_age>"
```

### ❌ Under-Abstraction  
```python
# Not abstracted enough
"/home/john/project/src/" → "/home/<username>/project/src/"

# Better - fully abstracted
"/home/john/project/src/" → "<project_root>/src/"
```

### ❌ Inconsistent Abstraction
```python
# Inconsistent - same type, different abstractions
"user_id = 123" → "user_id = <id>"
"user_id = 456" → "user_id = <user_identifier>"

# Better - consistent
"user_id = 123" → "user_id = <user_id>"
"user_id = 456" → "user_id = <user_id>"
```

---

## 🔍 Testing Patterns

Each pattern should have:
1. **Unit tests** for detection regex
2. **Integration tests** for transformation
3. **Edge case tests** for unusual formats
4. **Performance tests** for large content
5. **Validation tests** for safety scoring

Example test:
```python
def test_file_path_abstraction():
    engine = AbstractionEngine()
    
    test_cases = [
        ("/home/user/app/main.py", "<project_root>/main.py"),
        ("C:\\Projects\\MyApp\\config.json", "<project_root>/config.json"),
        ("/tmp/cache_12345/", "<temp_dir>/cache_*/"),
    ]
    
    for input_path, expected in test_cases:
        result = engine.abstract(input_path, context={'type': 'file_path'})
        assert result.abstracted == expected
        assert result.validation.score >= 0.8
```

---

*This catalog is a living document. Submit new patterns via pull request with examples and tests.*