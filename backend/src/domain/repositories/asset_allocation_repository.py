from abc import abstractmethod
from src.domain.entities.asset_allocation import AssetAllocation
from src.domain.repositories.base_repository import BaseRepository

class AssetAllocationRepository(BaseRepository[AssetAllocation]):
    @abstractmethod
    def find_active_allocation_for_asset(self, asset_id: str) -> AssetAllocation | None:
        """Find the single active (or overdue) allocation for a given asset."""
        pass

    @abstractmethod
    def find_active_allocations_for_employee(self, employee_id: str) -> list[AssetAllocation]:
        """Find all active (or overdue) allocations for an employee."""
        pass
