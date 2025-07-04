"""Unit tests for circuit breaker functionality."""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock, PropertyMock
from datetime import datetime, timedelta

# Import the modules to test
try:
    from src.trustworthiness.detector import TrustworthinessDetector, CircuitBreakerState
    from src.trustworthiness.models import TrustScore, ScoreExplanation
    from src.trustworthiness.scoring import get_scoring_function, register_scoring_function
except ImportError as e:
    pytest.skip(f"Could not import required modules: {e}", allow_module_level=True)

# Create a test trust score object for testing
TEST_TRUST_SCORE = TrustScore(
    score=0.8,
    confidence_interval=(0.7, 0.9),
    explanation=ScoreExplanation(
        score=0.8,
        confidence=0.9,
        reasoning="Test explanation",
        factors={"test_factor": 0.8}
    )
)

# Register a test scoring function
@register_scoring_function("test_score", "Test scoring function")
async def mock_scoring_fn(question: str, answer: str, **kwargs) -> TrustScore:
    """Test scoring function that returns a fixed score for testing."""
    return TEST_TRUST_SCORE

@pytest.fixture
def mock_trust_score():
    """Return a mock trust score for testing."""
    return TEST_TRUST_SCORE

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up
    pending = asyncio.all_tasks(loop=loop)
    for task in pending:
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
    loop.close()

