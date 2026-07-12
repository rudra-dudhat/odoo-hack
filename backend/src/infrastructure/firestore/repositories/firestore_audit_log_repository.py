from src.domain.entities.audit_log_entry import AuditLogEntry
from src.domain.repositories.audit_log_repository import AuditLogRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreAuditLogRepository(BaseFirestoreRepository[AuditLogEntry], AuditLogRepository):
    def __init__(self):
        super().__init__("auditLogs", AuditLogEntry)

_repository_instance = None

def get_audit_log_repository() -> AuditLogRepository:
    """Dependency injection factory for AuditLogRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreAuditLogRepository()
    return _repository_instance
