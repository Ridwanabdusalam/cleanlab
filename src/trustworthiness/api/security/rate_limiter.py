"""
Rate limiting functionality for the API.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


limiter = Limiter(key_func=get_remote_address)


def setup_rate_limiting(app):
    """
    Set up rate limiting for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Initialize the limiter
    app.state.limiter = limiter
    
    # Add rate limit exceeded handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests, please try again later."}
        )
    
    # Add rate limit headers to responses
    @app.middleware("http")
    async def add_rate_limit_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Get rate limit info from state if available
        if hasattr(request.state, "rate_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit.limit)
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit.remaining)
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit.reset)
        
        return response
