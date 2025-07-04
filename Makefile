# Makefile for Trustworthiness Detector

# Variables
PYTHON = python3
PIP = pip3
PYTEST = pytest
COVERAGE = coverage
BLACK = black
ISORT = isort
MYPY = mypy
RUFF = ruff

# Directories
SRC_DIR = src
TEST_DIR = tests

# Targets
.PHONY: help install install-dev install-test install-docs clean test test-cov lint format check-types check-docs docs serve-docs

help:
	@echo "Available commands:"
	@echo "  install       - Install the package in development mode"
	@echo "  install-dev   - Install development dependencies"
	@echo "  install-test  - Install test dependencies"
	@echo "  install-docs  - Install documentation dependencies"
	@echo "  clean         - Remove build artifacts and cache"
	@echo "  test          - Run tests"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  lint          - Run all linters"
	@echo "  format        - Format code with Black and isort"
	@echo "  check-types   - Run type checking with mypy"
	@echo "  check-docs    - Build documentation"
	@echo "  docs          - Generate and serve documentation"
	@echo "  serve-docs    - Serve documentation locally"

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

install-test:
	$(PIP) install -e ".[test]"

install-docs:
	$(PIP) install -e ".[docs]"

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .mypy_cache/ .pytest_cache/ .ruff_cache/

# Testing
test:
	$(PYTEST) -v $(TEST_DIR)

test-cov:
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html $(TEST_DIR)

# Linting and Formatting
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

format:
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

check-types:
	$(MYPY) $(SRC_DIR) $(TEST_DIR)

# Documentation
check-docs:
	cd docs && make html

docs: check-docs
	@echo "Documentation built in docs/_build/html/index.html"

serve-docs: docs
	cd docs/_build/html && python -m http.server 8000

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Docker
docker-build:
	docker build -t trustworthiness-detector .

docker-run:
	docker run -p 8000:8000 trustworthiness-detector

# Clean up Docker
clean-docker:
	docker system prune -f

docker-clean: clean-docker

# Development server
run:
	uvicorn trustworthiness.api:app --reload

# Production server
run-prod:
	gunicorn -w 4 -k uvicorn.workers.UvicornWorker trustworthiness.api:app
