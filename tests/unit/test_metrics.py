"""Unit tests for metrics collection functionality."""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, call, MagicMock
from fastapi import Request, FastAPI, Response
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from prometheus_client import Histogram

# Import metrics
from src.trustworthiness.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    TRUST_SCORE,
    ERROR_COUNT,
    ACTIVE_REQUESTS,
    MetricsRoute,
    setup_metrics,
    record_trust_score
)

# Create a test histogram with proper bucket configuration
test_histogram = Histogram(
    'test_trustworthiness_score',
    'Test trust score distribution',
    buckets=[0.1, 0.5, 1.0, float('inf')]
)

# Test decorator for async tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    return request

@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.status_code = 200
    return response

@pytest.fixture
def reset_metrics():
    """Fixture to reset metrics before each test."""
    # Clear all metrics
    for metric in [REQUEST_COUNT, REQUEST_LATENCY, TRUST_SCORE, ERROR_COUNT, ACTIVE_REQUESTS]:
        if hasattr(metric, '_metrics'):
            metric._metrics.clear()
        if hasattr(metric, '_buckets'):
            metric._buckets.clear()
        if hasattr(metric, '_sum'):
            metric._sum._value = 0.0
        if hasattr(metric, '_count'):
            metric._count._value = 0
    yield

def test_metrics_route_handler(monkeypatch):
    """Test the custom MetricsRoute handler."""
    # Create a test app with our metrics route
    app = FastAPI()
    
    # Create a mock for the request count
    mock_counter = Mock()
    mock_counter.labels.return_value._value.get.return_value = 1.0
    mock_counter.labels.return_value.inc.return_value = None
    
    # Create a mock for the active requests gauge
    mock_gauge = Mock()
    mock_gauge.labels.return_value.inc.return_value = None
    mock_gauge.labels.return_value.dec.return_value = None
    
    # Create a mock for the request latency histogram
    mock_latency = Mock()
    mock_latency.labels.return_value.observe.return_value = None
    
    # Patch the metrics with our mocks
    with (
        patch('src.trustworthiness.metrics.REQUEST_COUNT', mock_counter), \
        patch('src.trustworthiness.metrics.ACTIVE_REQUESTS', mock_gauge), \
        patch('src.trustworthiness.metrics.REQUEST_LATENCY', mock_latency)
    ):
        # Set up the route with our custom MetricsRoute
        app.router.route_class = MetricsRoute
        
        @app.get("/test")
        async def test_route():
            return {"status": "ok"}
        
        # Use the test client to make requests
        client = TestClient(app)
        
        # Make a request
        with patch('time.time', return_value=1000.0):
            response = client.get("/test")
        
        # Verify the response
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Verify metrics were updated
        mock_counter.labels.assert_called_once_with(
            method="GET", 
            endpoint="/test", 
            http_status=200
        )
        mock_counter.labels().inc.assert_called_once()
        
        # Verify active requests gauge was updated
        # Get all calls to mock_gauge.labels
        label_calls = mock_gauge.labels.mock_calls
        
        # Check that labels was called with the right arguments
        assert label_calls[0] == call(method="GET", endpoint="/test")
        assert label_calls[2] == call(method="GET", endpoint="/test")  # Skip the .inc() call
        
        # Verify inc and dec were called
        mock_gauge.labels().inc.assert_called_once()
        mock_gauge.labels().dec.assert_called_once()
        
        # Verify latency was recorded
        mock_latency.labels.assert_called_once_with(
            method="GET",
            endpoint="/test"
        )

async def test_metrics_route_handler_error():
    """Test error handling in MetricsRoute handler."""
    # Create a test app with an error route
    app = FastAPI()
    
    # Create a mock for the error counter
    mock_error_counter = Mock()
    mock_error_counter.labels.return_value._value.get.return_value = 1.0
    
    # Patch the ERROR_COUNT with our mock
    with patch('src.trustworthiness.metrics.ERROR_COUNT', mock_error_counter):
        # Set up the route with our custom MetricsRoute
        app.router.route_class = MetricsRoute
        
        @app.get("/test")
        async def error_route():
            raise ValueError("Test error")
        
        # Use the test client to make requests
        client = TestClient(app)
        
        # Make a request that will cause an error
        with patch('time.time', side_effect=[1000.0, 1000.5]):
            with pytest.raises(ValueError):
                client.get("/test")
        
        # Verify error was recorded
        mock_error_counter.labels.assert_called_once_with(
            method="GET",
            endpoint="/test",
            error_type="ValueError"
        )

def test_setup_metrics():
    """Test the setup_metrics function."""
    app = FastAPI()
    app = setup_metrics(app)
    
    # Verify the metrics endpoint was added
    assert any(route.path == "/metrics" for route in app.routes)
    
    # Verify the route class was set
    assert app.router.route_class.__name__ == "MetricsRoute"

def test_record_trust_score():
    """Test recording a trust score."""
    # Create a mock for the histogram
    mock_hist = Mock()
    
    # Patch the TRUST_SCORE with our mock
    with patch('src.trustworthiness.metrics.TRUST_SCORE', mock_hist):
        # Call the function with test values
        record_trust_score(0.3)
        record_trust_score(0.8)
        
        # Verify the histogram was called with the correct values
        assert mock_hist.observe.call_count == 2
        mock_hist.observe.assert_any_call(0.3)
        mock_hist.observe.assert_any_call(0.8)

def test_metrics_endpoint():
    """Test the /metrics endpoint."""
    # Create a test app
    app = FastAPI()
    
    # Setup metrics with our app
    app = setup_metrics(app)
    
    # Create a test client
    client = TestClient(app)
    
    # Call the metrics endpoint
    response = client.get("/metrics")
    
    # Verify the response
    assert response.status_code == 200
    response_text = response.text
    
    # Check for expected metrics in the response
    assert "trustworthiness_requests_total" in response_text
    assert "trustworthiness_request_duration_seconds" in response_text
    assert "trustworthiness_score" in response_text
    assert "trustworthiness_active_requests" in response_text
    assert "trustworthiness_errors_total" in response_text
