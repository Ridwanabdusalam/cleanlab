"""
Audit logging for security-relevant events.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..config import settings


class AuditLogger:
    """Logs security-relevant events for auditing purposes."""

    def __init__(self, log_file: Optional[str] = None):
        """Initialize the audit logger.
        
        Args:
            log_file: Path to the audit log file. If None, logs to stderr.
        """
        self.logger = logging.getLogger("trustworthiness.audit")
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            if log_file:
                # Create log directory if it doesn't exist
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Use RotatingFileHandler with 5MB max size, keeping 5 backup files
                handler = logging.handlers.RotatingFileHandler(
                    filename=log_file,
                    maxBytes=5 * 1024 * 1024,  # 5MB
                    backupCount=5,
                    encoding='utf-8',
                )
            else:
                handler = logging.StreamHandler()
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_event(
        self,
        event_type: str,
        message: str,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Log a security event.
        
        Args:
            event_type: Type of event (e.g., 'auth.success', 'auth.failure', 'request')
            message: Human-readable description of the event
            user: Username or user ID associated with the event
            ip_address: IP address of the client
            request_id: Unique request identifier
            **extra: Additional context data to include in the log
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
        }
        
        # Add optional fields if provided
        if user is not None:
            log_entry["user"] = user
        if ip_address is not None:
            log_entry["ip_address"] = ip_address
        if request_id is not None:
            log_entry["request_id"] = request_id
        
        # Add any extra context
        log_entry.update(extra)
        
        # Log the event as JSON
        self.logger.info(json.dumps(log_entry))
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Log an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP status code
            user: Username or user ID
            ip_address: Client IP address
            request_id: Unique request identifier
            **extra: Additional context data
        """
        self.log_event(
            event_type="request",
            message=f"{method} {path} -> {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            user=user,
            ip_address=ip_address,
            request_id=request_id,
            **extra
        )
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        **extra: Any
    ) -> None:
        """Log a security-related event.
        
        Args:
            event_type: Type of security event (e.g., 'auth.failure', 'xss.attempt')
            message: Description of the event
            severity: Severity level (debug, info, warning, error, critical)
            user: Username or user ID
            ip_address: Client IP address
            **extra: Additional context data
        """
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": f"security.{event_type}",
            "severity": severity.upper(),
            "message": message,
        }
        
        if user is not None:
            log_entry["user"] = user
        if ip_address is not None:
            log_entry["ip_address"] = ip_address
        
        log_entry.update(extra)
        
        log_method(json.dumps(log_entry))


# Global audit logger instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(
            log_file=getattr(settings, 'AUDIT_LOG_PATH', None)
        )
    return _audit_logger
