import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.shared.logging import correlation_id_ctx, logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Resolve or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_token = correlation_id_ctx.set(correlation_id)
        
        start_time = time.time()
        
        # Log request initiation
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"operation": "http_request"}
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log successful completion
            logger.info(
                f"Request finished: {request.method} {request.url.path} - Status {response.status_code} - Duration {duration:.3f}s",
                extra={"operation": "http_response"}
            )
            
            response.headers["X-Correlation-ID"] = correlation_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - Error {e} - Duration {duration:.3f}s",
                extra={"operation": "http_error"}
            )
            raise e
        finally:
            # Reset context variables to avoid cross-request contamination
            correlation_id_ctx.reset(correlation_id_token)
