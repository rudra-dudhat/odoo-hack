from src.domain.entities.asset_allocation import AssetAllocation
from src.domain.repositories.asset_allocation_repository import AssetAllocationRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreAssetAllocationRepository(BaseFirestoreRepository[AssetAllocation], AssetAllocationRepository):
    def __init__(self):
        super().__init__("assetAllocations", AssetAllocation)

    def find_active_allocation_for_asset(self, asset_id: str) -> AssetAllocation | None:
        # Fetch active or overdue allocations for the asset
        snapshots = self._collection_ref.where("assetId", "==", asset_id)\
                                        .where("status", "in", ["active", "overdue"])\
                                        .where("isDeleted", "==", False)\
                                        .limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return AssetAllocation.model_validate(data)

    def find_active_allocations_for_employee(self, employee_id: str) -> list[AssetAllocation]:
        snapshots = self._collection_ref.where("employeeId", "==", employee_id)\
                                        .where("status", "in", ["active", "overdue"])\
                                        .where("isDeleted", "==", False).get()
        allocations = []
        for snap in snapshots:
            data = snap.to_dict() or {}
            data["id"] = snap.id
            allocations.append(AssetAllocation.model_validate(data))
        return allocations

_repository_instance = None

def get_asset_allocation_repository() -> AssetAllocationRepository:
    """Dependency injection factory for AssetAllocationRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreAssetAllocationRepository()
    return _repository_instance
