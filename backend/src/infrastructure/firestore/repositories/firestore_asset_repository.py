from src.domain.entities.asset import Asset
from src.domain.repositories.asset_repository import AssetRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreAssetRepository(BaseFirestoreRepository[Asset], AssetRepository):
    def __init__(self):
        super().__init__("assets", Asset)

_repository_instance = None

def get_asset_repository() -> AssetRepository:
    """Dependency injection factory for AssetRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreAssetRepository()
    return _repository_instance
