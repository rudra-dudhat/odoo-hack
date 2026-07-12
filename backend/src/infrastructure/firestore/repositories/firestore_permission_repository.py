from src.domain.entities.permission import Permission
from src.domain.repositories.permission_repository import PermissionRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestorePermissionRepository(BaseFirestoreRepository[Permission], PermissionRepository):
    def __init__(self):
        super().__init__("permissions", Permission)

    def find_by_key(self, key: str) -> Permission | None:
        snapshots = self._collection_ref.where("key", "==", key).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Permission.model_validate(data)

_repository_instance = None

def get_permission_repository() -> PermissionRepository:
    """Dependency injection factory for PermissionRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestorePermissionRepository()
    return _repository_instance
