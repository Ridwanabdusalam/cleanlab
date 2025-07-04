"""
API configuration settings.
"""
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENV: str = os.getenv("ENV", "development")
    
    # Security
    ENABLE_AUTHENTICATION: bool = os.getenv("ENABLE_AUTHENTICATION", "false").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 15
    SECURE_COOKIES: bool = os.getenv("SECURE_COOKIES", "true").lower() == "true"
    SESSION_COOKIE_NAME: str = "trust_detector_session"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE: str = "lax"
    CSRF_PROTECTION: bool = os.getenv("CSRF_PROTECTION", "true").lower() == "true"
    
    # CORS
    ALLOWED_ORIGINS: list = Field(
        default_factory=lambda: os.getenv(
            "ALLOWED_ORIGINS", 
            "http://localhost:3000,http://localhost:8000"
        ).split(","),
        description="List of allowed origins for CORS"
    )
    CORS_METHODS: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS: list = ["Content-Type", "Authorization", "X-Requested-With"]
    CORS_MAX_AGE: int = 600  # 10 minutes
    
    # Rate limiting
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    rate_limit_max_requests: int = 15
    rate_limit_time_window: int = 60
    rate_limit_jitter: float = 0.1
    
    # Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_api_url: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # Trustworthiness settings
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemini-pro")
    TRUST_THRESHOLD: float = float(os.getenv("TRUST_THRESHOLD", "0.8"))
    WARNING_THRESHOLD: float = float(os.getenv("WARNING_THRESHOLD", "0.6"))
    
    # Feature flags
    ENABLE_REQUEST_SIGNING: bool = False
    ENABLE_AUDIT_LOGGING: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create settings instance
settings = Settings()
