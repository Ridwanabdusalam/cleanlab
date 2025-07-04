"""
Trustworthiness Detector for LLM outputs.

This package provides functionality to evaluate the trustworthiness of LLM answers
using self-reflection certainty based on the BSDetector paper.
"""

from .config import settings, validate_model_api_key
from .detector import TrustworthinessDetector as BaseTrustworthinessDetector
from .detector_gemini import TrustworthinessDetector as GeminiTrustworthinessDetector, evaluate_trustworthiness
from .prompts import REFLECTION_PROMPTS
from .models import (
    TrustScore,
    ScoreExplanation,
    EvaluationRequest,
    BatchEvaluationRequest,
    EvaluationResponse,
    ScoringFunctionType,
    ScoringFunction
)
from . import security
from .api import get_application

# For backward compatibility
DEFAULT_MODEL = settings.DEFAULT_MODEL
GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_API_URL = str(settings.GEMINI_API_URL)
RATE_LIMIT_JITTER = settings.RATE_LIMIT_JITTER
RATE_LIMIT_MAX_REQUESTS = settings.RATE_LIMIT_MAX_REQUESTS
RATE_LIMIT_MAX_RETRIES = settings.RATE_LIMIT_MAX_RETRIES
RATE_LIMIT_TIME_WINDOW = settings.RATE_LIMIT_TIME_WINDOW

__version__ = "0.2.0"

__all__ = [
    # Main classes
    "BaseTrustworthinessDetector",
    "GeminiTrustworthinessDetector",
    "TrustworthinessDetector",  # Alias for backward compatibility
    
    # Core functions
    "evaluate_trustworthiness",
    "get_application",
    
    # Models
    "TrustScore",
    "ScoreExplanation",
    "EvaluationRequest",
    "BatchEvaluationRequest",
    "EvaluationResponse",
    "ScoringFunctionType",
    "ScoringFunction",
    
    # Configuration
    "DEFAULT_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_API_URL",
    "RATE_LIMIT_MAX_REQUESTS",
    "RATE_LIMIT_TIME_WINDOW",
    "RATE_LIMIT_JITTER",
    "validate_model_api_key",
    
    # Prompts
    "REFLECTION_PROMPTS",
    
    # Security
    "security"
]

# Backward compatibility
TrustworthinessDetector = GeminiTrustworthinessDetector
