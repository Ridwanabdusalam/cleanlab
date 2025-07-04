"""
Test package for Trustworthiness Detector.

This package contains unit, integration, and functional tests.
"""

# Register custom marks to avoid pytest warnings
import pytest


def pytest_configure(config):
    """Register custom markers to avoid warnings."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API key)"
    )
    config.addinivalue_line("markers", "functional: mark test as functional test")
