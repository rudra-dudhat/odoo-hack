from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.domain.entities.audit_log_entry import AuditLogEntry
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[AuditLogEntry],
    dependencies=[Depends(require_permission("perm_audits_view"))]
)
def list_audit_logs(
    pagination: PaginationParams = Depends(get_pagination_params),
    entityType: str | None = Query(default=None, alias="entityType", description="Filter by entity type"),
    entityId: str | None = Query(default=None, alias="entityId", description="Filter by entity ID"),
    performedBy: str | None = Query(default=None, alias="performedBy", description="Filter by performer employee ID"),
    service: AuditLogService = Depends(get_audit_log_service)
):
    filters = {}
    if entityType is not None:
        filters["entityType"] = entityType
    if entityId is not None:
        filters["entityId"] = entityId
    if performedBy is not None:
        filters["performedBy"] = performedBy

    items, next_cursor = service.list_logs(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters=filters
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
    response_model=SingleResponse[AuditLogEntry],
    dependencies=[Depends(require_permission("perm_audits_view"))]
)
def get_audit_log(
    log_id: str = Path(..., alias="id"),
    service: AuditLogService = Depends(get_audit_log_service)
):
    log = service.get_by_id(log_id)
    if not log:
        raise NotFoundError(f"Audit log entry {log_id} not found")
    return SingleResponse(data=log)
