from fastapi import APIRouter, Depends, Query, Path
from src.application.dtos.base import SingleResponse, ListResponse, PaginatedMeta
from src.domain.entities.employee import Employee
from src.domain.entities.notification import Notification
from src.presentation.dependencies.auth import get_current_employee
from src.presentation.dependencies.pagination import get_pagination_params, PaginationParams
from src.application.services.notification_service import NotificationService, get_notification_service
from src.shared.errors import NotFoundError

router = APIRouter()

@router.get(
    "/",
    response_model=ListResponse[Notification]
)
def list_my_notifications(
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: Employee = Depends(get_current_employee),
    service: NotificationService = Depends(get_notification_service)
):
    items, next_cursor = service.list_my_notifications(
        employee_id=current_user.id,
        limit=pagination.limit,
        cursor=pagination.cursor
    )
    return ListResponse(
        data=items,
        meta=PaginatedMeta(
            nextCursor=next_cursor,
            hasMore=next_cursor is not None
        )
    )

@router.post(
    "/{id}/read",
    response_model=SingleResponse[None]
)
def mark_notification_as_read(
    notification_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(get_current_employee),
    service: NotificationService = Depends(get_notification_service)
):
    service.mark_read(notification_id, current_user.id)
    return SingleResponse(data=None)

@router.post(
    "/read-all",
    response_model=SingleResponse[None]
)
def mark_all_notifications_as_read(
    current_user: Employee = Depends(get_current_employee),
    service: NotificationService = Depends(get_notification_service)
):
    service.mark_all_read(current_user.id)
    return SingleResponse(data=None)

@router.delete(
    "/{id}",
    status_code=204
)
def clear_notification(
    notification_id: str = Path(..., alias="id"),
    current_user: Employee = Depends(get_current_employee),
    service: NotificationService = Depends(get_notification_service)
):
    service.clear_notification(notification_id, current_user.id)
