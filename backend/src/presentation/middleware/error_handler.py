from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from src.shared.errors import (
    BusinessRuleError, NotFoundError, ConflictError, 
    ValidationError as DomainValidationError, ForbiddenError, 
    UnauthenticatedError
)
from src.shared.logging import logger

def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthenticatedError)
    async def unauthenticated_handler(request: Request, exc: UnauthenticatedError):
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": []
                }
            }
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": []
                }
            }
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": []
                }
            }
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": []
                }
            }
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": exc.field_errors
                }
            }
        )

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(request: Request, exc: BusinessRuleError):
        # Maps to 422 Unprocessable Entity for general semantic errors
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "fieldErrors": []
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def fastapi_validation_handler(request: Request, exc: RequestValidationError):
        field_errors = []
        for error in exc.errors():
            # Exclude the "body" segment from field location path if present
            loc = error.get("loc", [])
            field_name = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else ".".join(str(x) for x in loc)
            field_errors.append({
                "field": field_name,
                "message": error.get("msg", "Validation failed")
            })
            
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "fieldErrors": field_errors
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "fieldErrors": []
                }
            }
        )
