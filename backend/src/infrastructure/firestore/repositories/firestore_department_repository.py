from src.domain.entities.department import Department
from src.domain.repositories.department_repository import DepartmentRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreDepartmentRepository(BaseFirestoreRepository[Department], DepartmentRepository):
    def __init__(self):
        super().__init__("departments", Department)

    def find_by_code(self, code: str) -> Department | None:
        snapshots = self._collection_ref.where("code", "==", code).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Department.model_validate(data)

    def find_by_name(self, name: str) -> Department | None:
        snapshots = self._collection_ref.where("name", "==", name).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Department.model_validate(data)

_repository_instance = None

def get_department_repository() -> DepartmentRepository:
    """Dependency injection factory for DepartmentRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreDepartmentRepository()
    return _repository_instance
