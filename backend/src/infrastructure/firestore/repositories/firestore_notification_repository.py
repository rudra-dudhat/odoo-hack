from google.cloud import firestore
from src.domain.entities.notification import Notification
from src.domain.repositories.notification_repository import NotificationRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository
from src.shared.errors import NotFoundError, ForbiddenError

class FirestoreNotificationRepository(BaseFirestoreRepository[Notification], NotificationRepository):
    def __init__(self):
        super().__init__("notifications", Notification)

    def mark_as_read(self, notification_id: str, employee_id: str) -> None:
        doc_ref = self._collection_ref.document(notification_id)
        snap = doc_ref.get()
        if not snap.exists or snap.to_dict().get("isDeleted", False):
            raise NotFoundError(f"Notification {notification_id} not found")
            
        data = snap.to_dict() or {}
        if data.get("recipientId") != employee_id:
            raise ForbiddenError("Cannot access another employee's notification")
            
        doc_ref.update({
            "isRead": True,
            "readAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

    def mark_all_as_read(self, employee_id: str) -> None:
        snapshots = self._collection_ref.where("recipientId", "==", employee_id)\
                                        .where("isRead", "==", False)\
                                        .where("isDeleted", "==", False).get()
        # Batch updates
        if not snapshots:
            return
            
        batch = self._collection_ref.database.batch()
        for snap in snapshots:
            batch.update(snap.reference, {
                "isRead": True,
                "readAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        batch.commit()

_repository_instance = None

def get_notification_repository() -> NotificationRepository:
    """Dependency injection factory for NotificationRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreNotificationRepository()
    return _repository_instance
