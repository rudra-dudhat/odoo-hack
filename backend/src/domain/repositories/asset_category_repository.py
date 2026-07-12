from abc import abstractmethod
from src.domain.entities.asset_category import AssetCategory
from src.domain.repositories.base_repository import BaseRepository

class AssetCategoryRepository(BaseRepository[AssetCategory]):
    @abstractmethod
    def find_by_code(self, code: str) -> AssetCategory | None:
        """Find a non-deleted asset category by code."""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> AssetCategory | None:
        """Find a non-deleted asset category by name."""
        pass
