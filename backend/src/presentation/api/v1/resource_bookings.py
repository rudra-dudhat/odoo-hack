from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.application.dtos.bookings import BookingCreate, BookingCancelRequest
from src.domain.entities.employee import Employee
from src.domain.entities.resource_booking import ResourceBooking
from src.domain.enums import BookingStatus
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.rbac import require_permission, _get_resolved_permissions_for_role
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.resource_service import ResourceService, get_shared_resource_service
from src.shared.errors import NotFoundError, ForbiddenError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[ResourceBooking],
    dependencies=[Depends(require_permission("perm_bookings_view"))]
)
def list_bookings(
    pagination: PaginationParams = Depends(get_pagination_params),
    includeDeleted: bool = Query(default=False, description="Include soft-deleted bookings"),
    status: BookingStatus | None = Query(default=None, description="Filter by status"),
    employeeId: str | None = Query(default=None, alias="employeeId", description="Filter by employee"),
    resourceId: str | None = Query(default=None, alias="resourceId", description="Filter by resource"),
    service: ResourceService = Depends(get_shared_resource_service)
):
    filters = {}
    if status is not None:
        filters["status"] = status.value
    if employeeId is not None:
        filters["employeeId"] = employeeId
    if resourceId is not None:
        filters["resourceId"] = resourceId

    items, next_cursor = service.list_bookings(
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
    response_model=SingleResponse[ResourceBooking],
    dependencies=[Depends(require_permission("perm_bookings_view"))]
)
def get_booking(
    booking_id: str = Path(..., alias="id"),
    service: ResourceService = Depends(get_shared_resource_service)
):
    booking = service.get_booking_by_id(booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError(f"Booking {booking_id} not found")
    return SingleResponse(data=booking)

@router.post(
    "/resources/{resourceId}/bookings",
    response_model=SingleResponse[ResourceBooking],
    status_code=201
)
def create_booking(
    payload: BookingCreate,
    resource_id: str = Path(..., alias="resourceId"),
    current_user: Employee = Depends(require_permission("perm_bookings_manage")),
    service: ResourceService = Depends(get_shared_resource_service)
):
    booking = service.create_booking(
        resource_id=resource_id,
        employee_id=current_user.id,
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
        attendee_ids=payload.attendee_ids,
        actor_id=current_user.id
    )
    return SingleResponse(data=booking)

@router.post(
    "/{id}/cancel",
    response_model=SingleResponse[ResourceBooking]
)
def cancel_booking(
    payload: BookingCancelRequest,
    booking_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(get_current_employee),
    service: ResourceService = Depends(get_shared_resource_service)
):
    # Fetch booking
    booking = service.get_booking_by_id(booking_id)
    if not booking or booking.is_deleted:
        raise NotFoundError(f"Booking {booking_id} not found")
        
    perms = _get_resolved_permissions_for_role(current_user.role_id)
    is_owner = booking.employee_id == current_user.id
    
    # Enforce cancel RBAC + owner checks
    if "perm_bookings_cancel_any" in perms:
        # Admins/Managers with cancel_any can cancel any booking
        pass
    elif "perm_bookings_manage" in perms and is_owner:
        # Standard employees can only cancel their own bookings
        pass
    else:
        raise ForbiddenError("Insufficient permissions: cannot cancel this booking")
        
    updated = service.cancel_booking(booking_id, payload.cancellation_reason, current_user.id)
    return SingleResponse(data=updated)
