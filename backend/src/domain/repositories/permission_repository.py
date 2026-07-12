from abc import abstractmethod
from src.domain.entities.permission import Permission
from src.domain.repositories.base_repository import BaseRepository

class PermissionRepository(BaseRepository[Permission]):
    @abstractmethod
    def find_by_key(self, key: str) -> Permission | None:
        """Find a permission by its machine key (e.g. 'asset.create')."""
        pass
