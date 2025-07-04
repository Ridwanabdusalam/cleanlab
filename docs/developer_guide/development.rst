.. _development_guide:

Development Guide
================

This guide provides instructions for setting up a development environment and working with the codebase.

Development Setup
----------------

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/trustworthiness-detector.git
   cd trustworthiness-detector
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

Code Organization
----------------

The project follows this structure:

- `src/trustworthiness/` - Main package source code
  - `api/` - FastAPI application and routes
  - `detector.py` - Core trustworthiness detection logic
  - `detector_gemini.py` - Gemini-specific implementation
  - `metrics.py` - Monitoring and metrics collection
  - `models.py` - Data models and schemas
  - `scoring.py` - Scoring functions implementation
  - `security/` - Security-related modules

Development Workflow
-------------------

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and run tests:
   ```bash
   pytest tests/ -v --cov=src --cov-report=term-missing
   ```

3. Run linters and formatters:
   ```bash
   black src/ tests/
   isort src/ tests/
   flake8 src/ tests/
   mypy src/ tests/
   ```

4. Commit your changes with a descriptive message:
   ```bash
   git commit -m "feat: add new feature"
   ```

5. Push your branch and create a pull request

Dependencies
-----------

- Python 3.8+
- FastAPI
- Pydantic
- Google Generative AI (for Gemini integration)
- pytest (for testing)
- black, isort, flake8 (for code quality)

See `pyproject.toml` for the complete list of dependencies.