@pytest.fixture
def detector(mock_trust_score, event_loop):
    """Create a test detector with mocks."""
    # Create a detector with a low failure threshold for testing
    with patch('asyncio.create_task') as mock_create_task, \
         patch('asyncio.ensure_future') as mock_ensure_future:
        
        # Mock the task objects to avoid actual async operations
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_create_task.return_value = mock_task
        mock_ensure_future.return_value = mock_task
        
        detector = TrustworthinessDetector(
            default_scoring_fn="test_score",
            max_concurrent=10,
            max_cache_size=1000,
            cache_ttl=60,
            circuit_breaker_failures=2,  # Trip after 2 failures
            circuit_breaker_timeout=1,   # 1 second timeout
        )
        
        # Mock the scoring function
        async def mock_scoring(question, answer, **kwargs):
            return mock_trust_score
        
        # Mock the get_scoring_function to return our mock
        detector._get_scoring_function = lambda name: mock_scoring
        
        # Mock the _check_system_load method to always return True
        detector._check_system_load = AsyncMock(return_value=True)
        
        # Mock the background tasks
        detector._batch_processor_task = mock_task
        detector._cache_cleanup_task = mock_task
        detector._monitor_task = mock_task
        
        return detector

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(detector, mock_trust_score, event_loop, caplog):
    """Test that circuit breaker opens after specified number of failures."""
    # Initial state should be closed
    assert detector._circuit_state == CircuitBreakerState.CLOSED
    
    # Create a new detector with a low failure threshold for testing
    test_detector = TrustworthinessDetector(
        default_scoring_fn="test_score",
        circuit_breaker_failures=2,  # Trip after 2 failures
        circuit_breaker_timeout=1,   # 1 second timeout
        max_concurrent=10,
        max_cache_size=1000,
        cache_ttl=60
    )
    
    # Set up the mock scoring function to raise an exception
    async def mock_score_failing(*args, **kwargs):
        raise Exception("Test error")
    
    # First failure
    with patch('src.trustworthiness.scoring.get_scoring_function') as mock_get_scoring, \
         patch('src.trustworthiness.scoring.SCORING_FUNCTIONS', new={}), \
         patch.object(test_detector, '_check_system_load', new_callable=AsyncMock, return_value=True) as mock_check_load:
        
        # Register our mock scoring function directly in the SCORING_FUNCTIONS dict
        from src.trustworthiness.scoring import ScoringFunction
        from src.trustworthiness.scoring import SCORING_FUNCTIONS as scoring_funcs
        
        # Create a mock scoring function that will raise an exception
        async def mock_score_failing_impl(*args, **kwargs):
            raise Exception("Test error")
            
        # Register it directly in the SCORING_FUNCTIONS dict
        scoring_funcs["test_score"] = ScoringFunction(
            name="test_score",
            description="Test scoring function that fails",
            function=mock_score_failing_impl
        )
        
        # This should raise the exception from our mock
        with patch.object(test_detector, '_cache', new=dict()):  # Ensure no caching

            with pytest.raises(Exception, match="Test error"):
                await test_detector.get_trustworthiness_score("Q", "A", use_cache=False)
            
            # Verify failure was recorded
            assert test_detector._failure_count == 1, "Failure count should be incremented"
    
    # Still closed after first failure
    assert test_detector._circuit_state == CircuitBreakerState.CLOSED
    assert test_detector._failure_count == 1
    
    # Second failure - should trigger circuit breaker
    # First, manually update the failure count to just below the threshold
    test_detector._failure_count = test_detector._circuit_breaker_failures - 1
    
    with patch('src.trustworthiness.scoring.get_scoring_function') as mock_get_scoring, \
         patch('src.trustworthiness.scoring.SCORING_FUNCTIONS', new={}), \
         patch.object(test_detector, '_check_system_load', new_callable=AsyncMock, return_value=True):
        
        # Register our mock scoring function again
        from src.trustworthiness.scoring import ScoringFunction
        from src.trustworthiness.scoring import SCORING_FUNCTIONS as scoring_funcs
        
        # Create a mock scoring function that will raise an exception
        async def mock_score_failing_impl(*args, **kwargs):
            raise Exception("Test error")
            
        # Register it directly in the SCORING_FUNCTIONS dict
        scoring_funcs["test_score"] = ScoringFunction(
            name="test_score",
            description="Test scoring function that fails",
            function=mock_score_failing_impl
        )
        
        # This should trigger the circuit breaker
        with patch.object(test_detector, '_cache', new=dict()):  # Ensure no caching
            # This should raise the scoring function exception, not the circuit breaker yet
            with pytest.raises(Exception, match="Test error"):
                await test_detector.get_trustworthiness_score("Q", "A", use_cache=False)
            
            # Now the circuit breaker should be open
            assert test_detector._circuit_state == CircuitBreakerState.OPEN
            
            # Next call should hit the circuit breaker
            with pytest.raises(RuntimeError, match="Service unavailable \(circuit breaker open"):
                await test_detector.get_trustworthiness_score("Q", "A", use_cache=False)
    
    # Verify circuit is open after second failure
    assert test_detector._circuit_state == CircuitBreakerState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_reset_after_timeout(detector, mock_trust_score, event_loop):
    """Test that circuit breaker resets after timeout."""
    # Create a new detector with a shorter timeout for testing
    with patch('asyncio.create_task') as mock_create_task, \
         patch('asyncio.ensure_future') as mock_ensure_future, \
         patch('src.trustworthiness.scoring.get_scoring_function') as mock_get_scoring:
        
        # Mock the task objects to avoid actual async operations
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_create_task.return_value = mock_task
        mock_ensure_future.return_value = mock_task
        
        test_detector = TrustworthinessDetector(
            default_scoring_fn="test_score",
            circuit_breaker_timeout=1,  # 1 second timeout for testing
            circuit_breaker_failures=1,  # Fail after 1 failure for testing
            max_concurrent=10,
            max_cache_size=1000,
            cache_ttl=60
        )
        
        # Mock the background tasks
        test_detector._batch_processor_task = mock_task
        test_detector._cache_cleanup_task = mock_task
        test_detector._monitor_task = mock_task
        
        # Mock the scoring function to return our test score
        async def mock_score(question, answer, **kwargs):
            return mock_trust_score
        
        # Set up the mock to return our scoring function
        mock_get_scoring.return_value = mock_score
        
        # Mock the _check_system_load method
        test_detector._check_system_load = AsyncMock(return_value=True)
        
        # Manually open the circuit for testing
        test_detector._circuit_state = CircuitBreakerState.OPEN
        test_detector._circuit_last_failure = datetime.now() - timedelta(seconds=2)  # 2 seconds ago
        
        # This should now work and reset the circuit
        result = await test_detector.get_trustworthiness_score("Q", "A")
        
        # Verify the result is as expected
        assert result == mock_trust_score, f"Expected {mock_trust_score}, got {result}"
        
        # Verify circuit is closed and result is correct
        assert test_detector._circuit_state == CircuitBreakerState.CLOSED
        assert test_detector._failure_count == 0  # Should reset failure count
