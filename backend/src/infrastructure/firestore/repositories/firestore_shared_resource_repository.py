from src.domain.entities.shared_resource import SharedResource
from src.domain.repositories.shared_resource_repository import SharedResourceRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreSharedResourceRepository(BaseFirestoreRepository[SharedResource], SharedResourceRepository):
    def __init__(self):
        super().__init__("sharedResources", SharedResource)

_repository_instance = None

def get_shared_resource_repository() -> SharedResourceRepository:
    """Dependency injection factory for SharedResourceRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreSharedResourceRepository()
    return _repository_instance
