from src.domain.entities.employee import Employee
from src.domain.repositories.employee_repository import EmployeeRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreEmployeeRepository(BaseFirestoreRepository[Employee], EmployeeRepository):
    def __init__(self):
        super().__init__("employees", Employee)

    def find_by_email(self, email: str) -> Employee | None:
        snapshots = self._collection_ref.where("email", "==", email).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Employee.model_validate(data)

    def find_by_code(self, code: str) -> Employee | None:
        snapshots = self._collection_ref.where("employeeCode", "==", code).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return Employee.model_validate(data)

_repository_instance = None

def get_employee_repository() -> EmployeeRepository:
    """Dependency injection factory for EmployeeRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreEmployeeRepository()
    return _repository_instance
