# Contributing to Trustworthiness Detector

Thank you for your interest in contributing to the Trustworthiness Detector project! We welcome contributions from the community to help improve this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [License](#license)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
   ```bash
   git clone https://github.com/your-username/trustworthiness-detector.git
   cd trustworthiness-detector
   ```
3. Set up your development environment (see below)

## Development Environment

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/) (recommended) or pip
- Git

### Setup with Poetry (Recommended)

1. Install dependencies:
   ```bash
   poetry install --with dev,docs
   ```
2. Activate the virtual environment:
   ```bash
   poetry shell
   ```

### Setup with pip

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -e ".[dev,docs]"
   ```

## Making Changes

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-number-short-description
   ```
2. Make your changes following the [code style guidelines](#code-style)
3. Add tests for your changes
4. Update documentation as needed
5. Run tests and linters
6. Commit your changes with a descriptive message

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run a specific test file
pytest tests/unit/test_module.py

# Run tests in parallel
pytest -n auto
```

## Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **mypy** for static type checking
- **ruff** for linting

Run the following commands to ensure your code follows our style guidelines:

```bash
# Auto-format code
make format

# Check code style
make lint

# Check types
make check-types
```

## Documentation

We use Sphinx for documentation. To build the documentation locally:

```bash
# Build documentation
make docs

# Serve documentation locally
make serve-docs
```

Documentation is automatically built and published to Read the Docs on each push to the main branch.

## Pull Request Process

1. Ensure all tests pass and there are no linting errors
2. Update the CHANGELOG.md with your changes
3. Submit a pull request with a clear description of your changes
4. Reference any related issues in your PR description
5. Wait for maintainers to review your PR and address any feedback

## Reporting Issues

When reporting issues, please include:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (Python version, OS, etc.)
- Any relevant error messages or logs

## License

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE).
