"""
Request/response logging middleware for observability.
Logs all API requests with timing, status codes, and errors.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("trading_bot.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for health check and static files
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info(
            f"→ {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            log_level = logging.INFO if response.status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"← {request.method} {request.url.path} "
                f"[{response.status_code}] {duration_ms:.2f}ms"
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"✗ {request.method} {request.url.path} "
                f"ERROR after {duration_ms:.2f}ms: {str(e)}"
            )
            raise
