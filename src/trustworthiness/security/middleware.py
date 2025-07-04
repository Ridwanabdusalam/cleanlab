"""
Security middleware for the Trustworthiness Detector API.
"""

import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from .audit import AuditLogger, get_audit_logger
from .headers import SecurityHeadersMiddleware
from .rate_limiting import RateLimiter, get_rate_limiter
from .request_signing import RequestSigner, get_request_signer
from ..config import settings


class SecurityMiddleware:
    """Main security middleware that combines all security features."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_request_signing: bool = True,
        enable_rate_limiting: bool = True,
        enable_cors: bool = True,
        enable_security_headers: bool = True,
    ) -> None:
        """Initialize the security middleware.
        
        Args:
            app: The ASGI application
            enable_request_signing: Whether to enable request signature verification
            enable_rate_limiting: Whether to enable rate limiting
            enable_cors: Whether to enable CORS middleware
            enable_security_headers: Whether to add security headers
        """
        self.app = app
        self.enable_request_signing = enable_request_signing
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_cors = enable_cors
        self.enable_security_headers = enable_security_headers
        
        # Initialize security components
        self.audit_logger = get_audit_logger()
        self.rate_limiter = get_rate_limiter()
        self.request_signer = get_request_signer()
        
        # Configure middleware chain
        self._configure_middleware()
    
    def _configure_middleware(self) -> None:
        """Configure the middleware pipeline."""
        app = self.app
        
        # 1. Security headers (innermost)
        if self.enable_security_headers:
            app = SecurityHeadersMiddleware(app)
        
        # 2. Request signing
        if self.enable_request_signing:
            app = RequestSigningMiddleware(app)
        
        # 3. Rate limiting
        if self.enable_rate_limiting:
            app = RateLimiterMiddleware(app, self.rate_limiter)
        
        # 4. CORS (outermost)
        if self.enable_cors:
            app = CORSMiddleware(
                app=app,
                allow_origins=getattr(settings, 'ALLOWED_ORIGINS', ["*"]),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        self.app = app
    
    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        """Handle the incoming request.
        
        This method is called for each request that goes through the middleware.
        """
        await self.app(scope, receive, send)


class RequestSigningMiddleware(BaseHTTPMiddleware):
    """Middleware for request signature verification."""
    
    def __init__(self, app: ASGIApp, request_signer: Optional[RequestSigner] = None) -> None:
        super().__init__(app)
        self.request_signer = request_signer or get_request_signer()
        self.audit_logger = get_audit_logger()
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Process the request and verify the signature."""
        # Skip signature verification for certain paths
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        try:
            # Verify the request signature
            await self.request_signer.verify_request(request)
            
            # Log successful verification
            self.audit_logger.log_security_event(
                "request_signed",
                f"Request verified: {request.method} {request.url.path}",
                ip_address=request.client.host if request.client else None,
                method=request.method,
                path=request.url.path,
            )
            
            # Proceed to the next middleware
            return await call_next(request)
            
        except HTTPException as http_exc:
            # Log the security event
            self.audit_logger.log_security_event(
                "request_verification_failed",
                f"Request verification failed: {str(http_exc.detail)}",
                ip_address=request.client.host if request.client else None,
                method=request.method,
                path=request.url.path,
                status_code=http_exc.status_code,
                error=str(http_exc.detail),
                severity="warning",
            )
            # Re-raise the original HTTPException to ensure status code is preserved
            raise http_exc from None

        except Exception as e:
            # Log unexpected errors
            self.audit_logger.log_security_event(
                "request_verification_error",
                f"Error verifying request: {str(e)}",
                ip_address=request.client.host if request.client else None,
                method=request.method,
                path=request.url.path,
                error=str(e),
                severity="error",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during request verification"
            ) from e


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(self, app: ASGIApp, rate_limiter: Optional[RateLimiter] = None) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter or get_rate_limiter()
        self.audit_logger = get_audit_logger()
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Any:
        """Process the request and apply rate limiting."""
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
        
        try:
            # Apply rate limiting
            await self.rate_limiter(request)
            
            # Proceed to the next middleware
            return await call_next(request)
            
        except HTTPException as e:
            # Log rate limit exceeded
            if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                self.audit_logger.log_security_event(
                    "rate_limit_exceeded",
                    f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}",
                    ip_address=request.client.host if request.client else None,
                    method=request.method,
                    path=request.url.path,
                    severity="warning",
                )
            raise


def setup_security(app: FastAPI) -> None:
    """Set up security middleware for the FastAPI application."""
    # Apply security middleware
    app.add_middleware(SecurityMiddleware)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        return {"status": "ok"}
    
    # Add startup event to log security configuration
    @app.on_event("startup")
    async def log_security_config() -> None:
        logger = get_audit_logger()
        logger.log_security_event(
            "security_config",
            "Security middleware initialized",
            config={
                "request_signing": getattr(settings, 'ENABLE_REQUEST_SIGNING', True),
                "rate_limiting": getattr(settings, 'ENABLE_RATE_LIMITING', True),
                "audit_logging": getattr(settings, 'ENABLE_AUDIT_LOGGING', True),
                "allowed_origins": getattr(settings, 'ALLOWED_ORIGINS', ["*"]),
            },
            severity="info",
        )
