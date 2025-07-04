"""
Security-related data models for the Trustworthiness Detector.
"""
from datetime import datetime
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum

class SecurityLevel(str, Enum):
    """Security level for API access and operations."""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    PRIVILEGED = "privileged"
    ADMIN = "admin"

class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    requests: int = Field(..., gt=0, description="Number of requests allowed")
    window_seconds: int = Field(..., gt=0, description="Time window in seconds")

class APIAccessToken(BaseModel):
    """API access token for authentication."""
    token: str = Field(..., min_length=32, description="The access token")
    name: str = Field(..., description="Name/description of the token")
    level: SecurityLevel = Field(default=SecurityLevel.AUTHENTICATED, 
                              description="Access level of the token")
    rate_limit: RateLimitConfig = Field(
        default_factory=lambda: RateLimitConfig(requests=100, window_seconds=60),
        description="Rate limiting configuration"
    )
    expires_at: Optional[float] = Field(
        None, 
        description="Expiration timestamp (unix time), None means never expires"
    )
    created_at: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="Creation timestamp (unix time)"
    )

    @field_validator('token')
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Validate token format."""
        if not v.isalnum():
            raise ValueError("Token must be alphanumeric")
        return v

class AuditLogEntry(BaseModel):
    """Entry in the audit log."""
    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="When the event occurred (unix time)"
    )
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource that was accessed")
    user: Optional[str] = Field(None, description="User who performed the action")
    ip_address: Optional[str] = Field(None, description="IP address of the client")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional context about the event"
    )
    success: bool = Field(True, description="Whether the action was successful")
