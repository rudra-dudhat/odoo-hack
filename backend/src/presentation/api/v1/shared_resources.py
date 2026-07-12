from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.resources import SharedResourceCreate, SharedResourceUpdate
from src.domain.entities.employee import Employee
from src.domain.entities.shared_resource import SharedResource, BookingRules
from src.presentation.dependencies.rbac import require_permission
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.resource_service import ResourceService, get_shared_resource_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[SharedResource],
    dependencies=[Depends(require_permission("perm_resources_view"))]
)
def list_resources(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted resources"),
    type: str | None = Query(default=None, description="Filter by resource type"),
    location: str | None = Query(default=None, description="Filter by location"),
    service: ResourceService = Depends(get_shared_resource_service)
):
    filters = {}
    if type is not None:
        filters["type"] = type
    if location is not None:
        filters["location"] = location

    items, next_cursor = service.list_resources(
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
    response_model=SingleResponse[SharedResource],
    dependencies=[Depends(require_permission("perm_resources_view"))]
)
def get_resource(
    resource_id: str = Path(..., alias="id"),
    service: ResourceService = Depends(get_shared_resource_service)
):
    res = service.get_resource_by_id(resource_id)
    if not res or res.is_deleted:
        raise NotFoundError(f"Resource {resource_id} not found")
    return SingleResponse(data=res)

@router.post(
    "/",
    response_model=SingleResponse[SharedResource],
    status_code=201
)
def create_resource(
    payload: SharedResourceCreate,
    current_user: Employee = Depends(require_permission("perm_resources_manage")),
    service: ResourceService = Depends(get_shared_resource_service)
):
    rules = BookingRules(
        min_duration_minutes=payload.booking_rules.min_duration_minutes,
        max_duration_minutes=payload.booking_rules.max_duration_minutes,
        advance_booking_days=payload.booking_rules.advance_booking_days
    )
    res = service.create_resource(
        name=payload.name,
        type_str=payload.type,
        capacity=payload.capacity,
        location=payload.location,
        amenities=payload.amenities,
        image_urls=payload.image_urls,
        booking_rules=rules,
        actor_id=current_user.id
    )
    return SingleResponse(data=res)

@router.put(
    "/{id}",
    response_model=SingleResponse[SharedResource]
)
def update_resource(
    payload: SharedResourceUpdate,
    resource_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_resources_manage")),
    service: ResourceService = Depends(get_shared_resource_service)
):
    rules = None
    if payload.booking_rules is not None:
        rules = BookingRules(
            min_duration_minutes=payload.booking_rules.min_duration_minutes,
            max_duration_minutes=payload.booking_rules.max_duration_minutes,
            advance_booking_days=payload.booking_rules.advance_booking_days
        )
    res = service.update_resource(
        resource_id=resource_id,
        name=payload.name,
        type_str=payload.type,
        capacity=payload.capacity,
        location=payload.location,
        amenities=payload.amenities,
        image_urls=payload.image_urls,
        booking_rules=rules,
        actor_id=current_user.id
    )
    return SingleResponse(data=res)

@router.delete(
    "/{id}",
    status_code=204
)
def delete_resource(
    resource_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_resources_manage")),
    service: ResourceService = Depends(get_shared_resource_service)
):
    service.soft_delete_resource(resource_id, current_user.id)

@router.post(
    "/{id}/restore",
    response_model=SingleResponse[None]
)
def restore_resource(
    resource_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(require_permission("perm_resources_manage")),
    service: ResourceService = Depends(get_shared_resource_service)
):
    service.restore_resource(resource_id, current_user.id)
    return SingleResponse(data=None)
