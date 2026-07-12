from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.assets import AssetCreate, AssetUpdate, AssetResponse, AssetRetireRequest, AssetLostRequest
from src.domain.entities.employee import Employee
from src.domain.enums import AssetStatus, AssetCondition
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission, _get_resolved_permissions_for_role
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.asset_service import AssetService, get_asset_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[AssetResponse]
)
def list_assets(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted assets"),
    status: AssetStatus | None = Query(default=None, description="Filter by status"),
    categoryId: str | None = Query(default=None, alias="categoryId", description="Filter by category"),
    departmentId: str | None = Query(default=None, alias="departmentId", description="Filter by department"),
    condition: AssetCondition | None = Query(default=None, description="Filter by condition"),
    current_user: Employee = Depends(require_permission("perm_assets_view")),
    service: AssetService = Depends(get_asset_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value
    if categoryId is not None:
        filters["categoryId"] = categoryId
    if departmentId is not None:
        filters["departmentId"] = departmentId
    if condition is not None:
        filters["condition"] = condition.value

    items, next_cursor = service.list_assets(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
        filters=filters,
        include_deleted=includeDeleted
    )
    
    # Financial permission check
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    
    data = [AssetResponse.from_entity(item, include_financial=has_financial) for item in items]
    
    return ListResponse(
        data=data,
        meta=PaginatedMeta(
            nextCursor=next_cursor,
            hasMore=next_cursor is not None
        )
    )

@router.get(
    "/{id}",
    response_model=SingleResponse[AssetResponse]
)
def get_asset(
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_view")),
    service: AssetService = Depends(get_asset_service)
):
    asset = service.get_asset_by_id(asset_id)
    if not asset or asset.is_deleted:
        raise NotFoundError(f"Asset {asset_id} not found")
        
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    
    return SingleResponse(data=AssetResponse.from_entity(asset, include_financial=has_financial))

@router.post(
    "/",
    response_model=SingleResponse[AssetResponse],
    status_code=201
)
def create_asset(
    payload: AssetCreate,
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    asset = service.create_asset(
        name=payload.name,
        category_id=payload.category_id,
        department_id=payload.department_id,
        serial_number=payload.serial_number,
        manufacturer=payload.manufacturer,
        model=payload.model,
        purchase_date=payload.purchase_date,
        purchase_cost=payload.purchase_cost,
        currency=payload.currency,
        warranty_expiry_date=payload.warranty_expiry_date,
        location=payload.location,
        image_urls=payload.image_urls,
        condition=payload.condition,
        actor_id=current_user.id
    )
    # Asset creation actor has perm_assets_manage which usually includes financial
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    return SingleResponse(data=AssetResponse.from_entity(asset, include_financial=has_financial))

@router.put(
    "/{id}",
    response_model=SingleResponse[AssetResponse]
)
def update_asset(
    payload: AssetUpdate,
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    asset = service.update_asset(
        asset_id=asset_id,
        name=payload.name,
        category_id=payload.category_id,
        department_id=payload.department_id,
        serial_number=payload.serial_number,
        manufacturer=payload.manufacturer,
        model=payload.model,
        purchase_date=payload.purchase_date,
        purchase_cost=payload.purchase_cost,
        currency=payload.currency,
        warranty_expiry_date=payload.warranty_expiry_date,
        location=payload.location,
        image_urls=payload.image_urls,
        condition=payload.condition,
        actor_id=current_user.id
    )
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    return SingleResponse(data=AssetResponse.from_entity(asset, include_financial=has_financial))

@router.post(
    "/{id}/retire",
    response_model=SingleResponse[AssetResponse]
)
def retire_asset(
    payload: AssetRetireRequest,
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    asset = service.retire_asset(asset_id, payload.note, current_user.id)
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    return SingleResponse(data=AssetResponse.from_entity(asset, include_financial=has_financial))

@router.post(
    "/{id}/lost",
    response_model=SingleResponse[AssetResponse]
)
def report_lost_asset(
    payload: AssetLostRequest,
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    asset = service.report_lost_asset(asset_id, payload.note, current_user.id)
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    has_financial = "perm_assets_financial_view" in perms
    return SingleResponse(data=AssetResponse.from_entity(asset, include_financial=has_financial))

@router.delete(
    "/{id}",
    status_code=204
)
def delete_asset(
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    service.soft_delete_asset(asset_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_asset(
    asset_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_assets_manage")),
    service: AssetService = Depends(get_asset_service)
):
    service.restore_asset(asset_id, current_user.id)
    return SingleResponse(data=None)
