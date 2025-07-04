"""
FastAPI application setup for the Trustworthiness Detector API.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

from fastapi import (
    FastAPI, 
    Request, 
    status, 
    Depends, 
    HTTPException,
    BackgroundTasks,
    Query,
    Path
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    JSONResponse, 
    Response, 
    StreamingResponse,
    HTMLResponse
)
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field, HttpUrl, validator
from starlette.background import BackgroundTask

from .config import settings
from .security import setup_security
from .detector import TrustworthinessDetector, EvaluationResult
from .models import (
    EvaluationRequest,
    EvaluationResponse,
    BatchEvaluationRequest,
    TrustScore,
    ScoreExplanation,
    ScoringFunction
)
from .scoring import get_scoring_function, list_scoring_functions, register_scoring_function as register_scoring_fn
from .metrics import setup_metrics, record_trust_score, REQUEST_COUNT, REQUEST_LATENCY

# Initialize the detector
detector = TrustworthinessDetector()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
def get_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Trustworthiness Detector API",
        description="API for detecting the trustworthiness of LLM-generated answers",
        version="1.0.0",
        docs_url="/docs" if settings.ENV != "production" else None,
        redoc_url="/redoc" if settings.ENV != "production" else None,
        openapi_url="/openapi.json" if settings.ENV != "production" else None,
    )
    
    # Store settings in app state
    app.state.settings = settings
    
    # Set up middleware and routes
    setup_security(app)
    setup_metrics(app)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

# Create the FastAPI application
app = get_application()

# These are now set up in the get_application() function

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Trustworthiness Detector API",
        version="1.0.0",
        description="API for detecting the trustworthiness of LLM-generated answers with confidence intervals and explanations",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication"
        }
    }
    
    # Add security to all endpoints
    for path in openapi_schema.get("paths", {}).values():
        for method in path.values():
            if method.get("operationId") not in ["health_check", "metrics"]:
                method["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "body": exc.body,
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail.get("error", "http_error") if isinstance(exc.detail, dict) else str(exc.detail),
            "detail": exc.detail if isinstance(exc.detail, dict) else str(exc.detail)
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred"
        },
    )

# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    response_model=Dict[str, str],
    responses={
        200: {"description": "Service is healthy"},
        500: {"description": "Service is unhealthy"}
    }
)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dict with status and timestamp
    """
    try:
        # Add any additional health checks here
        return {
            "status": "ok",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "service_unavailable", "message": str(e)}
        )

