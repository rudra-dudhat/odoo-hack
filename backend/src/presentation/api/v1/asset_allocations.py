from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.allocations import AllocationCreate, AllocationReturnRequest, AllocationLostRequest
from src.domain.entities.employee import Employee
from src.domain.entities.asset_allocation import AssetAllocation
from src.domain.enums import AllocationStatus
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.asset_allocation_service import AssetAllocationService, get_asset_allocation_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[AssetAllocation],
    dependencies=[Depends(require_permission("perm_allocations_view"))]
)
def list_allocations(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted allocations"),
    status: AllocationStatus | None = Query(default=None, description="Filter by status"),
    employeeId: str | None = Query(default=None, alias="employeeId", description="Filter by employee"),
    assetId: str | None = Query(default=None, alias="assetId", description="Filter by asset"),
    service: AssetAllocationService = Depends(get_asset_allocation_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value
    if employeeId is not None:
        filters["employeeId"] = employeeId
    if assetId is not None:
        filters["assetId"] = assetId

    items, next_cursor = service.list_allocations(
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
    response_model=SingleResponse[AssetAllocation],
    dependencies=[Depends(require_permission("perm_allocations_view"))]
)
def get_allocation(
    allocation_id: str = Path(..., alias="id"),
    service: AssetAllocationService = Depends(get_asset_allocation_service)
):
    alloc = service.get_by_id(allocation_id)
    if not alloc or alloc.is_deleted:
        raise NotFoundError(f"Allocation {allocation_id} not found")
    return SingleResponse(data=alloc)

@router.post(
    "/assets/{assetId}/allocate",
    response_model=SingleResponse[AssetAllocation],
    status_code=201
)
def allocate_asset(
    payload: AllocationCreate,
    asset_id: str = Path(..., alias="assetId"),
    current_user: Employee = Depends(require_permission("perm_allocations_manage")),
    service: AssetAllocationService = Depends(get_asset_allocation_service)
):
    alloc = service.allocate_asset(
        asset_id=asset_id,
        employee_id=payload.employee_id,
        expected_return_date=payload.expected_return_date,
        notes=payload.notes,
        actor_id=current_user.id
    )
    return SingleResponse(data=alloc)

@router.post(
    "/{id}/return",
    response_model=SingleResponse[AssetAllocation]
)
def return_asset(
    payload: AllocationReturnRequest,
    allocation_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_allocations_manage")),
    service: AssetAllocationService = Depends(get_asset_allocation_service)
):
    alloc = service.return_asset(
        allocation_id=allocation_id,
        condition_at_return=payload.condition_at_return,
        notes=payload.notes,
        actor_id=current_user.id
    )
    return SingleResponse(data=alloc)

@router.post(
    "/{id}/lost",
    response_model=SingleResponse[AssetAllocation]
)
def report_lost_allocation(
    payload: AllocationLostRequest,
    allocation_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_allocations_manage")),
    service: AssetAllocationService = Depends(get_asset_allocation_service)
):
    alloc = service.report_lost_allocation(
        allocation_id=allocation_id,
        notes=payload.notes,
        actor_id=current_user.id
    )
    return SingleResponse(data=alloc)
