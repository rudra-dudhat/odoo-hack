from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.maintenance import (
    MaintenanceRequestCreate,
    MaintenanceApproveRequest,
    MaintenanceRejectRequest,
    MaintenanceAssignRequest,
    MaintenanceProgressRequest
)
from src.domain.entities.employee import Employee
from src.domain.entities.maintenance_request import MaintenanceRequest, MaintenanceApproval, MaintenanceLog
from src.domain.enums import MaintenanceStatus, MaintenancePriority
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission, _get_resolved_permissions_for_role
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.maintenance_service import MaintenanceService, get_maintenance_service
from src.shared.errors import NotFoundError, ForbiddenError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[MaintenanceRequest],
    dependencies=[Depends(require_permission("perm_maintenance_view"))]
)
def list_maintenance_requests(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted requests"),
    status: MaintenanceStatus | None = Query(default=None, description="Filter by status"),
    priority: MaintenancePriority | None = Query(default=None, description="Filter by priority"),
    assetId: str | None = Query(default=None, alias="assetId", description="Filter by asset"),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value
    if priority is not None:
        filters["priority"] = priority.value
    if assetId is not None:
        filters["assetId"] = assetId

    items, next_cursor = service.list_requests(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters=filters,
        include_deleted=includeDeleted
    )
    return ListResponse(
        data=items,
        meta=PaginatedMeta(
            nextCursor=next_cursor,
            hasMore=next_cursor is not None
        )
    )

@router.get(
    "/{id}",
    response_model=SingleResponse[MaintenanceRequest],
    dependencies=[Depends(require_permission("perm_maintenance_view"))]
)
def get_maintenance_request(
    request_id: str = Path(..., alias="id"),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.get_request_by_id(request_id)
    if not req or req.is_deleted:
        raise NotFoundError(f"Maintenance request {request_id} not found")
    return SingleResponse(data=req)

@router.get(
    "/{id}/approvals",
    response_model=ListResponse[MaintenanceApproval],
    dependencies=[Depends(require_permission("perm_maintenance_view"))]
)
def list_maintenance_approvals(
    request_id: str = Path(..., alias="id"),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    # Verify request exists first
    req = service.get_request_by_id(request_id)
    if not req or req.is_deleted:
        raise NotFoundError(f"Maintenance request {request_id} not found")
        
    approvals = service.list_approvals(request_id)
    return ListResponse(
        data=approvals,
        meta=PaginatedMeta(nextCursor=None, hasMore=False)
    )

@router.get(
    "/{id}/logs",
    response_model=ListResponse[MaintenanceLog],
    dependencies=[Depends(require_permission("perm_maintenance_view"))]
)
def list_maintenance_logs(
    request_id: str = Path(..., alias="id"),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    # Verify request exists
    req = service.get_request_by_id(request_id)
    if not req or req.is_deleted:
        raise NotFoundError(f"Maintenance request {request_id} not found")
        
    logs = service.list_logs(request_id)
    return ListResponse(
        data=logs,
        meta=PaginatedMeta(nextCursor=None, hasMore=False)
    )

@router.post(
    "/",
    response_model=SingleResponse[MaintenanceRequest],
    status_code=201
)
def create_maintenance_request(
    payload: MaintenanceRequestCreate,
    current_user: Employee = Depends(require_permission("perm_maintenance_request")),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.create_request(
        asset_id=payload.asset_id,
        requested_by=current_user.id,
        issue_description=payload.issue_description,
        priority=payload.priority,
        actor_id=current_user.id
    )
    return SingleResponse(data=req)

@router.post(
    "/{id}/approve",
    response_model=SingleResponse[MaintenanceRequest]
)
def approve_maintenance_request(
    payload: MaintenanceApproveRequest,
    request_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_maintenance_approve")),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.approve_request(
        request_id=request_id,
        comments=payload.comments,
        actor_id=current_user.id
    )
    return SingleResponse(data=req)

@router.post(
    "/{id}/reject",
    response_model=SingleResponse[MaintenanceRequest]
)
def reject_maintenance_request(
    payload: MaintenanceRejectRequest,
    request_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_maintenance_approve")),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.reject_request(
        request_id=request_id,
        comments=payload.comments,
        actor_id=current_user.id
    )
    return SingleResponse(data=req)

@router.post(
    "/{id}/assign",
    response_model=SingleResponse[MaintenanceRequest]
)
def assign_technician(
    payload: MaintenanceAssignRequest,
    request_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_maintenance_log_write")),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.assign_technician(
        request_id=request_id,
        technician_id=payload.technician_id,
        actor_id=current_user.id
    )
    return SingleResponse(data=req)

@router.post(
    "/{id}/progress",
    response_model=SingleResponse[MaintenanceRequest]
)
def progress_maintenance_status(
    payload: MaintenanceProgressRequest,
    request_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_maintenance_log_write")),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.progress_status(
        request_id=request_id,
        new_status=payload.status,
        actual_cost=payload.actual_cost,
        actor_id=current_user.id
    )
    return SingleResponse(data=req)

@router.post(
    "/{id}/cancel",
    response_model=SingleResponse[MaintenanceRequest]
)
def cancel_maintenance_request(
    request_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(get_current_employee),
    service: MaintenanceService = Depends(get_maintenance_service)
):
    req = service.get_request_by_id(request_id)
    if not req or req.is_deleted:
        raise NotFoundError(f"Maintenance request {request_id} not found")
        
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    is_requester = req.requested_by == current_user.id
    is_admin = "perm_maintenance_approve" in perms
    
    # Standard rule: requester or admin can cancel
    if not (is_requester or is_admin):
        raise ForbiddenError("Insufficient permissions: only the requester or an administrator can cancel this request")
        
    updated = service.cancel_request(request_id, current_user.id)
    return SingleResponse(data=updated)
