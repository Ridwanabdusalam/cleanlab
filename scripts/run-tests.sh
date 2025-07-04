#!/bin/bash

# Exit on error
set -e

# Default values
COVERAGE=false
PARALLEL=false
TEST_PATH="tests/"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        *)
            TEST_PATH="$1"
            shift
            ;;
    esac
done

echo "Running tests..."

# Run tests with coverage if requested
if [ "$COVERAGE" = true ]; then
    echo "Running tests with coverage..."
    if [ "$PARALLEL" = true ]; then
        python -m pytest -n auto --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80 "$TEST_PATH"
    else
        python -m pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80 "$TEST_PATH"
    fi
    
    # Open coverage report in browser
    if command -v xdg-open &> /dev/null; then
        xdg-open htmlcov/index.html
    elif command -v open &> /dev/null; then
        open htmlcov/index.html
    fi
else
    if [ "$PARALLEL" = true ]; then
        python -m pytest -n auto "$TEST_PATH"
    else
        python -m pytest "$TEST_PATH"
    fi
fi
