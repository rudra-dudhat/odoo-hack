from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.assets import AssetCategoryCreate, AssetCategoryUpdate
from src.domain.entities.employee import Employee
from src.domain.entities.asset_category import AssetCategory
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.asset_service import AssetService, get_asset_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[AssetCategory],
    dependencies=[Depends(require_permission("perm_asset_categories_view"))]
)
def list_categories(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted categories"),
    service: AssetService = Depends(get_asset_service)
):
    items, next_cursor = service.list_categories(
        limit=pagination.limit,
        cursor=pagination.cursor,
        sort_by=pagination.sort_by,
        sort_dir=pagination.sort_dir,
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
    response_model=SingleResponse[AssetCategory],
    dependencies=[Depends(require_permission("perm_asset_categories_view"))]
)
def get_category(
    category_id: str = Path(..., alias="id"),
    service: AssetService = Depends(get_asset_service)
):
    cat = service.get_category_by_id(category_id)
    if not cat or cat.is_deleted:
        raise NotFoundError(f"Category {category_id} not found")
    return SingleResponse(data=cat)

@router.post(
    "/",
    response_model=SingleResponse[AssetCategory],
    status_code=201
)
def create_category(
    payload: AssetCategoryCreate,
    current_user: Employee = Depends(require_permission("perm_asset_categories_manage")),
    service: AssetService = Depends(get_asset_service)
):
    cat = service.create_category(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        parent_category_id=payload.parent_category_id,
        depreciation_method=payload.depreciation_method,
        default_useful_life_months=payload.default_useful_life_months,
        actor_id=current_user.id
    )
    return SingleResponse(data=cat)

@router.put(
    "/{id}",
    response_model=SingleResponse[AssetCategory]
)
def update_category(
    payload: AssetCategoryUpdate,
    category_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_asset_categories_manage")),
    service: AssetService = Depends(get_asset_service)
):
    cat = service.update_category(
        category_id=category_id,
        name=payload.name,
        description=payload.description,
        parent_category_id=payload.parent_category_id,
        depreciation_method=payload.depreciation_method,
        default_useful_life_months=payload.default_useful_life_months,
        actor_id=current_user.id
    )
    return SingleResponse(data=cat)

@router.delete(
    "/{id}",
    status_code=204
)
def delete_category(
    category_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_asset_categories_manage")),
    service: AssetService = Depends(get_asset_service)
):
    service.soft_delete_category(category_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_category(
    category_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_asset_categories_manage")),
    service: AssetService = Depends(get_asset_service)
):
    service.restore_category(category_id, current_user.id)
    return SingleResponse(data=None)
