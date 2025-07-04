"""
Input sanitization utilities to prevent injection attacks.
"""

import re
import html
from typing import Any, Dict, List, Union, Optional


class Sanitizer:
    """Sanitizes input to prevent XSS and injection attacks."""

    # Common XSS patterns to block
    XSS_PATTERNS = [
        (r'<script.*?>.*?</script>', ''),
        (r'javascript:', ''),
        (r'data:', ''),
        (r'vbscript:', ''),
        (r'expression\(', ''),
        (r'eval\(', ''),
        (r'document\.', ''),
        (r'window\.', ''),
        (r'on\w+\s*=', ''),
    ]

    # HTML tags to allow (all others will be escaped)
    ALLOWED_TAGS = {
        'b', 'i', 'em', 'strong', 'code', 'pre', 'br', 'p', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'blockquote', 'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div', 'span'
    }

    # HTML attributes to allow
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'div': ['class'],
        'span': ['class'],
        'p': ['class'],
        'code': ['class'],
        'pre': ['class'],
    }

    @classmethod
    def sanitize_string(
        cls,
        value: str,
        max_length: int = 10000,
        allow_html: bool = False
    ) -> str:
        """Sanitize a string to prevent XSS and injection attacks.

        Args:
            value: The string to sanitize
            max_length: Maximum allowed length of the string
            allow_html: Whether to allow HTML tags (with restrictions)

        Returns:
            Sanitized string
        """
        if not value:
            return value

        # Truncate to max length
        value = str(value)[:max_length]

        if not allow_html:
            # Escape HTML and remove all HTML tags
            value = html.escape(value)
            
            # Remove any remaining HTML tags that might have been missed
            value = re.sub(r'<[^>]*>', '', value)
        else:
            # Use a more permissive sanitizer for HTML content
            value = cls._sanitize_html(value)

        # Apply XSS patterns
        for pattern, repl in cls.XSS_PATTERNS:
            value = re.sub(pattern, repl, value, flags=re.IGNORECASE | re.DOTALL)

        return value

    @classmethod
    def _sanitize_html(cls, value: str) -> str:
        """Sanitize HTML content while allowing safe tags and attributes."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(value, 'html.parser')
        
        for tag in soup.find_all(True):
            # Remove disallowed tags
            if tag.name not in cls.ALLOWED_TAGS:
                tag.unwrap()
                continue
                
            # Remove disallowed attributes
            allowed_attrs = cls.ALLOWED_ATTRIBUTES.get(tag.name, {})
            attrs = dict(tag.attrs)
            tag.attrs = {}
            
            for attr, val in attrs.items():
                if attr in allowed_attrs:
                    # Additional validation for specific attributes
                    if attr == 'href':
                        if not val.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                            continue
                    tag.attrs[attr] = val
        
        return str(soup)

    @classmethod
    def sanitize_dict(
        cls,
        data: Dict[str, Any],
        max_length: int = 10000,
        allow_html: bool = False
    ) -> Dict[str, Any]:
        """Recursively sanitize all string values in a dictionary.
        
        Args:
            data: Dictionary to sanitize
            max_length: Maximum allowed length for string values
            allow_html: Whether to allow HTML tags in string values
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value, max_length, allow_html)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_length, allow_html)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(v, max_length, allow_html) if isinstance(v, dict)
                    else cls.sanitize_string(v, max_length, allow_html) if isinstance(v, str)
                    else v for v in value
                ]
            else:
                sanitized[key] = value
                
        return sanitized


def sanitize_input(
    data: Any,
    max_length: int = 10000,
    allow_html: bool = False
) -> Any:
    """Sanitize input data to prevent XSS and injection attacks.
    
    Args:
        data: Data to sanitize (str, dict, or list)
        max_length: Maximum allowed length for string values
        allow_html: Whether to allow HTML tags in string values
        
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        return Sanitizer.sanitize_string(data, max_length, allow_html)
    elif isinstance(data, dict):
        return Sanitizer.sanitize_dict(data, max_length, allow_html)
    elif isinstance(data, list):
        return [
            sanitize_input(item, max_length, allow_html)
            for item in data
        ]
    return data
