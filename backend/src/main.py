from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.presentation.middleware.logging_middleware import LoggingMiddleware
from src.presentation.middleware.error_handler import setup_exception_handlers
from src.shared.logging import logger

# Import API Routers
from src.presentation.api.v1.departments import router as departments_router
from src.presentation.api.v1.employees import router as employees_router
from src.presentation.api.v1.roles import router as roles_router
from src.presentation.api.v1.permissions import router as permissions_router
from src.presentation.api.v1.asset_categories import router as asset_categories_router
from src.presentation.api.v1.assets import router as assets_router
from src.presentation.api.v1.asset_allocations import router as asset_allocations_router
from src.presentation.api.v1.shared_resources import router as shared_resources_router
from src.presentation.api.v1.resource_bookings import router as resource_bookings_router
from src.presentation.api.v1.maintenance_requests import router as maintenance_requests_router
from src.presentation.api.v1.audit_cycles import router as audit_cycles_router
from src.presentation.api.v1.notifications import router as notifications_router
from src.presentation.api.v1.dashboard import router as dashboard_router
from src.presentation.api.v1.audit_logs import router as audit_logs_router

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    logger.info("Starting FastAPI application bootstrap")
    
    app = FastAPI(
        title="Enterprise Asset & Resource Management ERP API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 1. Register Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    
    # 2. Register Custom Exception Handlers
    setup_exception_handlers(app)
    
    # 3. Health check route
    @app.get("/health", tags=["System"])
    async def health_check():
        return {"status": "healthy", "service": "erp-backend"}
        
    # 4. Include Versioned API Routers
    api_prefix = "/api/v1"
    app.include_router(departments_router, prefix=f"{api_prefix}/departments", tags=["Departments"])
    app.include_router(employees_router, prefix=f"{api_prefix}/employees", tags=["Employees"])
    app.include_router(roles_router, prefix=f"{api_prefix}/roles", tags=["Roles"])
    app.include_router(permissions_router, prefix=f"{api_prefix}/permissions", tags=["Permissions"])
    app.include_router(asset_categories_router, prefix=f"{api_prefix}/asset-categories", tags=["Asset Categories"])
    app.include_router(assets_router, prefix=f"{api_prefix}/assets", tags=["Assets"])
    app.include_router(asset_allocations_router, prefix=f"{api_prefix}/asset-allocations", tags=["Asset Allocations"])
    app.include_router(shared_resources_router, prefix=f"{api_prefix}/shared-resources", tags=["Shared Resources"])
    app.include_router(resource_bookings_router, prefix=f"{api_prefix}/resource-bookings", tags=["Resource Bookings"])
    app.include_router(maintenance_requests_router, prefix=f"{api_prefix}/maintenance-requests", tags=["Maintenance Requests"])
    app.include_router(audit_cycles_router, prefix=f"{api_prefix}/audit-cycles", tags=["Audit Cycles"])
    app.include_router(notifications_router, prefix=f"{api_prefix}/notifications", tags=["Notifications"])
    app.include_router(dashboard_router, prefix=f"{api_prefix}/dashboard", tags=["Dashboard"])
    app.include_router(audit_logs_router, prefix=f"{api_prefix}/audit-logs", tags=["Audit Logs"])
    
    logger.info("FastAPI application bootstrap complete")
    return app

app = create_app()
