"""
Metrics collection and monitoring for the Trustworthiness Detector API.
"""
import os
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from functools import wraps

from prometheus_client import (
    Counter, 
    Gauge, 
    Histogram, 
    start_http_server,
    REGISTRY,
    generate_latest,
    CollectorRegistry
)
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
import atexit

# Create a custom registry to avoid conflicts with default registry
METRICS_REGISTRY = CollectorRegistry()

# Initialize metrics with unique names to prevent conflicts
REQUEST_COUNT = Counter(
    'trust_detector_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=METRICS_REGISTRY
)

REQUEST_LATENCY = Histogram(
    'trust_detector_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    registry=METRICS_REGISTRY
)

# Trust score metrics
TRUST_SCORE = Gauge(
    'trust_detector_trust_score',
    'Trust score distribution',
    ['score_type'],
    registry=METRICS_REGISTRY
)

# Error metrics
ERROR_COUNT = Counter(
    'trust_detector_errors_total',
    'Total number of errors',
    ['error_type'],
    registry=METRICS_REGISTRY
)

# System metrics
SYSTEM_CPU_USAGE = Gauge(
    'trust_detector_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=METRICS_REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    'trust_detector_system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=METRICS_REGISTRY
)

# Clean up function to unregister metrics when the application shuts down
def _cleanup_metrics():
    """Unregister metrics to prevent duplicate registration on reload."""
    for metric in [
        'trust_detector_http_requests_total',
        'trust_detector_http_request_duration_seconds',
        'trust_detector_trust_score',
        'trust_detector_errors_total',
        'trust_detector_system_cpu_usage_percent',
        'trust_detector_system_memory_usage_bytes'
    ]:
        if metric in METRICS_REGISTRY._names_to_collectors:
            METRICS_REGISTRY.unregister(METRICS_REGISTRY._names_to_collectors[metric])

# Register cleanup function
atexit.register(_cleanup_metrics)

# Custom metrics
CUSTOM_METRICS = {}

def record_metrics(func):
    """
    Decorator to record request metrics.
    
    This should be used to wrap FastAPI route handlers.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request information
        request = None
        endpoint = "unknown"
        method = "unknown"
        
        # Try to get request object from args or kwargs
        for arg in args:
            if hasattr(arg, 'method') and hasattr(arg, 'url'):
                request = arg
                break
        
        if not request and 'request' in kwargs:
            request = kwargs['request']
        
        if request:
            endpoint = request.url.path
            method = request.method
        
        # Record start time
        start_time = time.time()
        
        try:
            # Call the handler
            response = await func(*args, **kwargs)
            
            # Record success
            status_code = getattr(response, 'status_code', 200)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
            
            return response
        except Exception as e:
            # Record error
            error_type = e.__class__.__name__
            ERROR_COUNT.labels(error_type=error_type).inc()
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=500).inc()
            raise
        finally:
            # Record latency
            latency = time.time() - start_time
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    
    return wrapper

def record_trust_score(score: float, score_type: str = "default"):
    """
    Record a trust score metric.
    
    Args:
        score: Trust score between 0 and 1
        score_type: Type of score (e.g., 'default', 'custom')
    """
    TRUST_SCORE.labels(score_type=score_type).set(score)


def record_error(error_type: str):
    """
    Record an error metric.
    
    Args:
        error_type: Type of error
    """
    ERROR_COUNT.labels(error_type=error_type).inc()


def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics.
    
    Returns:
        Dictionary of system metrics
    """
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        # Get process info
        process = psutil.Process()
        
        metrics = {
            'cpu': {
                'percent': cpu_percent,
                'cores': psutil.cpu_count(),
                'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else []
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            },
            'process': {
                'pid': process.pid,
                'memory_info': process.memory_info()._asdict(),
                'cpu_percent': process.cpu_percent(interval=1),
                'threads': process.num_threads()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Update Prometheus metrics if initialized
        _init_metrics()
        if SYSTEM_CPU_USAGE is not None:
            SYSTEM_CPU_USAGE.set(cpu_percent)
        if SYSTEM_MEMORY_USAGE is not None:
            SYSTEM_MEMORY_USAGE.set(memory.used)
            
        return metrics
    except Exception as e:
        # Log the error but don't fail the request
        import logging
        logging.getLogger(__name__).error(f"Error getting system metrics: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def setup_metrics(app, port: int = 8001):
    """
    Set up metrics collection and endpoint.
    
    Args:
        app: FastAPI application
        port: Port to expose metrics on (default: 8001)
    """
    # Try to start the metrics server, but continue if the port is in use
    try:
        start_http_server(port, registry=METRICS_REGISTRY)
        print(f"Metrics server started on port {port}")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"Metrics server port {port} is already in use, using existing server")
        else:
            print(f"Error starting metrics server: {e}")
    
    # Add system metrics collection
    def collect_system_metrics():
        """Collect system metrics."""
        try:
            return get_system_metrics()
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            return {}
    
    # Collect initial metrics
    collect_system_metrics()
    
    # Schedule periodic collection only if not in test environment
    if os.environ.get('TESTING') != 'true':
        import threading
        from time import sleep
        
        def collect_metrics_loop():
            while True:
                try:
                    collect_system_metrics()
                except Exception as e:
                    print(f"Error in metrics collection loop: {e}")
                sleep(15)  # Collect every 15 seconds
        
        # Start the metrics collection thread
        metrics_thread = threading.Thread(target=collect_metrics_loop, daemon=True)
        metrics_thread.start()
    
    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Return Prometheus metrics."""
        try:
            return generate_latest(METRICS_REGISTRY)
        except Exception as e:
            print(f"Error generating metrics: {e}")
            return "Error generating metrics"
