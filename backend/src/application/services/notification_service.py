from fastapi import Depends
from src.domain.entities.notification import Notification
from src.domain.repositories.notification_repository import NotificationRepository
from src.infrastructure.firestore.repositories.firestore_notification_repository import get_notification_repository
from src.shared.errors import NotFoundError, ForbiddenError

class NotificationService:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    def list_my_notifications(
        self,
        employee_id: str,
        limit: int = 25,
        cursor: str | None = None
    ) -> tuple[list[Notification], str | None]:
        """
        List notifications for the requesting employee only.
        Enforces security isolation at service boundaries.
        """
        filters = {"recipientId": employee_id}
        # Inbox unread-first / newest-first list
        return self.notification_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by="createdAt",
            sort_dir="desc",
            filters=filters
        )

    def mark_read(self, notification_id: str, employee_id: str) -> None:
        """Mark a notification as read, validating ownership."""
        self.notification_repo.mark_as_read(notification_id, employee_id)

    def mark_all_read(self, employee_id: str) -> None:
        """Mark all unread notifications for the caller as read."""
        self.notification_repo.mark_all_as_read(employee_id)

    def clear_notification(self, notification_id: str, employee_id: str) -> None:
        """
        Hard delete a notification (user-dismissed/cleared).
        Enforces that users can only clear their own notifications.
        """
        notif = self.notification_repo.get_by_id(notification_id)
        if not notif or notif.is_deleted:
            raise NotFoundError(f"Notification {notification_id} not found")
            
        if notif.recipient_id != employee_id:
            raise ForbiddenError("Cannot clear another employee's notification")
            
        # Hard delete is permitted for notifications per Section 11.2
        self.notification_repo.hard_delete(notification_id)

def get_notification_service(
    repo: NotificationRepository = Depends(get_notification_repository)
) -> NotificationService:
    """Dependency injection factory for NotificationService."""
    return NotificationService(repo)
