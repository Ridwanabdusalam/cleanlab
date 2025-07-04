# Trustworthiness Detector

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docker](https://img.shields.io/badge/Docker-available-2496ED.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Documentation Status](https://readthedocs.org/projects/trustworthiness-detector/badge/?version=latest)](https://trustworthiness-detector.readthedocs.io/)
[![Tests](https://github.com/yourusername/trustworthiness-detector/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/trustworthiness-detector/actions)
[![codecov](https://codecov.io/gh/yourusername/trustworthiness-detector/graph/badge.svg?token=YOUR-TOKEN)](https://codecov.io/gh/yourusername/trustworthiness-detector)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code style: isort](https://img.shields.io/badge/%20imports-isort-ef8336.svg)](https://pycqa.github.io/isort/)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

A production-ready Python package and REST API for detecting unreliable outputs from Large Language Models (LLMs) with confidence intervals, model explainability, and custom scoring functions. The package provides both a Python API and a REST interface to evaluate the trustworthiness of LLM-generated answers through a comprehensive verification process.

## 🚀 Quick Start

### Installation

```bash
pip install -e .
```

### Basic Usage

```python
from trustworthiness import TrustworthinessDetector

# Initialize the detector
detector = TrustworthinessDetector()

# Evaluate a single Q&A pair
question = "What is the capital of France?"
answer = "Paris"
score = detector.evaluate(question, answer)
print(f"Trust score: {score:.2f}")
```

### Running the Example

Check out the complete example in [examples/usage_example.py](examples/usage_example.py) which demonstrates:
- Basic usage
- Batch evaluation
- Custom scoring functions
- Error handling
- Real-world integration

To run the example:

```bash
python examples/usage_example.py
```

## 📖 Documentation

For detailed documentation including API reference, advanced usage, and customization options, see:
- [Full Documentation](https://trustworthiness-detector.readthedocs.io/)
- [Example Implementation](examples/usage_example.py)
- [API Reference](docs/api.md)

## 🌟 Key Features

### Core Functionality
- **Modular Architecture**: Clean separation of concerns with pluggable components
- **Multiple Backends**: Support for Gemini API and custom model integrations
- **Type Annotated**: Full Python type hints for better IDE support and reliability

### Evaluation Features
- **Confidence Intervals**: Get trust scores with statistical confidence bounds
- **Model Explainability**: Detailed scoring explanations and factor analysis
- **Custom Scoring**: Define and use your own scoring functions
- **Batch Processing**: Efficient evaluation of multiple Q&A pairs
- **Streaming Support**: Real-time evaluation updates

### Production Ready
- **REST API**: Standardized HTTP endpoints with OpenAPI documentation
- **Containerized**: Easy deployment with Docker and Kubernetes
- **Monitoring**: Built-in Prometheus metrics and Grafana dashboards
- **Security**: Request validation, rate limiting, and audit logging
- **Resilience**: Circuit breaking and automatic retries

### Developer Experience
- **Pre-commit Hooks**: Enforce code quality with pre-commit hooks
- **Makefile**: Common development tasks simplified
- **Code Quality**: Black, isort, mypy, and ruff for consistent code style
- **Testing**: Comprehensive test suite with pytest and coverage reporting
- **Documentation**: Sphinx-generated documentation with examples

## 🏗️ Project Structure

```
.
├── .github/              # GitHub Actions workflows
├── .vscode/             # VS Code settings
├── docs/                # Documentation source
├── grafana/             # Grafana dashboards and provisioning
│   ├── dashboards/      # Pre-configured dashboards
│   └── provisioning/    # Data sources and dashboard configurations
├── prometheus/          # Prometheus configuration
├── scripts/             # Utility scripts
│   ├── install-dependencies.sh  # Setup development environment
│   ├── install-hooks.sh        # Install Git hooks
│   └── run-tests.sh            # Run tests with coverage
├── src/                 # Source code
│   └── trustworthiness/
│       ├── __init__.py         # Package exports and version
│       ├── api/                # FastAPI application and routes
│       │   ├── __init__.py     # API initialization and setup
│       │   ├── dependencies.py # API dependencies and middleware
│       │   └── routes/         # API endpoint definitions
│       │       ├── __init__.py
│       │       ├── evaluate.py # Evaluation endpoints
│       │       └── health.py   # Health check endpoints
│       ├── detector.py         # Base trustworthiness detector
│       ├── detector_gemini.py  # Gemini-specific detector
│       ├── models.py           # Core data models
│       └── security/           # Security components
├── tests/               # Test suite
├── .coveragerc          # Coverage configuration
├── .dockerignore        # Docker ignore file
├── .editorconfig        # Editor configuration
├── .env.example         # Example environment variables
├── .gitignore          # Git ignore file
├── .pre-commit-config.yaml  # Pre-commit hooks
├── docker-compose.yml   # Docker Compose configuration
├── docker-compose.override.yml.example  # Example override
├── Makefile             # Common development tasks
├── pyproject.toml       # Project metadata and dependencies
└── README.md            # This file
│   ├── __init__.py
│   ├── models.py         # Security models
│   ├── rate_limiting.py  # Rate limiting implementation
│   └── auth.py          # Authentication and authorization
├── scoring.py            # Scoring function registry
└── utils/                # Utility functions
    ├── __init__.py
    ├── logging.py       # Logging configuration
    └── validation.py    # Input validation

tests/
├── unit/                # Unit tests
│   ├── test_detector.py
│   ├── test_gemini_detector.py
│   └── test_circuit_breaker.py
└── integration/         # Integration tests
    └── test_api.py
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- [Gemini API Key](https://ai.google.dev/)

### Environment Setup

1. **Create a `.env` file**
   Copy the example environment file and update it with your configuration:
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file**
   Open the `.env` file in your preferred text editor and update the following required variables:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `SECRET_KEY`: A secure secret key for JWT token encryption

   Example:
   ```bash
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   SECRET_KEY=generate_a_secure_random_string_here
   ```

3. **Optional Configuration**
   Adjust other settings in the `.env` file as needed, such as:
   - API host and port
   - Logging level
   - CORS settings
   - Rate limiting
   - Database connection (if applicable)

### Installation

#### Using Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/trustworthiness-detector.git
cd trustworthiness-detector

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Build and start the services
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`

#### Local Development
```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev

# Activate the virtual environment
poetry shell

# Start the development server
uvicorn trustworthiness.api:app --reload
```

### Configuration

Configure the application using environment variables in `.env`:

```env
# API Configuration
ENV=development
DEBUG=true
API_KEY=your-api-key
API_SECRET=your-api-secret

# Model Configuration
MODEL_NAME=gemini-pro
MAX_TOKENS=2048
TEMPERATURE=0.7

# Security
ENABLE_RATE_LIMITING=true
RATE_LIMIT=100/1hour
ENABLE_REQUEST_SIGNING=true
REQUEST_TIMEOUT=30

# Monitoring
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
```

## 📚 API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Metrics Endpoint**: http://localhost:8000/metrics
- **Health Check**: http://localhost:8000/health

## 🛠️ API Endpoints

### Evaluate Single Response
```http
POST /api/v1/evaluate
Content-Type: application/json
X-API-Key: your-api-key

{
  "question": "What is the capital of France?",
  "answer": "Paris is the capital of France.",
  "context": "Geography questions about European capitals"
}
```

### Stream Evaluation Progress
```http
POST /api/v1/evaluate/stream
Content-Type: application/json
X-API-Key: your-api-key

{
  "question": "Explain quantum computing",
  "answer": "Quantum computing uses qubits...",
  "context": "Technical explanation of quantum computing concepts"
}
```

### Batch Evaluation
```http
POST /api/v1/evaluate/batch
Content-Type: application/json
X-API-Key: your-api-key

{
  "items": [
    {
      "question": "What is Python?",
      "answer": "Python is a programming language.",
      "context": "Programming languages"
    },
    {
      "question": "What is the speed of light?",
      "answer": "Approximately 299,792 kilometers per second",
      "context": "Physics constants"
    }
  ]
}
```

### Manage Scoring Functions
```http
# List available scoring functions
GET /api/v1/scoring-functions

# Register a new scoring function
POST /api/v1/scoring-functions/strict-qa
Content-Type: application/json

{
  "description": "Strict QA evaluation with heavy penalties for uncertainty",
  "weights": {
    "relevance": 0.6,
    "specificity": 0.4
  }
}
```

## 🔍 Response Format

### Single Evaluation Response
```json
{
  "question": "What is the capital of France?",
  "answer": "Paris is the capital of France.",
  "trust_score": {
    "score": 0.92,
    "confidence_interval": [0.88, 0.96],
    "explanation": {
      "score": 0.92,
      "confidence": 0.95,
      "reasoning": "The answer is factually correct and well-supported by the context.",
      "factors": {
        "relevance": 0.95,
        "specificity": 0.89,
        "context_match": 0.92
      }
    }
  },
  "context": "Geography questions about European capitals"
}
```

### Error Response
```json
{
  "error": "validation_error",
  "detail": [
    {
      "loc": ["body", "question"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 🔧 Advanced Configuration

### Custom Scoring Functions

You can create custom scoring functions by implementing the `ScoringFunction` protocol:

```python
from trustworthiness.models import ScoringFunction, TrustScore, ScoreExplanation

async def custom_scorer(
    question: str,
    answer: str,
    context: Optional[str] = None,
    **kwargs
) -> TrustScore:
    # Your custom scoring logic here
    score = calculate_custom_score(question, answer, context)
    
    return TrustScore(
        score=score,
        confidence_interval=(max(0, score - 0.1), min(1, score + 0.1)),
        explanation=ScoreExplanation(
            score=score,
            confidence=0.9,
            reasoning="Custom scoring applied",
            factors={"custom_factor": 0.85}
        )
    )
```

### Monitoring and Metrics

The API exposes Prometheus metrics at `/metrics` that can be scraped by a Prometheus server. A sample Grafana dashboard is included in the `monitoring/` directory.

Key metrics include:
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration histogram
- `trust_score_distribution`: Distribution of trust scores
- `evaluation_errors_total`: Count of evaluation errors

## 🚀 Deployment

### Kubernetes

```yaml
# trustworthiness-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:

```bash
# Apply Kubernetes manifests
kubectl apply -f deploy/kubernetes/

# Check deployment status
kubectl get pods -n trustworthiness

# View logs
kubectl logs -f deployment/trustworthiness-detector -n trustworthiness
```

### Monitoring Stack

The monitoring stack includes:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Redis**: Caching and rate limiting

Access the monitoring tools:

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- API Documentation: http://localhost:8000/docs

### Production Considerations

1. **Secrets Management**:
   - Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)
   - Never commit secrets to version control

2. **High Availability**:
   - Deploy multiple replicas of the API
   - Use a load balancer
   - Configure database connection pooling

3. **Monitoring and Alerting**:
   - Set up alerts in Grafana
   - Monitor error rates and response times
   - Set up log aggregation (ELK Stack, Loki)

4. **Security**:
   - Enable request signing
   - Use HTTPS with valid certificates
   - Implement proper CORS policies
   - Regular security audits

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## API Reference

### TrustworthinessDetector

```python
detector = TrustworthinessDetector(
    model=None,             # Uses DEFAULT_MODEL if not specified
    temperature=0.0,        # LLM temperature (0 = deterministic)
    cache_responses=True    # Cache to avoid duplicate API calls
)
```

### Main Methods

- `get_trustworthiness_score(question, answer)`: Get score for single Q&A
- `batch_evaluate(qa_pairs)`: Evaluate multiple Q&A pairs efficiently

## Examples

See `examples/usage_example.py` for comprehensive examples.

## Score Interpretation

- **> 0.7**: High confidence (trustworthy)
- **0.3 - 0.7**: Medium confidence (uncertain)
- **< 0.3**: Low confidence (likely incorrect)

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/trustworthiness
```

## License

MIT
