"""
Central configuration for the trustworthiness detector.
All model and API settings are managed here.
"""

import re
from typing import Tuple

import requests
from dotenv import load_dotenv
from pydantic import Field, HttpUrl, validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation."""

    # API Authentication
    API_KEY: str = Field(..., env="API_KEY")
    API_SECRET: str = Field(..., env="API_SECRET")
    REQUEST_SIGNING_MAX_AGE: int = Field(300, env="REQUEST_SIGNING_MAX_AGE")  # 5 minutes

    # Gemini API Configuration
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_API_URL: HttpUrl = Field(
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent",
        env="GEMINI_API_URL",
    )
    DEFAULT_MODEL: str = Field("gemini-1.5-pro", env="DEFAULT_MODEL")

    # Rate limiting configuration
    RATE_LIMIT_MAX_REQUESTS: int = Field(15, env="RATE_LIMIT_MAX_REQUESTS")
    RATE_LIMIT_TIME_WINDOW: int = Field(60, env="RATE_LIMIT_TIME_WINDOW")
    RATE_LIMIT_JITTER: float = Field(0.1, env="RATE_LIMIT_JITTER")
    RATE_LIMIT_MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("GEMINI_API_KEY")
    def validate_api_key(cls, v: str) -> str:
        if not v or not re.match(r"^[A-Za-z0-9-_]+$", v):
            raise ValueError("Invalid API key format")
        return v


# Initialize settings
try:
    settings = Settings()
except Exception as e:
    print(f"Error loading configuration: {e}")
    raise


# Backward compatibility
def validate_model_api_key() -> Tuple[bool, str]:
    """Check if the Gemini API key is set and valid.

    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if the API key is valid, False otherwise
            - str: Status message or error description
    """
    try:
        # Test the API key with a simple request
        response = requests.post(
            f"{settings.GEMINI_API_URL}?key={settings.GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generationConfig": {"maxOutputTokens": 10},
            },
            timeout=10,
        )

        if response.status_code == 200:
            return True, "API key validated"
        else:
            return (
                False,
                (
                    f"API key validation failed with status {response.status_code}: "
                    f"{response.text}"
                ),
            )

    except Exception as e:
        return False, f"Error validating API key: {str(e)}"
