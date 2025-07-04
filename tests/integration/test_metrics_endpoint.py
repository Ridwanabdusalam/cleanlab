"""Integration tests for metrics endpoint."""
import pytest

# Skip tests if required modules are not available
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.trustworthiness.metrics import get_metrics_router
    METRICS_MODULES_AVAILABLE = True
except ImportError:
    METRICS_MODULES_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not METRICS_MODULES_AVAILABLE,
    reason="Metrics modules not available"
)

def create_test_app():
    """Create a test FastAPI app with metrics endpoint."""
    app = FastAPI()
    app.include_router(get_metrics_router())
    
    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}
        
    return app

def test_metrics_endpoint():
    """Test that the metrics endpoint returns Prometheus data."""
    app = create_test_app()
    client = TestClient(app)
    
    # Make a request to generate some metrics
    client.get("/test")
    
    # Check metrics endpoint
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "trustworthiness_requests_total" in response.text
    assert "trustworthiness_request_duration_seconds" in response.text
