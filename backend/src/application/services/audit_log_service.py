from fastapi import Depends
from src.domain.entities.audit_log_entry import AuditLogEntry
from src.domain.enums import AuditLogAction
from src.domain.repositories.audit_log_repository import AuditLogRepository
from src.infrastructure.firestore.repositories.firestore_audit_log_repository import get_audit_log_repository

class AuditLogService:
    def __init__(self, audit_log_repo: AuditLogRepository):
        self.audit_log_repo = audit_log_repo

    def log_action(
        self,
        entity_type: str,
        entity_id: str,
        action: AuditLogAction,
        performed_by: str,
        changed_fields: list[str] | None = None,
        before_snapshot: dict | None = None,
        after_snapshot: dict | None = None,
        ip_address: str | None = None
    ) -> AuditLogEntry:
        """
        Record a system-wide mutation event into the immutable audit trail.
        """
        entry = AuditLogEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=performed_by,
            changed_fields=changed_fields or [],
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            ip_address=ip_address
        )
        return self.audit_log_repo.create(entry)
        
    def get_by_id(self, log_id: str) -> AuditLogEntry | None:
        return self.audit_log_repo.get_by_id(log_id)
        
    def list_logs(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
        filters: dict | None = None
    ) -> tuple[list[AuditLogEntry], str | None]:
        # Enforce compliance view sorting default (newest first)
        actual_sort_by = sort_by or "createdAt"
        return self.audit_log_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters
        )

def get_audit_log_service(
    repo: AuditLogRepository = Depends(get_audit_log_repository)
) -> AuditLogService:
    """Dependency injection factory for AuditLogService."""
    return AuditLogService(repo)
