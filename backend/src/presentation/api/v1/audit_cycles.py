from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.audits import AuditCycleCreate, AuditReportSubmit
from src.domain.entities.employee import Employee
from src.domain.entities.audit_cycle import AuditCycle, AuditReport
from src.domain.enums import AuditCycleStatus
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission, _get_resolved_permissions_for_role
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.audit_service import AuditService, get_audit_service
from src.shared.errors import NotFoundError, ForbiddenError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[AuditCycle],
    dependencies=[Depends(require_permission("perm_audits_view"))]
)
def list_audit_cycles(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted cycles"),
    status: AuditCycleStatus | None = Query(default=None, description="Filter by status"),
    service: AuditService = Depends(get_audit_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value

    items, next_cursor = service.list_cycles(
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
    response_model=SingleResponse[AuditCycle],
    dependencies=[Depends(require_permission("perm_audits_view"))]
)
def get_audit_cycle(
    cycle_id: str = Path(..., alias="id"),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.get_cycle_by_id(cycle_id)
    if not cycle or cycle.is_deleted:
        raise NotFoundError(f"Audit cycle {cycle_id} not found")
    return SingleResponse(data=cycle)

@router.get(
    "/{id}/reports",
    response_model=ListResponse[AuditReport],
    dependencies=[Depends(require_permission("perm_audits_view"))]
)
def list_audit_reports(
    cycle_id: str = Path(..., alias="id"),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.get_cycle_by_id(cycle_id)
    if not cycle or cycle.is_deleted:
        raise NotFoundError(f"Audit cycle {cycle_id} not found")
        
    reports = service.list_reports(cycle_id)
    return ListResponse(
        data=reports,
        meta=PaginatedMeta(nextCursor=None, hasMore=False)
    )

@router.post(
    "/",
    response_model=SingleResponse[AuditCycle],
    status_code=201
)
def create_audit_cycle(
    payload: AuditCycleCreate,
    current_user: Employee = Depends(require_permission("perm_audits_manage")),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.create_cycle(
        cycle_code=payload.cycle_code,
        name=payload.name,
        department_ids=payload.department_ids,
        category_ids=payload.category_ids,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        assigned_auditor_ids=payload.assigned_auditor_ids,
        actor_id=current_user.id
    )
    return SingleResponse(data=cycle)

@router.post(
    "/{id}/start",
    response_model=SingleResponse[AuditCycle]
)
def start_audit_cycle(
    cycle_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_audits_manage")),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.start_cycle(cycle_id, current_user.id)
    return SingleResponse(data=cycle)

@router.post(
    "/{id}/reports",
    response_model=SingleResponse[AuditReport]
)
def submit_audit_report(
    payload: AuditReportSubmit,
    cycle_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_audits_report_submit")),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.get_cycle_by_id(cycle_id)
    if not cycle or cycle.is_deleted:
        raise NotFoundError(f"Audit cycle {cycle_id} not found")
        
    # Verify the auditor is assigned to this cycle or has elevated manage permission
    is_assigned = current_user.id in cycle.assigned_auditor_ids
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_manage = "perm_audits_manage" in perms
    
    if not (is_assigned or has_manage):
        raise ForbiddenError("Insufficient permissions: you are not an assigned auditor for this cycle")

    report = service.submit_report(
        cycle_id=cycle_id,
        asset_id=payload.asset_id,
        audited_by=current_user.id,
        actual_location=payload.actual_location,
        actual_condition=payload.actual_condition,
        found=payload.found,
        discrepancy_notes=payload.discrepancy_notes,
        photo_urls=payload.photo_urls,
        actor_id=current_user.id
    )
    return SingleResponse(data=report)

@router.post(
    "/{id}/close",
    response_model=SingleResponse[AuditCycle]
)
def close_audit_cycle(
    cycle_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_audits_manage")),
    service: AuditService = Depends(get_audit_service)
):
    cycle = service.close_cycle(cycle_id, current_user.id)
    return SingleResponse(data=cycle)
