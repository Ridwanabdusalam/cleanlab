#!/bin/bash

# Exit on error
set -e

echo "Setting up development environment..."

# Check if Python 3.10+ is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3.10+ is required but not installed. Please install Python 3.10 or later and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
if [[ "$PYTHON_VERSION" < "3.10" ]]; then
    echo "Python 3.10 or later is required, but you have Python $PYTHON_VERSION. Please upgrade Python and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip is not installed. Please install pip and try again."
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install pip-tools for dependency management
echo "Installing pip-tools..."
python3 -m pip install --upgrade pip-tools

# Install development dependencies
echo "Installing development dependencies..."
python3 -m pip install --upgrade -r requirements-dev.txt

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Install Git hooks
echo "Installing Git hooks..."
./scripts/install-hooks.sh

echo ""
echo "Development environment setup complete!"
echo "You can now start developing. Here are some useful commands:"
echo "- 'make test' - Run tests"
echo "- 'make lint' - Run linters"
echo "- 'make format' - Format code"
echo "- 'make check-types' - Run type checking"
echo "- 'make docs' - Build documentation"
echo "- 'make run' - Start the development server"
