from google.cloud import firestore
from src.domain.entities.audit_cycle import AuditCycle, AuditReport
from src.domain.repositories.audit_cycle_repository import AuditCycleRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreAuditCycleRepository(BaseFirestoreRepository[AuditCycle], AuditCycleRepository):
    def __init__(self):
        super().__init__("auditCycles", AuditCycle)

    def create_report(self, cycle_id: str, report: AuditReport) -> AuditReport:
        subcol_ref = self._collection_ref.document(cycle_id).collection("reports")
        doc_ref = subcol_ref.document()
        
        data = report.model_dump(by_alias=True, exclude_none=True)
        data.pop("id", None)
        
        data["auditedAt"] = firestore.SERVER_TIMESTAMP
        data["createdAt"] = firestore.SERVER_TIMESTAMP
        data["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        doc_ref.set(data)
        
        snap = doc_ref.get()
        rdata = snap.to_dict() or {}
        rdata["id"] = snap.id
        return AuditReport.model_validate(rdata)

    def list_reports(self, cycle_id: str) -> list[AuditReport]:
        subcol_ref = self._collection_ref.document(cycle_id).collection("reports")
        snapshots = subcol_ref.order_by("auditedAt", direction=firestore.Query.DESCENDING).get()
        
        reports = []
        for snap in snapshots:
            data = snap.to_dict() or {}
            data["id"] = snap.id
            reports.append(AuditReport.model_validate(data))
        return reports

    def find_report_by_asset(self, cycle_id: str, asset_id: str) -> AuditReport | None:
        subcol_ref = self._collection_ref.document(cycle_id).collection("reports")
        snapshots = subcol_ref.where("assetId", "==", asset_id).where("isDeleted", "==", False).limit(1).get()
        if not snapshots:
            return None
        snap = snapshots[0]
        data = snap.to_dict() or {}
        data["id"] = snap.id
        return AuditReport.model_validate(data)

_repository_instance = None

def get_audit_cycle_repository() -> AuditCycleRepository:
    """Dependency injection factory for AuditCycleRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreAuditCycleRepository()
    return _repository_instance
