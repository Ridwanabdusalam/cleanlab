"""
Main Trustworthiness Detector implementation with support for streaming, confidence intervals,
model explainability, and custom scoring functions.
"""
from typing import Dict, List, Optional, AsyncGenerator, Union, Any, Deque, Tuple
import asyncio
import logging
import time
import psutil
from dataclasses import dataclass
from collections import OrderedDict, deque
from enum import Enum, auto
from datetime import datetime, timedelta

from .models import (
    EvaluationRequest,
    EvaluationResponse,
    TrustScore,
    ScoreExplanation,
    ScoringFunction
)
from .scoring import (
    default_scoring,
    get_scoring_function,
    register_scoring_function
)

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """Result of a trust evaluation."""
    request: EvaluationRequest
    response: Optional[EvaluationResponse] = None
    error: Optional[Exception] = None

class CircuitBreakerState(Enum):
    CLOSED = auto()
    HALF_OPEN = auto()
    OPEN = auto()

class TrustworthinessDetector:
    """
    Detects trustworthiness of answers with support for streaming, confidence intervals,
    model explainability, and custom scoring functions.
    
    Features:
    - Adaptive batching based on processing times
    - Response caching with TTL and LRU eviction
    - Circuit breaker for error handling
    - Concurrency control with semaphores
    - System load monitoring
    """
    
    def __init__(
        self, 
        default_scoring_fn: str = "default",
        max_concurrent: int = 100,
        max_cache_size: int = 1000,
        cache_ttl: int = 300,  # 5 minutes
        circuit_breaker_failures: int = 5,
        circuit_breaker_timeout: int = 30  # seconds
    ):
        """Initialize the detector.
        
        Args:
            default_scoring_fn: Name of the default scoring function to use
            max_concurrent: Maximum number of concurrent evaluations
            max_cache_size: Maximum number of items to keep in cache
            cache_ttl: Time-to-live for cache entries in seconds
            circuit_breaker_failures: Number of failures before opening the circuit
            circuit_breaker_timeout: Time in seconds before attempting to close the circuit
        """
        self.default_scoring_fn = default_scoring_fn
        self._batch_queue = asyncio.Queue()
        self._batch_event = asyncio.Event()
        self._batch_size = 10  # Initial batch size
        self._min_batch_size = 1
        self._max_batch_size = 100
        self._batch_timeout = 0.1  # seconds
        self._batch_processing_times = deque(maxlen=10)  # Track last 10 batch processing times
        
        # Caching
        self._cache = OrderedDict()
        self._max_cache_size = max_cache_size
        self._cache_ttl = cache_ttl
        
        # Circuit breaker
        self._circuit_state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._circuit_breaker_failures = circuit_breaker_failures
        self._circuit_breaker_timeout = circuit_breaker_timeout
        self._circuit_last_failure = None
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Start background tasks
        self._batch_processor_task = asyncio.create_task(self._process_batches())
        self._cache_cleanup_task = asyncio.create_task(self._cleanup_cache())
        self._monitor_task = asyncio.create_task(self._monitor_system_load())
        
        # Register built-in scoring functions
        self.register_default_scoring_functions()
    
    def register_default_scoring_functions(self) -> None:
        """Register built-in scoring functions."""
        # Already registered via decorators in scoring.py
        pass
    
    def register_scoring_function(
        self,
        name: str,
        scoring_fn: callable,
        description: str = ""
    ) -> None:
        """Register a custom scoring function.
        
        Args:
            name: Unique name for the scoring function
            scoring_fn: The scoring function to register
            description: Optional description of the function
        """
        register_scoring_function(name, description)(scoring_fn)
    
    def _get_cache_key(self, question: str, answer: str, scoring_fn: str, **kwargs) -> str:
        """Generate a cache key for the given inputs."""
        # Convert kwargs to a stable string representation
        params = ','.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{scoring_fn}:{question}:{answer}:{params}"
    
    async def _check_circuit_breaker(self) -> None:
        """Check if the circuit breaker should be opened or closed."""
        if self._circuit_state == CircuitBreakerState.OPEN:
            if (datetime.now() - self._circuit_last_failure).total_seconds() > self._circuit_breaker_timeout:
                self._circuit_state = CircuitBreakerState.HALF_OPEN
                logger.warning("Circuit breaker moved to HALF_OPEN state")
            else:
                raise RuntimeError("Service unavailable (circuit breaker open)")
    
    def _record_failure(self) -> None:
        """Record a failure and update circuit breaker state."""
        self._failure_count += 1
        self._circuit_last_failure = datetime.now()
        
        if self._circuit_state == CircuitBreakerState.HALF_OPEN or \
           (self._circuit_state == CircuitBreakerState.CLOSED and 
            self._failure_count >= self._circuit_breaker_failures):
            self._circuit_state = CircuitBreakerState.OPEN
            logger.error(f"Circuit breaker OPEN after {self._failure_count} failures")
    
    def _record_success(self) -> None:
        """Record a success and update circuit breaker state."""
        if self._circuit_state == CircuitBreakerState.HALF_OPEN:
            self._circuit_state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            logger.info("Circuit breaker CLOSED after successful operation")
    
    async def _check_system_load(self) -> bool:
        """Check if system load is acceptable for processing."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        
        if cpu_percent > 90 or mem.percent > 90:
            logger.warning(f"High system load - CPU: {cpu_percent}%, Memory: {mem.percent}%")
            return False
        return True
    
    async def get_trustworthiness_score(
        self,
        question: str,
        answer: str,
        context: Optional[str] = None,
        scoring_fn: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> TrustScore:
        """Get the trustworthiness score for a single question-answer pair.
        
        Args:
            question: The question being asked
            answer: The answer to evaluate
            context: Optional context for the question
            scoring_fn: Name of the scoring function to use
            use_cache: Whether to use cache for this request
            **kwargs: Additional arguments to pass to the scoring function
            
        Returns:
            TrustScore object with score, confidence interval, and explanation
            
        Raises:
            RuntimeError: If the circuit breaker is open or system load is too high
        """
        # Check circuit breaker first
        await self._check_circuit_breaker()
        
        # Check system load
        if not await self._check_system_load():
            raise RuntimeError("System load too high, please try again later")
        
        scoring_fn_name = scoring_fn or self.default_scoring_fn
        cache_key = self._get_cache_key(question, answer, scoring_fn_name, **kwargs)
        
        # Try cache first
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if (datetime.now() - cached['timestamp']).total_seconds() < self._cache_ttl:
                # Move to end to mark as recently used
                self._cache.move_to_end(cache_key)
                return cached['result']
            # Remove expired cache entry
            del self._cache[cache_key]
        
        # Get scoring function
        score_func = get_scoring_function(scoring_fn_name)
        if not score_func:
            raise ValueError(f"Scoring function '{scoring_fn_name}' not found")
        
        # Process with concurrency control
        async with self._semaphore:
            try:
                start_time = time.monotonic()
                result = await score_func(
                    question=question,
                    answer=answer,
                    context=context,
                    **kwargs
                )
                processing_time = time.monotonic() - start_time
                
                # Update adaptive batching
                self._batch_processing_times.append(processing_time)
                self._adjust_batch_size(processing_time)
                
                # Update cache
                if use_cache:
                    self._cache[cache_key] = {
                        'result': result,
                        'timestamp': datetime.now(),
                        'size': len(question) + len(answer) + (len(context) if context else 0)
                    }
                    # Evict if cache is full (LRU)
                    while len(self._cache) > self._max_cache_size:
                        self._cache.popitem(last=False)
                
                # Update circuit breaker on success
                self._record_success()
                return result
                
            except Exception as e:
                logger.error(f"Error in scoring function '{scoring_fn_name}': {str(e)}")
                self._record_failure()
                raise
    
    async def evaluate(
        self,
        request: Union[EvaluationRequest, List[EvaluationRequest]],
        scoring_fn: Optional[str] = None,
        **kwargs
    ) -> Union[EvaluationResponse, List[EvaluationResponse]]:
        """Evaluate one or more question-answer pairs.
        
        Args:
            request: Single evaluation request or list of requests
            scoring_fn: Name of the scoring function to use
            **kwargs: Additional arguments to pass to the scoring function
            
        Returns:
            Single EvaluationResponse or list of EvaluationResponse objects
        """
        if isinstance(request, list):
            return await self.batch_evaluate(request, scoring_fn, **kwargs)
        
        try:
            trust_score = await self.get_trustworthiness_score(
                question=request.question,
                answer=request.answer,
                context=request.context,
                scoring_fn=scoring_fn or request.custom_scoring_fn,
                **kwargs
            )
            
            return EvaluationResponse(
                question=request.question,
                answer=request.answer,
                trust_score=trust_score,
                context=request.context
            )
            
        except Exception as e:
            logger.error(f"Error evaluating request: {str(e)}")
            raise
    
    async def batch_evaluate(
        self,
        requests: List[EvaluationRequest],
        scoring_fn: Optional[str] = None,
        **kwargs
    ) -> List[EvaluationResponse]:
        """Evaluate multiple question-answer pairs in batch.
        
        Args:
            requests: List of evaluation requests
            scoring_fn: Name of the scoring function to use
            **kwargs: Additional arguments to pass to the scoring function
            
        Returns:
            List of EvaluationResponse objects
        """
        if not requests:
            return []
        
        # Process requests in parallel
        tasks = []
        for req in requests:
            task = asyncio.create_task(
                self.evaluate(req, scoring_fn=scoring_fn, **kwargs)
            )
            tasks.append(task)
        
        # Gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        responses = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in batch evaluation: {str(result)}")
                continue
            responses.append(result)
        
        return responses
    
    async def stream_evaluate(
        self,
        request: EvaluationRequest,
        scoring_fn: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream evaluation results as they become available.
        
        Args:
            request: Evaluation request
            scoring_fn: Name of the scoring function to use
            **kwargs: Additional arguments to pass to the scoring function
            
        Yields:
            Partial results as they become available
        """
        # For streaming, we'll simulate partial results
        # In a real implementation, this would stream from an LLM API
        
        # Yield initial status
        yield {
            "status": "processing",
            "progress": 0.1,
            "message": "Starting evaluation..."
        }
        
        # Process the request
        try:
            # Simulate processing steps
            for step in range(1, 6):
                await asyncio.sleep(0.1)  # Simulate work
                progress = step / 5
                yield {
                    "status": "processing",
                    "progress": progress,
                    "message": f"Processing step {step}/5..."
                }
            
            # Get the final result
            response = await self.evaluate(request, scoring_fn=scoring_fn, **kwargs)
            
            # Yield final result
            yield {
                "status": "completed",
                "progress": 1.0,
                "result": response.model_dump()
            }
            
        except Exception as e:
            logger.error(f"Error in streaming evaluation: {str(e)}")
            yield {
                "status": "error",
                "progress": 1.0,
                "error": str(e)
            }
    
    def _adjust_batch_size(self, processing_time: float) -> None:
        """Adjust batch size based on recent processing times."""
        if not self._batch_processing_times:
            return
            
        avg_time = sum(self._batch_processing_times) / len(self._batch_processing_times)
        
        # If processing is fast, try increasing batch size
        if avg_time < 0.5 and len(self._batch_processing_times) == self._batch_processing_times.maxlen:
            new_size = min(self._batch_size * 2, self._max_batch_size)
            if new_size != self._batch_size:
                logger.info(f"Increasing batch size from {self._batch_size} to {new_size}")
                self._batch_size = new_size
        # If processing is slow, decrease batch size
        elif avg_time > 1.0:
            new_size = max(self._batch_size // 2, self._min_batch_size)
            if new_size != self._batch_size:
                logger.info(f"Decreasing batch size from {self._batch_size} to {new_size}")
                self._batch_size = new_size
    
    async def _cleanup_cache(self) -> None:
        """Background task to clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                now = datetime.now()
                expired = [
                    k for k, v in self._cache.items()
                    if (now - v['timestamp']).total_seconds() > self._cache_ttl
                ]
                for k in expired:
                    del self._cache[k]
                if expired:
                    logger.debug(f"Cleaned up {len(expired)} expired cache entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {str(e)}")
    
    async def _monitor_system_load(self) -> None:
        """Background task to monitor system load and adjust processing accordingly."""
        while True:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                
                # Log high load
                if cpu_percent > 80 or mem.percent > 80:
                    logger.warning(f"High system load - CPU: {cpu_percent}%, Memory: {mem.percent}%")
                
                # Adjust concurrency based on load
                if cpu_percent > 90 or mem.percent > 90:
                    # Reduce concurrency under high load
                    current_limit = self._semaphore._value
                    if current_limit > 10:
                        new_limit = max(10, int(current_limit * 0.8))
                        self._semaphore = asyncio.Semaphore(new_limit)
                        logger.warning(f"Reduced concurrency to {new_limit} due to high load")
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system monitor: {str(e)}")
                await asyncio.sleep(5)  # Prevent tight loop on errors
    
    async def _process_batches(self) -> None:
        """Background task to process batches of evaluation requests."""
        while True:
            try:
                # Wait for batch event or timeout
                try:
                    await asyncio.wait_for(self._batch_event.wait(), timeout=1.0)
                    self._batch_event.clear()
                except asyncio.TimeoutError:
                    # No batches recently, check for stragglers
                    if not self._batch_queue.empty():
                        self._batch_event.set()
                    continue
                
                # Check system load before processing
                if not await self._check_system_load():
                    await asyncio.sleep(1)
                    continue
                
                # Collect a batch of requests
                batch = []
                batch_start = time.monotonic()
                
                try:
                    # Get at least one request with a small timeout
                    try:
                        item = await asyncio.wait_for(
                            self._batch_queue.get(),
                            timeout=0.1
                        )
                        batch.append(item)
                        
                        # Get more requests if available, up to batch size
                        while len(batch) < self._batch_size and not self._batch_queue.empty():
                            # Don't spend too much time collecting a batch
                            if time.monotonic() - batch_start > self._batch_timeout:
                                break
                                
                            try:
                                item = await asyncio.wait_for(
                                    self._batch_queue.get_nowait(),
                                    timeout=0.01
                                )
                                batch.append(item)
                            except (asyncio.QueueEmpty, asyncio.TimeoutError):
                                break
                        
                        # Process the batch
                        if batch:
                            await self._process_batch(batch)
                            
                    except asyncio.TimeoutError:
                        continue
                        
                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    # Re-queue failed items
                    for item in batch:
                        await self._batch_queue.put(item)
                    await asyncio.sleep(1)  # Back off on error
                
            except asyncio.CancelledError:
                # Handle cancellation
                break
            except Exception as e:
                logger.error(f"Unexpected error in batch processor: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on errors
    
    async def _process_batch(self, batch: List[EvaluationResult]) -> None:
        """Process a batch of evaluation requests."""
        try:
            # Group requests by scoring function
            requests_by_fn: Dict[str, List[EvaluationRequest]] = {}
            for result in batch:
                fn_name = result.request.custom_scoring_fn or self.default_scoring_fn
                if fn_name not in requests_by_fn:
                    requests_by_fn[fn_name] = []
                requests_by_fn[fn_name].append(result.request)
            
            # Process each group
            for fn_name, requests in requests_by_fn.items():
                scoring_fn = get_scoring_function(fn_name)
                if not scoring_fn:
                    logger.error(f"Scoring function '{fn_name}' not found")
                    continue
                
                # Process the batch with the appropriate scoring function
                responses = await self.batch_evaluate(requests, scoring_fn=fn_name)
                
                # Update results
                for result, response in zip(batch, responses):
                    result.response = response
                    if hasattr(result, 'future') and result.future and not result.future.done():
                        result.future.set_result(response)
        
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            # Set exception on all futures
            for result in batch:
                if hasattr(result, 'future') and result.future and not result.future.done():
                    result.future.set_exception(e)
    
    async def close(self) -> None:
        """Clean up resources."""
        # Cancel all background tasks
        tasks = [
            self._batch_processor_task,
            self._cache_cleanup_task,
            self._monitor_task
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error during cleanup: {str(e)}")
        
        # Clear cache
        self._cache.clear()
        logger.info("TrustworthinessDetector resources cleaned up")
    
    async def __aenter__(self) -> 'TrustworthinessDetector':
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
        await self.close()
