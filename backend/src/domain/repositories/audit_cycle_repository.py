from abc import abstractmethod
from src.domain.entities.audit_cycle import AuditCycle, AuditReport
from src.domain.repositories.base_repository import BaseRepository

class AuditCycleRepository(BaseRepository[AuditCycle]):
    @abstractmethod
    def create_report(self, cycle_id: str, report: AuditReport) -> AuditReport:
        """Submit an audit report for an asset within an audit cycle."""
        pass

    @abstractmethod
    def list_reports(self, cycle_id: str) -> list[AuditReport]:
        """List all audit reports submitted under an audit cycle."""
        pass

    @abstractmethod
    def find_report_by_asset(self, cycle_id: str, asset_id: str) -> AuditReport | None:
        """Find an audit report for a specific asset in a cycle."""
        pass
