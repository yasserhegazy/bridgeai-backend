import re
import html
from typing import Optional

def sanitize_string(value: Optional[str], max_length: int = 1000) -> Optional[str]:
    """Sanitize string input to prevent XSS attacks."""
    if value is None:
        return None
    
    # Trim whitespace
    value = value.strip()
    
    # Enforce max length
    if len(value) > max_length:
        value = value[:max_length]
    
    # Escape HTML entities
    value = html.escape(value)
    
    return value

def validate_no_sql_keywords(value: str) -> bool:
    """Check for common SQL injection patterns."""
    sql_patterns = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(--)",
        r"(;.*\bDROP\b)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(\bSCRIPT\b.*>)",
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return False
    return True

def validate_alphanumeric_with_spaces(value: str, allow_special: str = "") -> bool:
    """Validate string contains only alphanumeric characters, spaces, and allowed special chars."""
    pattern = f"^[a-zA-Z0-9\\s{re.escape(allow_special)}]+$"
    return bool(re.match(pattern, value))

def validate_name(value: str) -> str:
    """Validate and sanitize name fields."""
    if not value or not value.strip():
        raise ValueError("Name cannot be empty")
    
    value = sanitize_string(value, max_length=256)
    
    if not validate_no_sql_keywords(value):
        raise ValueError("Invalid characters detected")
    
    return value

def validate_description(value: Optional[str]) -> Optional[str]:
    """Validate and sanitize description fields."""
    if value is None:
        return None
    
    value = sanitize_string(value, max_length=2000)
    
    if not validate_no_sql_keywords(value):
        raise ValueError("Invalid characters detected")
    
    return value

def validate_email_format(email: str) -> bool:
    """Validate email format with strict pattern."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254