# API endpoints
@app.post(
    "/api/v1/evaluate",
    response_model=EvaluationResponse,
    tags=["evaluation"],
    summary="Evaluate trustworthiness of a single answer",
    responses={
        200: {"description": "Evaluation successful"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def evaluate_trustworthiness(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    scoring_fn: Optional[str] = None,
) -> EvaluationResponse:
    """
    Evaluate the trustworthiness of an answer to a question.
    
    Args:
        request: Evaluation request containing question, answer, and optional context
        background_tasks: FastAPI background tasks
        scoring_fn: Optional name of a custom scoring function to use
        
    Returns:
        EvaluationResponse with trust score and explanation
    """
    try:
        # Record metrics
        REQUEST_COUNT.labels(
            method="POST",
            endpoint="/api/v1/evaluate",
            http_status=200
        ).inc()
        
        # Process the evaluation
        result = await detector.evaluate(
            request=request,
            scoring_fn=scoring_fn
        )
        
        # Record the score in the background
        if result and result.trust_score:
            background_tasks.add_task(
                record_trust_score,
                result.trust_score.score
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_trustworthiness: {str(e)}")
        raise

@app.post(
    "/api/v1/evaluate/stream",
    response_class=StreamingResponse,
    tags=["evaluation"],
    summary="Streaming evaluation of answer trustworthiness",
    responses={
        200: {"description": "Evaluation stream started"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def stream_evaluate_trustworthiness(
    request: EvaluationRequest,
    scoring_fn: Optional[str] = None,
) -> StreamingResponse:
    """
    Stream the evaluation of answer trustworthiness.
    
    This endpoint provides real-time updates as the evaluation progresses.
    
    Args:
        request: Evaluation request containing question, answer, and optional context
        scoring_fn: Optional name of a custom scoring function to use
        
    Returns:
        StreamingResponse with evaluation progress and final result
    """
    try:
        # Record metrics
        REQUEST_COUNT.labels(
            method="POST",
            endpoint="/api/v1/evaluate/stream",
            http_status=200
        ).inc()
        
        # Create a streaming response
        async def generate():
            try:
                # Stream the evaluation
                async for chunk in detector.stream_evaluate(request, scoring_fn=scoring_fn):
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay to prevent overwhelming the client
                
                # Signal the end of the stream
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in stream: {str(e)}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable buffering for nginx
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream_evaluate_trustworthiness: {str(e)}")
        raise

@app.post(
    "/api/v1/evaluate/batch",
    response_model=List[EvaluationResponse],
    tags=["evaluation"],
    summary="Batch evaluate multiple question-answer pairs",
    responses={
        200: {"description": "Batch evaluation successful"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def batch_evaluate_trustworthiness(
    request: BatchEvaluationRequest,
    background_tasks: BackgroundTasks,
    scoring_fn: Optional[str] = None,
) -> List[EvaluationResponse]:
    """
    Evaluate multiple question-answer pairs in a single request.
    
    Args:
        request: Batch evaluation request containing multiple question-answer pairs
        background_tasks: FastAPI background tasks
        scoring_fn: Optional name of a custom scoring function to use for all evaluations
        
    Returns:
        List of evaluation responses
    """
    try:
        # Record metrics
        REQUEST_COUNT.labels(
            method="POST",
            endpoint="/api/v1/evaluate/batch",
            http_status=200
        ).inc()
        
        # Process the batch evaluation
        results = await detector.batch_evaluate(
            requests=request.items,
            scoring_fn=scoring_fn
        )
        
        # Record metrics in the background
        background_tasks.add_task(
            lambda: [
                record_trust_score(result.trust_score.score) 
                for result in results 
                if result and result.trust_score
            ]
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch_evaluate_trustworthiness: {str(e)}")
        raise

@app.post("/api/v1/batch-evaluate", tags=["evaluation"])
async def legacy_batch_evaluate_trustworthiness(request: Request) -> dict:
    """
    Legacy endpoint for batch evaluation.
    
    This is maintained for backward compatibility. New clients should use /api/v1/evaluate/batch.
    
    Request body should be a JSON array of objects with:
    - question: The question being asked
    - answer: The answer to evaluate
    - context: Optional context for the question
    """
    try:
        data = await request.json()
        
        if not isinstance(data, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a JSON array of question-answer objects",
            )
        
        # Convert to new request format
        requests = []
        for item in data:
            requests.append(EvaluationRequest(
                question=item.get("question"),
                answer=item.get("answer"),
                context=item.get("context"),
                metadata={"source": "legacy_batch_endpoint"}
            ))
        
        # Process the batch
        results = []
        batch_request = BatchEvaluationRequest(items=requests)
        responses = await batch_evaluate_trustworthiness(
            request=batch_request,
            background_tasks=BackgroundTasks(),
            scoring_fn=None
        )
        
        # Convert to legacy format
        for response in responses:
            if response.trust_score:
                results.append({
                    "question": response.question,
                    "answer": response.answer,
                    "trustworthiness_score": response.trust_score.score,
                    "explanation": response.trust_score.explanation.dict() if response.trust_score.explanation else None
                })
            else:
                results.append({
                    "question": response.question,
                    "answer": response.answer,
                    "error": "Failed to evaluate trust score"
                })
        
        return {"results": results}
        
    except Exception as e:
        logger.error(f"Error in legacy batch evaluation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": str(e)}
        )

# Scoring function management endpoints
@app.get(
    "/api/v1/scoring-functions",
    response_model=Dict[str, Dict[str, str]],
    tags=["scoring"],
    summary="List available scoring functions",
    responses={
        200: {"description": "List of available scoring functions"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)
async def list_scoring_functions() -> Dict[str, Dict[str, str]]:
    """
    List all available scoring functions.
    
    Returns:
        Dictionary of scoring function names to their descriptions
    """
    try:
        return list_scoring_functions()
    except Exception as e:
        logger.error(f"Error listing scoring functions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Failed to list scoring functions"}
        )

@app.post(
    "/api/v1/scoring-functions/{function_name}",
    status_code=status.HTTP_201_CREATED,
    tags=["scoring"],
    summary="Register a custom scoring function",
    responses={
        201: {"description": "Scoring function registered successfully"},
        400: {"description": "Invalid function definition"},
        401: {"description": "Unauthorized"},
        409: {"description": "Function with this name already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def register_scoring_function(
    function_name: str,
    function_def: Dict[str, Any],
    overwrite: bool = False,
) -> Dict[str, str]:
    """
    Register a custom scoring function.
    
    Args:
        function_name: Unique name for the scoring function
        function_def: Dictionary containing the function definition
        overwrite: Whether to overwrite an existing function with the same name
        
    Returns:
        Confirmation message
    """
    try:
        # Check if function already exists
        existing_fn = get_scoring_function(function_name)
        if existing_fn and not overwrite:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "function_exists", "message": f"Scoring function '{function_name}' already exists"}
            )
        
        # TODO: Add function validation and registration logic
        # This is a placeholder - in a real implementation, you would:
        # 1. Validate the function definition
        # 2. Compile/register the function
        # 3. Add it to the registry
        
        return {"status": "success", "message": f"Scoring function '{function_name}' registered"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering scoring function: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "registration_failed", "message": str(e)}
        )

# Metrics and monitoring endpoints
@app.get(
    "/api/v1/metrics",
    tags=["metrics"],
    summary="Get application metrics in Prometheus format",
    response_class=Response,
    responses={
        200: {"description": "Prometheus metrics"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
    try:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "metrics_error", "message": "Failed to generate metrics"}
        )

@app.get(
    "/api/v1/stats",
    tags=["metrics"],
    summary="Get application statistics",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "Application statistics"},
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"}
    }
)
async def get_stats() -> Dict[str, Any]:
    """
    Get application statistics and health metrics.
    
    Returns:
        Dictionary containing various application metrics
    """
    try:
        # Collect basic metrics
        stats = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "requests_total": REQUEST_COUNT.labels()._value.get() if hasattr(REQUEST_COUNT, '_value') else 0,
                "active_requests": 0,  # This would track currently active requests
                "avg_processing_time": 0,  # This would track average processing time
            },
            "system": {
                "python_version": ".".join(map(str, sys.version_info[:3])),
                "platform": sys.platform,
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "stats_error", "message": "Failed to get statistics"}
        )

# Add startup event to log configuration
@app.on_event("startup")
async def startup_event():
    """Log application startup with configuration."""
    import logging
    
    logger = logging.getLogger("trustworthiness")
    logger.info("Starting Trustworthiness Detector API")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Allowed origins: {settings.ALLOWED_ORIGINS}")
    logger.info(f"Request signing: {getattr(settings, 'ENABLE_REQUEST_SIGNING', False)}")
    logger.info(f"Rate limiting: {getattr(settings, 'ENABLE_RATE_LIMITING', False)}")
    logger.info(f"Metrics enabled: True")
    logger.info(f"API Documentation: {'/docs' if settings.ENV != 'production' else 'Disabled in production'}")
