"""
Tests for batch processing functionality of the Trustworthiness Detector.
"""

from unittest.mock import ANY, MagicMock, patch

import pytest

from src.trustworthiness import TrustworthinessDetector

# Sample data for testing
SAMPLE_QUESTIONS = [
    "What is the capital of France?",
    "Who wrote 'To Kill a Mockingbird'?",
    "What is the chemical symbol for gold?",
]

SAMPLE_ANSWERS = ["Paris", "Harper Lee", "Au"]

# Expected mock responses for each prompt
MOCK_RESPONSES = [
    {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "explanation: The answer is correct, answer: Y"}]
                }
            }
        ]
    },
    {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "explanation: The answer is correct, answer: Y"}]
                }
            }
        ]
    },
    {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "explanation: The answer is correct, answer: Y"}]
                }
            }
        ]
    },
]


class TestBatchProcessing:
    """Test batch processing functionality of TrustworthinessDetector."""

    @patch("requests.post")
    def test_batch_evaluation(self, mock_post):
        """Test batch evaluation of multiple Q&A pairs."""
        # Set up mock responses
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSES[
            0
        ]  # Use the first mock response for all calls
        mock_post.return_value = mock_response

        # Initialize detector with caching disabled for testing
        detector = TrustworthinessDetector(cache_responses=False)

        # Evaluate batch
        results = detector.evaluate_trustworthiness_batch(
            SAMPLE_QUESTIONS, SAMPLE_ANSWERS
        )

        # Verify results
        assert len(results) == len(SAMPLE_QUESTIONS)
        for score in results:
            assert 0 <= score <= 1.0

        # Each question gets processed with all reflection prompts
        # Each prompt makes 3 API calls (2 retries + 1 success)
        expected_calls = len(SAMPLE_QUESTIONS) * len(detector.reflection_prompts) * 3
        assert (
            mock_post.call_count == expected_calls
        ), f"Expected {expected_calls} API calls, got {mock_post.call_count}"

    @patch("requests.post")
    def test_batch_with_different_lengths(self, mock_post):
        """Test batch evaluation with mismatched question and answer lengths."""
        detector = TrustworthinessDetector()

        with pytest.raises(ValueError):
            detector.evaluate_trustworthiness_batch(
                ["Q1", "Q2"], ["A1"]  # 2 questions  # 1 answer
            )

    @patch("requests.post")
    def test_empty_batch(self, mock_post):
        """Test batch evaluation with empty input."""
        detector = TrustworthinessDetector()

        # Empty input should return empty output
        results = detector.evaluate_trustworthiness_batch([], [])
        assert results == []

        # No API calls should be made
        assert mock_post.call_count == 0

    @patch("requests.post")
    def test_batch_with_custom_prompts(self, mock_post):
        """Test batch evaluation with custom prompts."""
        # Set up mock responses
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_RESPONSES[
            0
        ]  # Use the first mock response for all calls
        mock_post.return_value = mock_response

        # Custom prompts
        custom_prompts = [
            "Q: {question}\nA: {answer}\nIs this correct? (Y/N/M)",
            "Evaluate: {question}\nAnswer: {answer}\nScore (1-3):",
        ]

        # Initialize with custom prompts
        detector = TrustworthinessDetector(
            reflection_prompts=custom_prompts, cache_responses=False
        )

        # Evaluate batch
        results = detector.evaluate_trustworthiness_batch(
            SAMPLE_QUESTIONS, SAMPLE_ANSWERS
        )

        # Verify results
        assert len(results) == len(SAMPLE_QUESTIONS)
        for score in results:
            assert 0 <= score <= 1.0

        # Each question gets processed with all custom prompts
        # Each prompt makes 3 API calls (2 retries + 1 success)
        expected_calls = len(SAMPLE_QUESTIONS) * len(custom_prompts) * 3
        assert (
            mock_post.call_count == expected_calls
        ), f"Expected {expected_calls} API calls, got {mock_post.call_count}"

    @patch("requests.post")
    def test_batch_with_retries(self, mock_post):
        """Test batch evaluation with retry logic."""
        # Set up mock to fail twice then succeed for each prompt
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = MOCK_RESPONSES[0]

        mock_response_failure = MagicMock()
        mock_response_failure.raise_for_status.side_effect = Exception("API error")

        # First two calls fail, third succeeds for each prompt
        # We need to account for the retry logic in the _query_llm method
        mock_post.side_effect = [
            # First prompt: 3 attempts (2 failures + 1 success)
            mock_response_failure,
            mock_response_failure,
            mock_response_success,
            # Second prompt: 3 attempts (2 failures + 1 success)
            mock_response_failure,
            mock_response_failure,
            mock_response_success,
        ]

        # Mock the sleep function to speed up the test
        with patch("time.sleep"):
            # Use a single custom prompt to simplify the test
            detector = TrustworthinessDetector(
                reflection_prompts=["Test prompt"], cache_responses=False
            )

            # Single Q&A pair
            results = detector.evaluate_trustworthiness_batch(
                [SAMPLE_QUESTIONS[0]], [SAMPLE_ANSWERS[0]]
            )

            # Should eventually succeed
            assert len(results) == 1
            assert 0 <= results[0] <= 1.0

            # Should have made 3 API calls (2 failures + 1 success)
            assert (
                mock_post.call_count == 3
            ), f"Expected 3 API calls, got {mock_post.call_count}"
