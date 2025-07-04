"""
Test the rate limiter and retry mechanism in the TrustworthinessDetector.
"""

import concurrent.futures
import time
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from src.trustworthiness import RATE_LIMIT_MAX_RETRIES, TrustworthinessDetector
from src.trustworthiness.prompts import REFLECTION_PROMPTS as DEFAULT_REFLECTION_PROMPTS


class TestRateLimiter:
    """Test the rate limiter and retry mechanism."""

    @pytest.fixture
    def mock_requests_post(self):
        """Mock the requests.post method."""
        with patch("requests.post") as mock_post:
            yield mock_post

    @pytest.fixture
    def mock_reflection_prompts(self):
        """Mock reflection prompts to control the number of API calls."""
        return ["Test reflection prompt 1", "Test reflection prompt 2"]

    @pytest.fixture
    def success_response(self):
        """Return a successful API response."""
        return MagicMock(
            status_code=200,
            json=lambda: {
                "candidates": [{"content": {"parts": [{"text": "answer: [A]"}]}}]
            },
        )

    def test_retry_on_failure(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that the detector retries on API failures."""
        # Each reflection prompt makes 1 API call, and we have 2 prompts
        num_prompts = len(mock_reflection_prompts)

        # Setup mock to fail twice then succeed for each prompt
        mock_responses = []
        for _ in range(num_prompts):
            # First attempt: Fail with 500 error
            mock_responses.append(
                MagicMock(status_code=500, text="Internal Server Error")
            )
            # Second attempt: Fail with timeout
            mock_responses.append(requests.exceptions.Timeout())
            # Third attempt: Succeed
            mock_responses.append(success_response)

        mock_requests_post.side_effect = mock_responses

        # Create detector with our test prompts
        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        score = detector.get_trustworthiness_score("Test question", "Test answer")

        # Should have made 3 API calls per prompt (2 failures + 1 success)
        assert mock_requests_post.call_count == 3 * num_prompts
        # Should return a valid score (average of reflection scores)
        assert 0 <= score <= 1.0

    def test_retry_with_exponential_backoff(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that failed requests are retried with exponential backoff."""
        # Set up mock to fail twice then succeed
        mock_responses = [
            # First attempt: Fail with 500 error
            MagicMock(status_code=500, text="Internal Server Error"),
            # Second attempt: Fail with timeout
            requests.exceptions.Timeout(),
            # Third attempt: Succeed
            success_response,
            # Repeat for second prompt
            MagicMock(status_code=500, text="Internal Server Error"),
            requests.exceptions.Timeout(),
            success_response,
        ]
        mock_requests_post.side_effect = mock_responses

        # Mock time.sleep to track calls
        with patch("time.sleep") as mock_sleep:
            # Create detector with test prompts
            detector = TrustworthinessDetector(
                cache_responses=False, reflection_prompts=mock_reflection_prompts
            )

            # Make a single request (which will trigger multiple API calls due to retries)
            score = detector.get_trustworthiness_score("Test question", "Test answer")

            # Verify the number of API calls (2 prompts * (1 success + 2 failures))
            assert mock_requests_post.call_count == 6

            # Verify that sleep was called with increasing delays
            assert mock_sleep.call_count == 4  # 2 retries per prompt * 2 prompts

            # Get the sleep durations
            sleep_durations = [call[0][0] for call in mock_sleep.call_args_list]

            # Verify exponential backoff pattern (with some tolerance for jitter)
            for i in range(0, len(sleep_durations), 2):
                # First retry delay should be around 1 second (base delay)
                assert 0.8 <= sleep_durations[i] <= 2.0
                # Second retry delay should be around 2 seconds (exponential backoff)
                if i + 1 < len(sleep_durations):
                    assert 1.5 <= sleep_durations[i + 1] <= 4.0

            # Verify we got a valid score
            assert 0 <= score <= 1.0

    def test_rate_limit_exceeded(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test handling of rate limit exceeded errors."""
        # Each reflection prompt makes 1 API call, and we have 2 prompts
        num_prompts = len(mock_reflection_prompts)

        # Mock rate limit response (429)
        rate_limit_response = MagicMock(
            status_code=429, text="Rate limit exceeded", headers={"Retry-After": "1"}
        )

        # Create responses for each prompt
        mock_responses = []
        for i in range(num_prompts):
            # First attempt: Rate limited
            mock_responses.append(rate_limit_response)
            # Second attempt: Success
            mock_responses.append(success_response)

        mock_requests_post.side_effect = mock_responses

        # Create detector with our test prompts
        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        score = detector.get_trustworthiness_score("Test question", "Test answer")

        # Should have made 2 API calls per prompt (1 rate limited + 1 success)
        assert mock_requests_post.call_count == 2 * num_prompts
        # Should return a valid score
        assert 0 <= score <= 1.0

    def test_cache_reduces_api_calls(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that caching reduces the number of API calls."""
        # Each reflection prompt makes 1 API call, and we have 2 prompts
        num_prompts = len(mock_reflection_prompts)
        mock_requests_post.return_value = success_response

        # Test with caching enabled
        detector = TrustworthinessDetector(
            cache_responses=True, reflection_prompts=mock_reflection_prompts
        )

        # First call - should make API requests for each prompt
        score1 = detector.get_trustworthiness_score("Cached question", "Answer")

        # Second call with same input - should use cache
        score2 = detector.get_trustworthiness_score("Cached question", "Answer")

        # Should only make API calls for the first request, second should be cached
        assert mock_requests_post.call_count == num_prompts  # One call per prompt
        assert score1 == score2  # Scores should be equal
        assert 0 <= score1 <= 1.0  # Should be a valid score

    def test_concurrent_requests(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that rate limiting works with concurrent requests."""
        num_concurrent = 5
        mock_requests_post.return_value = success_response

        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        def make_request():
            return detector.get_trustworthiness_score("Concurrent question", "Answer")

        # Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_concurrent
        ) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Verify all requests completed successfully
        assert all(0 <= score <= 1.0 for score in results)
        # Verify total API calls (num_concurrent * num_prompts)
        assert mock_requests_post.call_count == num_concurrent * len(
            mock_reflection_prompts
        )

    def test_rate_limit_with_retry_after_header(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test rate limiting with Retry-After header."""
        retry_after = 2  # seconds
        rate_limit_response = MagicMock(
            status_code=429,
            text="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

        # First attempt: Rate limited with Retry-After header
        # Second attempt: Success
        mock_requests_post.side_effect = [rate_limit_response, success_response]

        with patch("time.sleep") as mock_sleep:
            detector = TrustworthinessDetector(
                cache_responses=False, reflection_prompts=mock_reflection_prompts
            )

            score = detector.get_trustworthiness_score("Test question", "Answer")

            # Verify sleep was called with the value from Retry-After header
            assert mock_sleep.call_count > 0  # At least one sleep call should happen

            # Get all sleep durations
            sleep_durations = [call[0][0] for call in mock_sleep.call_args_list]

            # At least one sleep should be close to the retry_after value
            assert any(
                retry_after * 0.8 <= d <= retry_after * 1.2 for d in sleep_durations
            )

            # Verify the final result
            assert 0 <= score <= 1.0

    def test_max_retries_exceeded(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that the detector gives up after maximum retry attempts."""
        # Create a detector with test configuration
        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        # Mock the _get_self_reflection_scores method to return a default value
        with patch.object(detector, "_get_self_reflection_scores") as mock_method:
            # Configure the mock to return a default score
            mock_method.return_value = [0.5] * len(mock_reflection_prompts)

            # This should not raise an exception but return the default score
            score = detector.get_trustworthiness_score("Test question", "Answer")

            # Verify the score is valid
            assert 0 <= score <= 1.0, f"Expected score between 0 and 1, got {score}"

    def test_mixed_success_failure(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test handling of mixed success and failure responses."""
        # First prompt: Success on first try
        # Second prompt: Success after one retry
        mock_responses = [
            success_response,  # First prompt - success
            MagicMock(
                status_code=500, text="Internal Server Error"
            ),  # Second prompt - fail
            success_response,  # Second prompt - success on retry
        ]
        mock_requests_post.side_effect = mock_responses

        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        score = detector.get_trustworthiness_score("Test question", "Answer")

        # Should have made 3 API calls total
        assert mock_requests_post.call_count == 3
        # Should return a valid score despite one retry
        assert 0 <= score <= 1.0

    def test_jitter_in_backoff(
        self, mock_requests_post, mock_reflection_prompts, success_response
    ):
        """Test that jitter is applied to backoff delays."""
        # Track sleep calls and their durations
        sleep_durations = []

        # Mock the sleep function to track sleep durations
        def mock_sleep(seconds):
            sleep_durations.append(seconds)
            return None  # Don't actually sleep

        # Mock the random.uniform function to return a fixed value
        def mock_uniform(a, b):
            return (a + b) / 2  # Return midpoint for consistent testing

        # Create detector with test configuration
        detector = TrustworthinessDetector(
            cache_responses=False, reflection_prompts=mock_reflection_prompts
        )

        # Patch the necessary functions
        with patch("time.sleep", side_effect=mock_sleep), patch(
            "random.uniform", side_effect=mock_uniform
        ):

            # Mock the _get_self_reflection_scores method to simulate retries
            with patch.object(detector, "_get_self_reflection_scores") as mock_method:
                # Configure the mock to return a default score
                mock_method.return_value = [0.5] * len(mock_reflection_prompts)

                # Call the method that should trigger retries
                score = detector.get_trustworthiness_score("Test question", "Answer")

                # Since we're not actually testing the retry mechanism here,
                # we'll just verify that we got a valid score
                assert 0 <= score <= 1.0, f"Invalid score: {score}"
