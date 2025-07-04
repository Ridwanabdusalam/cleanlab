"""
Data models for the Trustworthiness Detector API.
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, validator

from ..models import (
    EvaluationRequest as BaseEvaluationRequest,
    EvaluationResponse as BaseEvaluationResponse,
    BatchEvaluationRequest as BaseBatchEvaluationRequest,
    TrustScore,
    ScoreExplanation,
    ScoringFunction
)

# Re-export base models for convenience
EvaluationRequest = BaseEvaluationRequest
BatchEvaluationRequest = BaseBatchEvaluationRequest
EvaluationResponse = BaseEvaluationResponse

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    uptime: float = Field(..., description="Uptime in seconds")
    dependencies: Dict[str, str] = Field(
        default_factory=dict, 
        description="Dependency statuses"
    )


class StatsResponse(BaseModel):
    """System statistics response model."""
    request_count: int = Field(..., description="Total number of requests")
    avg_latency: float = Field(..., description="Average request latency in seconds")
    error_rate: float = Field(..., description="Error rate (0-1)")
    trust_score_avg: float = Field(..., description="Average trust score")
    system: Dict[str, Any] = Field(..., description="System metrics")


class ScoringFunctionRegister(BaseModel):
    """Model for registering a new scoring function."""
    name: str = Field(..., description="Unique name for the scoring function")
    description: str = Field("", description="Description of the scoring function")
    code: str = Field(..., description="Python code for the scoring function")
    overwrite: bool = Field(False, description="Whether to overwrite if exists")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error details"
    )


class StreamUpdateType(str, Enum):
    """Types of stream updates."""
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"


class StreamUpdate(BaseModel):
    """Model for streaming updates."""
    type: StreamUpdateType = Field(..., description="Type of update")
    data: Dict[str, Any] = Field(..., description="Update data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Update timestamp"
    )


class BatchProgress(BaseModel):
    """Batch processing progress model."""
    total: int = Field(..., description="Total number of items")
    processed: int = Field(..., description="Number of items processed")
    successful: int = Field(..., description="Number of successful items")
    failed: int = Field(..., description="Number of failed items")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0-1)")


class BatchResult(BaseModel):
    """Batch processing result model."""
    request_id: str = Field(..., description="Batch request ID")
    status: str = Field(..., description="Batch status")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    progress: BatchProgress = Field(..., description="Processing progress")
    results: List[Union[EvaluationResponse, ErrorResponse]] = Field(
        default_factory=list,
        description="Processing results"
    )


class RateLimitHeaders(BaseModel):
    """Rate limit headers model."""
    x_ratelimit_limit: int = Field(..., alias="X-RateLimit-Limit")
    x_ratelimit_remaining: int = Field(..., alias="X-RateLimit-Remaining")
    x_ratelimit_reset: int = Field(..., alias="X-RateLimit-Reset")
    retry_after: Optional[int] = Field(None, alias="Retry-After")

    class Config:
        allow_population_by_field_name = True
