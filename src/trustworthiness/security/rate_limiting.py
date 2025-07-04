"""
Rate limiting for API requests.
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ..config import settings


class RateLimiter:
    """Implements rate limiting for API endpoints."""
    
    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        jitter: float = 0.1,
        block_duration: int = 300,  # 5 minutes
    ):
        """Initialize the rate limiter.
        
        Args:
            requests: Number of requests allowed per window
            window: Time window in seconds
            jitter: Random jitter factor (0-1) to prevent thundering herd
            block_duration: How long to block clients that exceed the rate limit (seconds)
        """
        self.requests = requests
        self.window = window
        self.jitter = jitter
        self.block_duration = block_duration
        
        # Store request timestamps by client IP
        self.access_records: Dict[str, List[float]] = defaultdict(list)
        # Track blocked clients and when they were blocked
        self.blocked_clients: Dict[str, float] = {}
        self._cleanup_interval = 60  # Clean up old records every 60 seconds
        self._last_cleanup = time.time()
    
    async def __call__(self, request: Request) -> bool:
        """Check if the request is allowed based on rate limits.
        
        Args:
            request: The incoming request
            
        Returns:
            bool: True if the request is allowed, False otherwise
            
        Raises:
            HTTPException: 429 if rate limit is exceeded
        """
        if not getattr(settings, 'ENABLE_RATE_LIMITING', True):
            return True
            
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Check if client is blocked
        if client_ip in self.blocked_clients:
            block_until = self.blocked_clients[client_ip] + self.block_duration
            if current_time < block_until:
                # Client is still blocked
                retry_after = int(block_until - current_time)
                self._raise_rate_limit_exceeded(retry_after)
            else:
                # Block has expired, remove from blocked clients
                del self.blocked_clients[client_ip]
        
        # Clean up old records periodically
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_records()
            self._last_cleanup = current_time
        
        # Get timestamps within the current window
        window_start = current_time - self.window
        recent_requests = [
            t for t in self.access_records[client_ip] 
            if t >= window_start
        ]
        
        # Check rate limit
        if len(recent_requests) >= self.requests:
            # Add to blocked clients
            self.blocked_clients[client_ip] = current_time
            retry_after = self.window
            self._raise_rate_limit_exceeded(retry_after)
        
        # Add current request timestamp
        self.access_records[client_ip].append(current_time)
        
        # Add jitter to spread out retries
        if len(recent_requests) > self.requests * 0.8:  # Only apply jitter when approaching limit
            jitter = self.jitter * (2 * (random.random() - 0.5))  # Random value between -jitter and +jitter
            time.sleep(abs(jitter))
        
        return True
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client's IP address from the request."""
        # Try to get the real IP behind proxies
        if x_forwarded_for := request.headers.get("X-Forwarded-For"):
            # X-Forwarded-For can be a comma-separated list of IPs
            return x_forwarded_for.split(",")[0].strip()
        
        if x_real_ip := request.headers.get("X-Real-IP"):
            return x_real_ip
            
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_records(self) -> None:
        """Clean up old access records to prevent memory leaks."""
        current_time = time.time()
        window_start = current_time - max(self.window, self.block_duration) * 2
        
        # Clean up access records
        for ip in list(self.access_records.keys()):
            # Keep only recent requests
            self.access_records[ip] = [
                t for t in self.access_records[ip] 
                if t >= window_start
            ]
            
            # Remove empty lists
            if not self.access_records[ip]:
                del self.access_records[ip]
        
        # Clean up expired blocks
        for ip in list(self.blocked_clients.keys()):
            if current_time - self.blocked_clients[ip] > self.block_duration:
                del self.blocked_clients[ip]
    
    def _raise_rate_limit_exceeded(self, retry_after: int) -> None:
        """Raise an HTTP 429 exception with appropriate headers."""
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(self.requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            },
        )


def get_rate_limiter() -> RateLimiter:
    """Get or create a rate limiter instance with settings from config."""
    if not hasattr(get_rate_limiter, '_instance'):
        get_rate_limiter._instance = RateLimiter(
            requests=getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 100),
            window=getattr(settings, 'RATE_LIMIT_WINDOW', 60),
            jitter=getattr(settings, 'RATE_LIMIT_JITTER', 0.1),
        )
    return get_rate_limiter._instance
