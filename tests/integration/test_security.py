"""Integration tests for security features."""
import os
import sys
import pytest
from fastapi import FastAPI, status, HTTPException
from fastapi.testclient import TestClient
from trustworthiness.security.middleware import SecurityMiddleware
from trustworthiness.security.request_signing import RequestSigner, get_request_signer

# Set all required environment variables before any imports
os.environ.update({
    "GEMINI_API_KEY": "dummy-gemini-key",
    "API_KEY": "test-key",
    "API_SECRET": "test-secret",
    "REQUEST_SIGNING_MAX_AGE": "300"
})

# Add src to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

pytestmark = pytest.mark.skipif(
    not all(k in os.environ for k in ["API_KEY", "API_SECRET"]),
    reason="Missing required environment variables for security tests"
)

@pytest.fixture
def test_app(mock_security):
    """Create a test FastAPI app with security middleware."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    # Apply security middleware with testing configuration
    app.add_middleware(
        SecurityMiddleware,
        enable_request_signing=True,
        enable_rate_limiting=False,  # Disable rate limiting for tests
        enable_cors=False,  # Disable CORS for tests
        enable_security_headers=False  # Disable security headers for tests
    )
    
    return app

def test_request_signing(test_app):
    """Test that requests with valid signatures are accepted."""
    client = TestClient(test_app)
    
    # Get the mock signer that was set up in conftest.py
    signer = get_request_signer()
    
    # Sign a test request using the mock signer
    headers = signer.sign_request("GET", "/test")
    
    # Make the request with the signed headers
    response = client.get("/test", headers=headers)
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.fixture
def test_app_with_signing():
    """Create a test FastAPI app with just the request signing middleware."""
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
    
    # Apply only the request signing middleware
    from trustworthiness.security.middleware import RequestSigningMiddleware
    app.add_middleware(RequestSigningMiddleware)
    
    return app

def test_unsigned_request_rejected(test_app_with_signing):
    """Test that requests without valid signatures are rejected."""
    # Create a test client that raises exceptions
    client = TestClient(test_app_with_signing)
    
    # Make a request without any authentication headers
    print("\n=== Sending request to /test without any headers ===")
    
    # We expect this to raise an HTTPException with status_code=400
    with pytest.raises(HTTPException) as exc_info:
        client.get("/test")
    
    # Verify the exception has the correct status code
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST, \
        f"Expected status code 400, got {exc_info.value.status_code}"
    
    # Verify the error message
    assert "Missing required headers" in str(exc_info.value.detail), \
        f"Unexpected error message: {exc_info.value.detail}"
    
    print("\n=== Test Passed Successfully ===")
