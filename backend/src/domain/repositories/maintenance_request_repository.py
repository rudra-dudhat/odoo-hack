from abc import abstractmethod
from src.domain.entities.maintenance_request import MaintenanceRequest, MaintenanceApproval, MaintenanceLog
from src.domain.repositories.base_repository import BaseRepository

class MaintenanceRequestRepository(BaseRepository[MaintenanceRequest]):
    @abstractmethod
    def create_approval(self, request_id: str, approval: MaintenanceApproval) -> MaintenanceApproval:
        """Create a new approval entry under a maintenance request."""
        pass

    @abstractmethod
    def list_approvals(self, request_id: str) -> list[MaintenanceApproval]:
        """List all approvals for a maintenance request."""
        pass

    @abstractmethod
    def create_log(self, request_id: str, log: MaintenanceLog) -> MaintenanceLog:
        """Create a new log entry under a maintenance request."""
        pass

    @abstractmethod
    def list_logs(self, request_id: str) -> list[MaintenanceLog]:
        """List all logs for a maintenance request."""
        pass
