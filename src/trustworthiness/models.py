"""
Data models for the Trustworthiness Detector.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from pydantic import BaseModel, Field, field_validator, ConfigDict, EmailStr
from enum import Enum
import numpy as np

T = TypeVar('T')

class ScoreExplanation(BaseModel):
    """Detailed explanation of the trust score."""
    score: float = Field(..., ge=0.0, le=1.0, description="The normalized trust score between 0 and 1")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of the score")
    reasoning: str = Field(..., description="Human-readable explanation of the score")
    factors: Dict[str, float] = Field(
        default_factory=dict, 
        description="Individual factor contributions to the score"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "score": 0.85,
                "confidence": 0.92,
                "reasoning": "The answer is factually accurate and well-supported by the context.",
                "factors": {
                    "factual_accuracy": 0.9,
                    "relevance": 0.8,
                    "completeness": 0.85
                }
            }
        }
    )


class TrustScore(BaseModel):
    """Trust score with confidence intervals and explanation."""
    score: float = Field(..., ge=0.0, le=1.0, description="The normalized trust score between 0 and 1")
    confidence_interval: tuple[float, float] = Field(
        ..., 
        description="95% confidence interval for the score (lower, upper)"
    )
    explanation: ScoreExplanation = Field(..., description="Detailed explanation of the score")
    
    @property
    def lower_bound(self) -> float:
        """Get the lower bound of the confidence interval."""
        return self.confidence_interval[0]
    
    @property
    def upper_bound(self) -> float:
        """Get the upper bound of the confidence interval."""
        return self.confidence_interval[1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with flattened structure."""
        return {
            "score": self.score,
            "confidence_interval_lower": self.lower_bound,
            "confidence_interval_upper": self.upper_bound,
            "explanation": self.explanation.model_dump()
        }


class EvaluationRequest(BaseModel):
    """Request model for trust evaluation."""
    question: str = Field(..., min_length=1, description="The question being asked")
    answer: str = Field(..., min_length=1, description="The answer to evaluate")
    context: Optional[str] = Field(
        None, 
        description="Optional context or additional information"
    )
    custom_scoring_fn: Optional[str] = Field(
        None,
        description="Optional name of a custom scoring function to use"
    )
    
    @field_validator('question', 'answer', mode='before')
    @classmethod
    def validate_strings(cls, v: Any) -> str:
        """Validate and clean string fields."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class BatchEvaluationRequest(BaseModel):
    """Request model for batch trust evaluation."""
    items: List[EvaluationRequest] = Field(
        ...,
        min_items=1,
        description="List of evaluation requests"
    )
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v: List[EvaluationRequest]) -> List[EvaluationRequest]:
        """Validate batch size limits."""
        if len(v) > 100:  # Arbitrary batch size limit
            raise ValueError("Batch size cannot exceed 100 items")
        return v


class EvaluationResponse(BaseModel):
    """Response model for trust evaluation."""
    question: str
    answer: str
    trust_score: TrustScore
    context: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the capital of France?",
                "answer": "Paris",
                "trust_score": {
                    "score": 0.95,
                    "confidence_interval": [0.9, 0.98],
                    "explanation": {
                        "score": 0.95,
                        "confidence": 0.92,
                        "reasoning": "The answer is factually correct and matches the context.",
                        "factors": {
                            "factual_accuracy": 0.95,
                            "relevance": 0.95,
                            "completeness": 0.9
                        }
                    }
                }
            }
        }


class ScoringFunctionType(str, Enum):
    """Available scoring function types."""
    DEFAULT = "default"
    STRICT = "strict"
    LENIENT = "lenient"
    CUSTOM = "custom"


class ScoringFunction(BaseModel, Generic[T]):
    """Base class for custom scoring functions."""
    name: str
    description: str
    function: Callable[..., T]
    
    def __call__(self, *args, **kwargs) -> T:
        """Call the scoring function."""
        return self.function(*args, **kwargs)
    
    @classmethod
    def from_callable(
        cls, 
        name: str,
        description: str = "",
    ) -> Callable[[Callable[..., T]], 'ScoringFunction']:
        """Create a scoring function from a callable."""
        def decorator(func: Callable[..., T]) -> 'ScoringFunction':
            return cls(
                name=name,
                description=description or func.__doc__ or "",
                function=func
            )
        return decorator

    @classmethod
    def decorator(
        cls, 
        func: Callable[..., T]
    ) -> 'ScoringFunction':
        """Decorator to create a scoring function from a callable."""
        return cls(
            name=func.__name__,
            description=func.__doc__ or "",
            function=func
        )


class TokenData(BaseModel):
    """Token data model for JWT authentication."""
    username: Optional[str] = None
    scopes: List[str] = []


class User(BaseModel):
    """User model for authentication."""
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    hashed_password: str
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.hashed_password)
    
    def get_password_hash(self) -> str:
        """Generate a password hash."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(self.hashed_password)
