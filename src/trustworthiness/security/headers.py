"""
Security-related HTTP headers middleware.
"""

from typing import Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""
    
    def __init__(
        self,
        app: ASGIApp,
        csp_directives: Optional[Dict[str, List[str]]] = None,
        feature_policy: Optional[Dict[str, List[str]]] = None,
        permissions_policy: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Initialize the middleware.
        
        Args:
            app: The ASGI application
            csp_directives: Content Security Policy directives
            feature_policy: Feature-Policy header directives (legacy)
            permissions_policy: Permissions-Policy header directives
        """
        super().__init__(app)
        
        # Default CSP directives (can be overridden)
        self.csp_directives = csp_directives or {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'"],
            "img-src": ["'self'"],
            "connect-src": ["'self'"],
            "font-src": ["'self'"],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
        }
        
        # Legacy Feature-Policy (for older browsers)
        self.feature_policy = feature_policy or {
            "accelerometer": ["'none'"],
            "camera": ["'none'"],
            "geolocation": ["'none'"],
            "gyroscope": ["'none'"],
            "magnetometer": ["'none'"],
            "microphone": ["'none'"],
            "payment": ["'none'"],
            "usb": ["'none'"],
        }
        
        # Modern Permissions-Policy (replaces Feature-Policy)
        self.permissions_policy = permissions_policy or {
            "accelerometer": [],
            "ambient-light-sensor": [],
            "autoplay": [],
            "battery": [],
            "camera": [],
            "display-capture": [],
            "document-domain": [],
            "encrypted-media": [],
            "execution-while-not-rendered": [],
            "execution-while-out-of-viewport": [],
            "fullscreen": [],
            "geolocation": [],
            "gyroscope": [],
            "layout-animations": [],
            "legacy-image-formats": [],
            "magnetometer": [],
            "microphone": [],
            "midi": [],
            "navigation-override": [],
            "payment": [],
            "picture-in-picture": [],
            "publickey-credentials-get": [],
            "sync-xhr": [],
            "usb": [],
            "wake-lock": [],
            "xr-spatial-tracking": [],
        }
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and add security headers to the response."""
        response = await call_next(request)
        
        # Skip if headers already set
        if hasattr(request.state, 'security_headers_processed'):
            return response
        
        # Add security headers
        self._add_security_headers(response)
        
        # Mark as processed to avoid duplicate processing
        request.state.security_headers_processed = True
        
        return response
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to the response."""
        headers = self._get_security_headers()
        for header, value in headers.items():
            if value and header.lower() not in response.headers:
                response.headers[header] = value
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get a dictionary of security headers and their values."""
        headers: Dict[str, str] = {}
        
        # Content Security Policy
        csp_parts = []
        for directive, sources in self.csp_directives.items():
            if sources:
                csp_parts.append(f"{directive} {' '.join(sources)}")
            else:
                csp_parts.append(directive)
        
        headers["Content-Security-Policy"] = "; ".join(csp_parts)
        
        # Legacy Feature-Policy
        feature_policy_parts = []
        for feature, origins in self.feature_policy.items():
            if origins:
                feature_policy_parts.append(f"{feature} {' '.join(origins)}")
            else:
                feature_policy_parts.append(feature)
        
        headers["Feature-Policy"] = ", ".join(feature_policy_parts)
        
        # Modern Permissions-Policy
        permissions_policy_parts = []
        for feature, origins in self.permissions_policy.items():
            if origins:
                permissions_policy_parts.append(f"{feature}=({' '.join(origins)})")
            else:
                permissions_policy_parts.append(f"{feature}=()")
        
        headers["Permissions-Policy"] = ", ".join(permissions_policy_parts)
        
        # Other security headers
        headers.update({
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Clickjacking protection
            "X-Frame-Options": "DENY",
            
            # XSS protection (legacy, but still useful)
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # HSTS (should be configured at the web server level in production)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Prevent content from being embedded in frames from other sites
            "X-Content-Security-Policy": "frame-ancestors 'none'",
            
            # Disable FLoC tracking
            "Permissions-Policy": "interest-cohort=()",
            
            # Enable cross-origin isolation
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Resource-Policy": "same-site",
        })
        
        return headers
