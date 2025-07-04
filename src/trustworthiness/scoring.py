"""
Scoring functions for evaluating answer trustworthiness.
"""
from typing import Dict, List, Optional, Callable, Any
import numpy as np

from .models import ScoringFunction, ScoreExplanation, TrustScore

# Registry for custom scoring functions
SCORING_FUNCTIONS: Dict[str, ScoringFunction] = {}

def register_scoring_function(name: str, description: str = "") -> Callable:
    """Decorator to register a custom scoring function.
    
    Args:
        name: Unique name for the scoring function
        description: Optional description of the function
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        SCORING_FUNCTIONS[name] = ScoringFunction(
            name=name,
            description=description or func.__doc__ or "",
            function=func
        )
        return func
    return decorator

def get_scoring_function(name: str) -> Optional[ScoringFunction]:
    """Get a registered scoring function by name.
    
    Args:
        name: Name of the scoring function
        
    Returns:
        ScoringFunction instance or None if not found
    """
    return SCORING_FUNCTIONS.get(name)

def list_scoring_functions() -> Dict[str, str]:
    """List all registered scoring functions.
    
    Returns:
        Dictionary mapping function names to their descriptions
    """
    return {name: func.description for name, func in SCORING_FUNCTIONS.items()}

# Built-in scoring functions
@register_scoring_function(
    name="default",
    description="Default scoring function that balances accuracy and relevance"
)
async def default_scoring(
    question: str,
    answer: str,
    context: Optional[str] = None,
    **kwargs
) -> TrustScore:
    """Default scoring function that evaluates answer trustworthiness."""
    # This is a simplified example - in practice, you'd use more sophisticated logic
    # Here we'll use some simple heuristics for demonstration
    
    # Calculate base score components
    factors = {
        "answer_length_score": min(len(answer) / 100, 1.0),  # Prefer longer answers
        "question_coverage": min(len(answer) / (len(question) * 2), 1.0),  # Answer should be proportional to question
    }
    
    if context:
        # If context is provided, check if answer is consistent with it
        context_similarity = min(
            sum(1 for word in answer.lower().split() if word in context.lower()) / 
            max(1, len(answer.split())),
            1.0
        )
        factors["context_relevance"] = context_similarity
    
    # Calculate final score as weighted average of factors
    weights = {
        "answer_length_score": 0.3,
        "question_coverage": 0.4,
        "context_relevance": 0.3 if context else 0.0
    }
    
    score = sum(factors[factor] * weight 
               for factor, weight in weights.items() 
               if factor in factors)
    
    # Add some noise to simulate confidence intervals
    confidence = 0.8 + (np.random.random() * 0.2)  # 0.8-1.0 confidence
    margin = (1 - score) * 0.2  # Wider margin for lower scores
    lower = max(0, score - margin)
    upper = min(1, score + margin)
    
    return TrustScore(
        score=float(score),
        confidence_interval=(float(lower), float(upper)),
        explanation=ScoreExplanation(
            score=float(score),
            confidence=float(confidence),
            reasoning="Score based on answer length, question coverage, and context relevance",
            factors={k: float(v) for k, v in factors.items()}
        )
    )

@register_scoring_function(
    name="strict",
    description="Strict scoring that penalizes short or vague answers"
)
async def strict_scoring(
    question: str,
    answer: str,
    context: Optional[str] = None,
    **kwargs
) -> TrustScore:
    """Strict scoring function that penalizes short or vague answers."""
    # Get default score first
    default_result = await default_scoring(question, answer, context, **kwargs)
    
    # Apply stricter penalties
    factors = default_result.explanation.factors
    
    # Penalize short answers more heavily
    length_penalty = 0.5 if len(answer) < 30 else 1.0
    
    # Update score with penalties
    score = default_result.score * length_penalty
    
    return TrustScore(
        score=float(score),
        confidence_interval=(
            max(0, default_result.lower_bound * length_penalty),
            min(1, default_result.upper_bound * length_penalty)
        ),
        explanation=ScoreExplanation(
            score=float(score),
            confidence=default_result.explanation.confidence,
            reasoning=("Strict scoring applied. " + 
                      default_result.explanation.reasoning),
            factors={
                **{k: float(v) for k, v in factors.items()},
                "length_penalty": length_penalty
            }
        )
    )

# Example of a custom scoring function that could be registered at runtime
def create_custom_scoring(
    weights: Dict[str, float],
    min_length: int = 10,
    max_length: int = 1000
) -> Callable:
    """Create a custom scoring function with the given weights.
    
    Args:
        weights: Dictionary of factor weights
        min_length: Minimum answer length to consider
        max_length: Maximum answer length to consider
        
    Returns:
        A scoring function
    """
    async def custom_scoring(
        question: str,
        answer: str,
        context: Optional[str] = None,
        **kwargs
    ) -> TrustScore:
        # Simple custom scoring based on provided weights
        factors = {
            "length_score": min(max(len(answer) / max_length, 0), 1),
            "question_terms": min(len(set(question.lower().split()) & 
                                  set(answer.lower().split())) / 
                                 max(1, len(question.split())), 1),
        }
        
        if context:
            factors["context_similarity"] = min(
                len(set(answer.lower().split()) & set(context.lower().split())) /
                max(1, len(set(answer.lower().split()))),
                1.0
            )
        
        # Apply weights
        total_weight = sum(weights.values())
        if total_weight == 0:
            total_weight = 1
            
        score = sum(factors.get(factor, 0) * (weights.get(factor, 0) / total_weight)
                   for factor in set(factors) | set(weights))
        
        return TrustScore(
            score=float(score),
            confidence_interval=(
                max(0, score - 0.1),
                min(1, score + 0.1)
            ),
            explanation=ScoreExplanation(
                score=float(score),
                confidence=0.9,
                reasoning="Custom scoring based on provided weights",
                factors=factors
            )
        )
    
    return custom_scoring
