from src.domain.entities.asset_category import AssetCategory
from src.domain.repositories.asset_category_repository import AssetCategoryRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreAssetCategoryRepository(BaseFirestoreRepository[AssetCategory], AssetCategoryRepository):
    def __init__(self):
        super().__init__("assetCategories", AssetCategory)

    def find_by_code(self, code: str) -> AssetCategory | None:
        snapshots = self._collection_ref.where("code", "==", code).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return AssetCategory.model_validate(data)

    def find_by_name(self, name: str) -> AssetCategory | None:
        snapshots = self._collection_ref.where("name", "==", name).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return AssetCategory.model_validate(data)

_repository_instance = None

def get_asset_category_repository() -> AssetCategoryRepository:
    """Dependency injection factory for AssetCategoryRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreAssetCategoryRepository()
    return _repository_instance
