"""Shared test fixtures and configuration."""
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch
from dotenv import load_dotenv

# Set test environment variables before importing any application code
os.environ.update({
    "GEMINI_API_KEY": "dummy-gemini-key",
    "API_KEY": "test-key",
    "API_SECRET": "test-secret",
    "REQUEST_SIGNING_MAX_AGE": "300",
    "TESTING": "true"
})

# Now import application code
from src.trustworthiness.detector import TrustworthinessDetector
from src.trustworthiness.security.request_signing import RequestSigner

@pytest.fixture
def mock_scoring_function():
    """Mock scoring function for testing."""
    async def scoring_fn(question, answer, **kwargs):
        return 0.8  # Default mock score
    return scoring_fn

@pytest.fixture
def detector():
    """Create a TrustworthinessDetector instance for testing."""
    return TrustworthinessDetector(
        default_scoring_fn="test",
        max_concurrent=10,
        max_cache_size=100,
        cache_ttl=300,
        circuit_breaker_failures=2,
        circuit_breaker_timeout=1
    )

@pytest.fixture
def app():
    """Create a FastAPI app instance for testing."""
    from fastapi import FastAPI
    from src.trustworthiness.api import router
    
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    return TestClient(app)

# Mock RequestSigner for testing
class MockRequestSigner:
    def __init__(self, *args, **kwargs):
        self.api_key = kwargs.get('api_key', 'test-key')
        self.api_secret = kwargs.get('api_secret', 'test-secret')
        self.timestamp_header = "X-API-Timestamp"
        self.signature_header = "X-API-Signature"
        self.key_header = "X-API-Key"
        self.max_age = 300
    
    def sign_request(self, method, path, body=None, timestamp=None, headers=None):
        return {
            self.key_header: self.api_key,
            self.timestamp_header: str(timestamp or 1234567890),
            self.signature_header: "mocked-signature"
        }
    
    async def verify_request(self, request):
        """Mock verify_request that checks for required headers."""
        # Debug: Log all request headers
        print("\n=== Request Headers ===")
        for k, v in request.headers.items():
            print(f"{k}: {v}")
        print("====================\n")
        
        # Check if required headers are present
        required_headers = [
            self.key_header,
            self.timestamp_header,
            self.signature_header
        ]
        
        missing_headers = [
            header for header in required_headers 
            if header not in request.headers
        ]
        
        if missing_headers:
            from fastapi import HTTPException, status
            print(f"Missing required headers: {missing_headers}")
            print(f"All headers: {dict(request.headers)}")
            
            # Create and raise the exception
            exc = HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required headers: {', '.join(missing_headers)}"
            )
            print(f"Raising exception: {exc}")
            raise exc
            
        print("Request verification successful")
        return True

        # In a real test, we might want to verify the signature
        # But for testing, we'll just check the API key
        if request.headers.get(self.key_header) != self.api_key:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
            
        return True

@pytest.fixture(autouse=True)
def mock_security(monkeypatch):
    """Mock security components for testing."""
    # Patch the RequestSigner with our mock
    monkeypatch.setattr("src.trustworthiness.security.request_signing.RequestSigner", MockRequestSigner)
    
    # Mock the get_request_signer function
    def mock_get_signer():
        return MockRequestSigner()
    
    monkeypatch.setattr(
        "src.trustworthiness.security.request_signing.get_request_signer",
        mock_get_signer
    )
    
    # Mock the SecurityMiddleware to use our test signer
    monkeypatch.setattr(
        "src.trustworthiness.security.middleware.get_request_signer",
        mock_get_signer
    )
