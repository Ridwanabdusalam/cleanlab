"""
Prometheus metrics collection for the Trustworthiness Detector API.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from fastapi.routing import APIRoute
import time

# Request metrics
REQUEST_COUNT = Counter(
    'trustworthiness_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'http_status']
)

REQUEST_LATENCY = Histogram(
    'trustworthiness_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

# Business metrics
TRUST_SCORE = Histogram(
    'trustworthiness_score',
    'Distribution of trust scores',
    buckets=(0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
)

# System metrics
ACTIVE_REQUESTS = Gauge(
    'trustworthiness_active_requests',
    'Number of active requests',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'trustworthiness_errors_total',
    'Total number of errors',
    ['method', 'endpoint', 'error_type']
)

class MetricsRoute(APIRoute):
    """Custom route class to collect metrics for each endpoint."""
    
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request):
            method = request.method
            endpoint = request.url.path
            
            # Track active requests
            ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).inc()
            
            # Measure request latency
            start_time = time.time()
            response = None
            
            try:
                # Process the request
                response = await original_route_handler(request)
                
                # Record metrics
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
                REQUEST_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    http_status=response.status_code
                ).inc()
                
                return response
                
            except Exception as e:
                # Record error metrics
                ERROR_COUNT.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=type(e).__name__
                ).inc()
                raise
                
            finally:
                # Decrement active requests counter
                ACTIVE_REQUESTS.labels(method=method, endpoint=endpoint).dec()
        
        return custom_route_handler

def setup_metrics(app):
    """Set up metrics collection for the FastAPI application."""
    
    # Add metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    # Add startup event to log metrics initialization
    @app.on_event("startup")
    async def startup_event():
        app.state.metrics_initialized = True
    
    # Use custom route class for all routes
    app.router.route_class = MetricsRoute
    
    return app

def record_trust_score(score: float):
    """Record a trust score metric."""
    TRUST_SCORE.observe(score)
