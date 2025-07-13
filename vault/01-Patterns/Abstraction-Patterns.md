# 🔄 Abstraction Patterns

## Common Patterns

### File Paths
```
Original: /home/user/project/src/main.py
Abstract: <user_home>/project/src/main.py

Original: /var/log/application.log
Abstract: <log_directory>/application.log
```

### Database References
```
Original: postgresql://user:pass@localhost:5432/mydb
Abstract: <database_connection_string>

Original: users table, products table
Abstract: <users_table>, <products_table>
```

### API References
```
Original: /api/v1/users/12345
Abstract: /api/v1/users/<id>

Original: X-API-Key: abc123def456
Abstract: X-API-Key: <api_key>
```

### Variable Names
```
Original: current_user.id
Abstract: <user_reference>.id

Original: config["database_url"]
Abstract: config["<db_config>"]
```

### Cloud Resources
```
Original: arn:aws:s3:::my-bucket
Abstract: arn:aws:<service>:<region>:<account>:<resource>

Original: /subscriptions/12345/resourceGroups/mygroup/
Abstract: /subscriptions/<subscription_id>/resourceGroups/<resource_group>/
```

## Pattern Rules
1. **Semantic Preservation**: Abstractions maintain meaning
2. **Consistency**: Similar items get similar abstractions
3. **Specificity**: Use specific placeholders when possible
4. **Readability**: Abstractions should be human-readable

## Quality Dimensions
- **Specificity**: How well abstraction captures type
- **Consistency**: Uniform patterns for similar items
- **Completeness**: All concrete references abstracted
- **Semantic**: Meaning preserved through abstraction
- **Efficiency**: Minimal processing overhead
- **Maintainability**: Clear, understandable patterns