.. _configuration:

Configuration
=============

The Trustworthiness Detector can be configured using environment variables or programmatically through the Python API.

Environment Variables
--------------------

You can configure the application using environment variables. Create a `.env` file in your project root:

.. code-block:: ini

    # API Configuration
    ENV=development
    DEBUG=true
    HOST=0.0.0.0
    PORT=8000
    WORKERS=4
    
    # CORS
    ALLOWED_ORIGINS='["*"]'
    ALLOWED_METHODS='["*"]'
    ALLOWED_HEADERS='["*"]'
    
    # Security
    SECRET_KEY=your-secret-key
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    
    # Rate Limiting
    ENABLE_RATE_LIMITING=true
    RATE_LIMIT=100
    RATE_LIMIT_WINDOW=60
    
    # Monitoring
    ENABLE_METRICS=true
    METRICS_PATH=/metrics
    
    # Logging
    LOG_LEVEL=INFO
    LOG_FORMAT=json
    
    # Gemini API
    GEMINI_API_KEY=your-gemini-api-key
    GEMINI_MODEL=gemini-pro
    GEMINI_MAX_TOKENS=2048
    GEMINI_TEMPERATURE=0.7
    
    # Redis (for rate limiting and caching)
    REDIS_URL=redis://redis:6379/0
    
    # Prometheus
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
    
    # Trustworthiness Thresholds
    TRUST_THRESHOLD=0.8
    WARNING_THRESHOLD=0.6
    
    # Feature Flags
    ENABLE_REQUEST_SIGNING=false
    ENABLE_AUDIT_LOGGING=true
    ENABLE_SECURITY_HEADERS=true

Python API Configuration
------------------------

You can also configure the detector programmatically:

.. code-block:: python

    from trustworthiness import TrustworthinessDetector, ModelConfig, APIConfig
    
    # Configure the model
    model_config = ModelConfig(
        model_name="gemini-1.5-pro",
        temperature=0.7,
        max_tokens=1024,
        trust_threshold=0.8,
        warning_threshold=0.6
    )
    
    # Configure the API
    api_config = APIConfig(
        host="0.0.0.0",
        port=8000,
        debug=True,
        workers=4,
        enable_metrics=True,
        metrics_path="/metrics"
    )
    
    # Initialize the detector with custom config
    detector = TrustworthinessDetector(
        model_config=model_config,
        api_config=api_config
    )

Logging Configuration
---------------------

Configure logging using Python's logging configuration:

.. code-block:: python

    import logging
    from trustworthiness import setup_logging
    
    # Basic configuration
    setup_logging(level=logging.INFO, format="json")
    
    # Or configure manually
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('trustworthiness.log')
        ]
    )

Monitoring Configuration
-----------------------

The application exposes Prometheus metrics by default. To enable:

1. Set `ENABLE_METRICS=true`
2. Configure Prometheus to scrape the metrics endpoint
3. Import the provided Grafana dashboard

Rate Limiting
-------------

Configure rate limiting using Redis:

.. code-block:: ini

    # Enable rate limiting
    ENABLE_RATE_LIMITING=true
    
    # Requests per window
    RATE_LIMIT=100
    
    # Time window in seconds
    RATE_LIMIT_WINDOW=60
    
    # Redis connection
    REDIS_URL=redis://redis:6379/0

Security Configuration
---------------------

Enable security features:

.. code-block:: ini

    # Enable request signing
    ENABLE_REQUEST_SIGNING=false
    
    # Enable audit logging
    ENABLE_AUDIT_LOGGING=true
    
    # Enable security headers
    ENABLE_SECURITY_HEADERS=true
    
    # CORS settings
    ALLOWED_ORIGINS='["*"]'
    ALLOWED_METHODS='["*"]'
    ALLOWED_HEADERS='["*"]'
