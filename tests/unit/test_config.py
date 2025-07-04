"""
Tests for configuration and environment variable handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.trustworthiness.config import Settings, validate_model_api_key


def test_settings_defaults():
    """Test that default values are set correctly in Settings."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
        settings = Settings()

        # Check default values
        assert settings.GEMINI_API_KEY == "test_key"
        assert "generativelanguage.googleapis.com" in str(settings.GEMINI_API_URL)
        assert "gemini" in settings.DEFAULT_MODEL.lower()
        assert settings.RATE_LIMIT_MAX_REQUESTS == 15
        assert settings.RATE_LIMIT_TIME_WINDOW == 60
        assert settings.RATE_LIMIT_JITTER == 0.1
        assert settings.RATE_LIMIT_MAX_RETRIES == 3


def test_settings_validation():
    """Test validation of settings values."""
    # Test invalid API key format
    with pytest.raises(ValueError, match="Invalid API key format"):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "invalid key with spaces"}):
            Settings()

    # Test with valid settings to ensure no exceptions are raised
    with patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "valid_key_123",
            "GEMINI_API_URL": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            "RATE_LIMIT_MAX_REQUESTS": "10",
        },
    ):
        settings = Settings()
        assert settings.GEMINI_API_KEY == "valid_key_123"
        assert settings.RATE_LIMIT_MAX_REQUESTS == 10


@patch("requests.post")
def test_validate_model_api_key_success(mock_post):
    """Test API key validation with a successful response."""
    # Configure mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "test"}]}}]
    }
    mock_post.return_value = mock_response

    # Test with valid settings
    with patch(
        "src.trustworthiness.config.settings",
        Settings(
            GEMINI_API_KEY="test_key", GEMINI_API_URL="https://test-api.example.com"
        ),
    ):

        is_valid, message = validate_model_api_key()

        # Verify results
        assert is_valid is True
        assert "validated" in message.lower()

        # Verify the API was called with the correct parameters
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert "test-api.example.com" in call_args[0]
        assert "test_key" in call_args[0]


@patch("requests.post")
def test_validate_model_api_key_failure(mock_post):
    """Test API key validation with a failed API call."""
    # Configure mock to raise an exception
    mock_post.side_effect = Exception("Connection error")

    # Test with valid settings but API failure
    with patch(
        "src.trustworthiness.config.settings", Settings(GEMINI_API_KEY="test_key")
    ):

        is_valid, message = validate_model_api_key()

        # Verify results
        assert is_valid is False
        assert "error" in message.lower()
