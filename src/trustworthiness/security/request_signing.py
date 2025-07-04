"""
Request signing and verification for API authentication.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, validator

from ..config import settings


class RequestSigner:
    """Handles request signing and verification."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timestamp_header: str = "X-API-Timestamp",
        signature_header: str = "X-API-Signature",
        key_header: str = "X-API-Key",
        max_age: int = 300,  # 5 minutes
    ):
        """Initialize the request signer.
        
        Args:
            api_key: The API key for identifying the client
            api_secret: The secret key for signing requests
            timestamp_header: Header name for the request timestamp
            signature_header: Header name for the request signature
            key_header: Header name for the API key
            max_age: Maximum allowed age of a request in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.timestamp_header = timestamp_header
        self.signature_header = signature_header
        self.key_header = key_header
        self.max_age = max_age
    
    def sign_request(
        self,
        method: str,
        path: str,
        body: Optional[Union[dict, str, bytes]] = None,
        timestamp: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate headers for a signed request.
        
        Args:
            method: HTTP method (e.g., 'GET', 'POST')
            path: Request path (e.g., '/api/endpoint')
            body: Request body (dict, str, or bytes)
            timestamp: Optional timestamp (defaults to current time)
            headers: Additional headers to include
            
        Returns:
            Dictionary of headers to include in the request
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Convert body to string if it's a dict
        if isinstance(body, dict):
            body_str = json.dumps(body, sort_keys=True, separators=(",", ":"))
        elif body is None:
            body_str = ""
        else:
            body_str = str(body)
        
        # Create the signature
        message = self._create_message(method, path, body_str, timestamp)
        signature = self._sign_message(message)
        
        # Build headers
        result = {
            self.key_header: self.api_key,
            self.timestamp_header: str(timestamp),
            self.signature_header: signature,
        }
        
        if headers:
            result.update(headers)
            
        return result
    
    async def verify_request(self, request: Request) -> bool:
        """Verify a signed request.
        
        Args:
            request: The incoming request
            
        Returns:
            bool: True if the request is valid, False otherwise
            
        Raises:
            HTTPException: If the request is invalid
        """
        # Check if required headers are present
        missing_headers = []
        for header in [self.key_header, self.timestamp_header, self.signature_header]:
            if header not in request.headers:
                missing_headers.append(header)
        
        if missing_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required headers: {', '.join(missing_headers)}",
            )
        
        # Get headers
        api_key = request.headers[self.key_header]
        timestamp_str = request.headers[self.timestamp_header]
        signature = request.headers[self.signature_header]
        
        # Verify API key
        if not hmac.compare_digest(api_key, self.api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        
        # Parse timestamp
        try:
            timestamp = float(timestamp_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format",
            )
        
        # Check timestamp freshness
        current_time = time.time()
        if abs(current_time - timestamp) > self.max_age:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Request timestamp is too old or in the future",
                headers={"X-Timestamp-Now": str(current_time)},
            )
        
        # Read request body
        body = await request.body()
        body_str = body.decode() if body else ""
        
        # Recreate the message that was signed
        method = request.method
        path = request.url.path
        message = self._create_message(method, path, body_str, timestamp)
        
        # Verify the signature
        expected_signature = self._sign_message(message)
        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature",
            )
        
        return True
    
    def _create_message(
        self, method: str, path: str, body: str, timestamp: float
    ) -> str:
        """Create the message to be signed."""
        # Normalize method and path
        method = method.upper()
        path = path.rstrip("/") or "/"
        
        # Create message components
        components = [
            method,
            path,
            str(timestamp),
            hashlib.sha256(body.encode()).hexdigest() if body else "",
        ]
        
        # Join with newlines to prevent injection
        return "\n".join(components)
    
    def _sign_message(self, message: str) -> str:
        """Sign a message using HMAC-SHA256."""
        if isinstance(self.api_secret, str):
            secret = self.api_secret.encode()
        else:
            secret = self.api_secret
            
        signature = hmac.new(
            key=secret,
            msg=message.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return signature


# Global request signer instance
_request_signer = None

def get_request_signer() -> RequestSigner:
    """Get or create a request signer instance."""
    global _request_signer
    if _request_signer is None:
        _request_signer = RequestSigner(
            api_key=settings.API_KEY,
            api_secret=settings.API_SECRET,
            max_age=getattr(settings, 'REQUEST_SIGNING_MAX_AGE', 300),
        )
    return _request_signer
