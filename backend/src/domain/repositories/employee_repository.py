from abc import abstractmethod
from src.domain.entities.employee import Employee
from src.domain.repositories.base_repository import BaseRepository

class EmployeeRepository(BaseRepository[Employee]):
    @abstractmethod
    def find_by_email(self, email: str) -> Employee | None:
        """Find a non-deleted employee by email."""
        pass

    @abstractmethod
    def find_by_code(self, code: str) -> Employee | None:
        """Find a non-deleted employee by employee code."""
        pass
