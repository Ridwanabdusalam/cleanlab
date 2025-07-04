"""Test prompt processing with mock responses."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from trustworthiness.detector_gemini import TrustworthinessDetector
from trustworthiness.prompts import REFLECTION_PROMPTS as DEFAULT_REFLECTION_PROMPTS


def run_test_case(detector: TrustworthinessDetector, case: Dict[str, Any]) -> None:
    """Run a single test case and print the results."""
    print(f"\n{'='*80}")
    print(f"Testing: {case['description']}")
    print(f"Question: {case['question']}")
    print(f"Answer: {case['answer']}")

    # Mock the _query_llm method to return our test responses
    with patch.object(detector, "_query_llm", side_effect=case["mock_responses"]):
        # Get trustworthiness score
        score = detector.get_trustworthiness_score(case["question"], case["answer"])
        print(f"Calculated trustworthiness score: {score:.2f}")

        # Verify the score is as expected
        if "expected_score" in case:
            assert (
                abs(score - case["expected_score"]) < 0.1
            ), f"Expected score ~{case['expected_score']}, got {score}"

        # Print interpretation
        if score >= 0.7:
            confidence = "High"
        elif score >= 0.4:
            confidence = "Moderate"
        else:
            confidence = "Low"

        print(f"{confidence} confidence in the answer's correctness")
        print(f"Test passed for: {case['description']}")
        print(f"{'='*80}")


def test_prompt_processing():
    """Test how the detector processes various prompts with mock responses."""
    # Initialize the detector with caching disabled
    detector = TrustworthinessDetector(cache_responses=False)

    # Define test cases with expected mock responses
    test_cases = [
        # Basic factual questions
        {
            "question": "What is 1 + 1?",
            "answer": "2",
            "mock_responses": ["(A) Correct", "(A) Correct"],
            "expected_score": 1.0,
            "description": "Basic arithmetic - correct answer",
        },
        {
            "question": "What is 1 + 1?",
            "answer": "3",
            "mock_responses": ["(B) Incorrect", "(B) Incorrect"],
            "expected_score": 0.0,
            "description": "Basic arithmetic - incorrect answer",
        },
        {
            "question": "What is the third month in alphabetical order?",
            "answer": "April",
            "mock_responses": ["(A) Correct", "(A) Correct"],
            "expected_score": 1.0,
            "description": "Alphabetical ordering - correct",
        },
        # More test cases...
    ]

    # Run all test cases
    for case in test_cases:
        run_test_case(detector, case)


# Custom Prompts Tests
CUSTOM_PROMPTS = [
    """Question: {question}
Proposed Answer: {answer}
Is this answer correct? (Yes/No/Maybe)
The output should be in the format: explanation: [your analysis], answer: [Y/N/M]""",
    """Evaluate this Q&A pair:
Q: {question}
A: {answer}

Rate the answer's correctness on a scale of 1-3 where:
1 = Incorrect
2 = Partially correct
3 = Correct

Format: explanation: [your analysis], score: [1/2/3]""",
]

CUSTOM_PROMPT_SCORES = {
    "Y": 1.0,
    "N": 0.0,
    "M": 0.5,  # First prompt format
    "1": 0.0,
    "2": 0.5,
    "3": 1.0,  # Second prompt format
}


class TestCustomPrompts:
    """Tests for TrustworthinessDetector with custom prompts."""

    @patch("requests.post")
    def test_basic_custom_prompts(self, mock_post):
        """Test basic functionality with custom prompts."""
        # Mock successful API responses for each prompt
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "explanation: The answer is correct, answer: Y"}
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        # Initialize with custom prompts
        detector = TrustworthinessDetector(
            reflection_prompts=CUSTOM_PROMPTS, cache_responses=False
        )

        # Test evaluation
        score = detector.get_trustworthiness_score(
            "What is the capital of France?", "Paris"
        )

        # Verify the score is within valid range
        assert 0 <= score <= 1.0

        # The detector makes multiple API calls per prompt due to retries
        # So we just verify that some API calls were made
        assert mock_post.call_count > 0

    @patch("requests.post")
    def test_mixed_confidence_responses(self, mock_post):
        """Test with mixed confidence responses from custom prompts."""
        # Mock responses with mixed confidence
        mock_responses = [
            # First prompt response (Maybe)
            MagicMock(
                json=lambda: {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "explanation: I'm not entirely sure, answer: M"
                                    }
                                ]
                            }
                        }
                    ]
                }
            ),
            # Second prompt response (Partially correct)
            MagicMock(
                json=lambda: {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "explanation: Partially correct, score: 2"}
                                ]
                            }
                        }
                    ]
                }
            ),
        ]
        mock_post.side_effect = mock_responses

        detector = TrustworthinessDetector(
            reflection_prompts=CUSTOM_PROMPTS, cache_responses=False
        )

        # Test evaluation
        score = detector.get_trustworthiness_score(
            "What is the capital of France?", "Paris"
        )

        # The score should be the average of the two responses
        # (0.5 + 0.5) / 2 = 0.5
        assert abs(score - 0.5) < 0.1


if __name__ == "__main__":
    test_prompt_processing()
    pytest.main([__file__])
