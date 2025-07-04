"""
Security-related functionality for the API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .rate_limiter import setup_rate_limiting
from .headers import setup_security_headers
from .auth import setup_authentication


def setup_security(app: FastAPI) -> None:
    """
    Set up all security-related middleware and utilities.
    
    Args:
        app: FastAPI application instance
    """
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup rate limiting
    setup_rate_limiting(app)
    
    # Setup security headers
    setup_security_headers(app)
    
    # Setup authentication (if enabled)
    if app.state.settings.ENABLE_AUTHENTICATION:
        setup_authentication(app)
