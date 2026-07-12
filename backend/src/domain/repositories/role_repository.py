from abc import abstractmethod
from src.domain.entities.role import Role
from src.domain.repositories.base_repository import BaseRepository

class RoleRepository(BaseRepository[Role]):
    @abstractmethod
    def find_by_name(self, name: str) -> Role | None:
        """Find a non-deleted role by name."""
        pass
