from abc import abstractmethod
from src.domain.entities.department import Department
from src.domain.repositories.base_repository import BaseRepository

class DepartmentRepository(BaseRepository[Department]):
    @abstractmethod
    def find_by_code(self, code: str) -> Department | None:
        """Find a non-deleted department by its code."""
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Department | None:
        """Find a non-deleted department by its name."""
        pass
