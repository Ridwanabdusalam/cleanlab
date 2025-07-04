"""
Scoring function management for the Trustworthiness Detector API.
"""
from typing import Dict, List, Any, Callable, Optional, TypeVar, Union
import inspect
import logging
from functools import wraps

from ..models import (
    ScoringFunction,
    EvaluationRequest,
    EvaluationResponse,
    TrustScore,
    ScoreExplanation
)
from .models import BatchEvaluationRequest

logger = logging.getLogger(__name__)

# Registry of available scoring functions
SCORING_FUNCTIONS: Dict[str, ScoringFunction] = {}

T = TypeVar('T')

def register_scoring_function(
    name: str,
    description: str = "",
    overwrite: bool = False
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to register a custom scoring function.
    
    Args:
        name: Unique name for the scoring function
        description: Description of what the scoring function does
        overwrite: Whether to overwrite an existing function with the same name
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if not overwrite and name in SCORING_FUNCTIONS:
            raise ValueError(f"Scoring function '{name}' already exists")
        
        # Create a scoring function instance
        scoring_fn = ScoringFunction(
            name=name,
            description=description or func.__doc__ or "",
            function=func
        )
        
        # Register the function
        SCORING_FUNCTIONS[name] = scoring_fn
        logger.info(f"Registered scoring function: {name}")
        
        # Return the original function
        return func
    
    return decorator


def get_scoring_function(name: str) -> Optional[ScoringFunction]:
    """
    Get a scoring function by name.
    
    Args:
        name: Name of the scoring function
        
    Returns:
        ScoringFunction instance or None if not found
    """
    return SCORING_FUNCTIONS.get(name)


def list_scoring_functions() -> Dict[str, str]:
    """
    List all available scoring functions.
    
    Returns:
        Dictionary mapping function names to their descriptions
    """
    return {name: fn.description for name, fn in SCORING_FUNCTIONS.items()}


# Default scoring functions
@register_scoring_function(
    name="default",
    description="Default scoring function that returns a fixed score of 0.8"
)
async def default_scoring_function(request: EvaluationRequest) -> float:
    """Default scoring function that returns a fixed score."""
    return 0.8


@register_scoring_function(
    name="length_based",
    description="Scores based on answer length (longer answers get higher scores)"
)
async def length_based_scoring(request: EvaluationRequest) -> float:
    """Score based on answer length."""
    # Normalize length to 0-1 range (capped at 1000 characters)
    length = len(request.answer)
    return min(length / 1000, 1.0)


@register_scoring_function(
    name="keyword_matching",
    description="Scores based on presence of certain keywords in the answer"
)
async def keyword_matching_scoring(request: EvaluationRequest) -> float:
    """Score based on presence of certain keywords."""
    keywords = ["confident", "certain", "sure", "definitely", "clearly"]
    answer = request.answer.lower()
    
    # Count matching keywords
    matches = sum(1 for kw in keywords if kw in answer)
    
    # Return score based on number of matches
    return min(matches * 0.2, 1.0)


async def apply_scoring_function(
    request: EvaluationRequest,
    scoring_fn_name: Optional[str] = None
) -> float:
    """
    Apply a scoring function to an evaluation request.
    
    Args:
        request: Evaluation request
        scoring_fn_name: Optional name of the scoring function to use
        
    Returns:
        Score between 0 and 1
        
    Raises:
        ValueError: If the scoring function is not found
    """
    if not scoring_fn_name or scoring_fn_name == "default":
        scoring_fn = SCORING_FUNCTIONS["default"]
    else:
        scoring_fn = get_scoring_function(scoring_fn_name)
        if not scoring_fn:
            raise ValueError(f"Unknown scoring function: {scoring_fn_name}")
    
    # Call the scoring function
    try:
        score = await scoring_fn.function(request)
        # Ensure the score is between 0 and 1
        return max(0.0, min(1.0, float(score)))
    except Exception as e:
        logger.error(f"Error in scoring function '{scoring_fn.name}': {e}")
        # Fall back to default scoring on error
        default_fn = SCORING_FUNCTIONS["default"]
        return await default_fn.function(request)
