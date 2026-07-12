from abc import abstractmethod
from src.domain.entities.notification import Notification
from src.domain.repositories.base_repository import BaseRepository

class NotificationRepository(BaseRepository[Notification]):
    @abstractmethod
    def mark_as_read(self, notification_id: str, employee_id: str) -> None:
        """Mark a notification as read. recipientId must equal employee_id."""
        pass

    @abstractmethod
    def mark_all_as_read(self, employee_id: str) -> None:
        """Mark all unread notifications for a recipient as read."""
        pass
