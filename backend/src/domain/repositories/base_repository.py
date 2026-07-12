from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, doc_id: str) -> T | None:
        """Fetch a single document by its ID. Returns None if not found."""
        pass

    @abstractmethod
    def list(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False
    ) -> tuple[list[T], str | None]:
        """List documents with pagination, sorting, and filtering. Returns (items, next_cursor)."""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new document. Throws ConflictError if ID already exists."""
        pass

    @abstractmethod
    def update(self, doc_id: str, updates: dict[str, Any], updated_by: str) -> T:
        """Partially update a document by ID. Merges updates and bumps updatedAt/updatedBy."""
        pass

    @abstractmethod
    def soft_delete(self, doc_id: str, deleted_by: str) -> None:
        """Soft delete a document by setting isDeleted=True, deletedAt, and deletedBy."""
        pass

    @abstractmethod
    def restore(self, doc_id: str) -> None:
        """Restore a soft-deleted document by resetting isDeleted=False, deletedAt/By=None."""
        pass

    @abstractmethod
    def hard_delete(self, doc_id: str) -> None:
        """Hard delete a document by deleting it from the collection."""
        pass
