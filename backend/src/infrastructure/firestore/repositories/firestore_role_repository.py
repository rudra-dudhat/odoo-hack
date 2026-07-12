from src.domain.entities.role import Role
from src.domain.repositories.role_repository import RoleRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreRoleRepository(BaseFirestoreRepository[Role], RoleRepository):
    def __init__(self):
        super().__init__("roles", Role)

    def find_by_name(self, name: str) -> Role | None:
        snapshots = self._collection_ref.where("name", "==", name).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Role.model_validate(data)

_repository_instance = None

def get_role_repository() -> RoleRepository:
    """Dependency injection factory for RoleRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreRoleRepository()
    return _repository_instance
