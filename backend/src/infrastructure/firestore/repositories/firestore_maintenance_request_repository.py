from google.cloud import firestore
from src.domain.entities.maintenance_request import MaintenanceRequest, MaintenanceApproval, MaintenanceLog
from src.domain.repositories.maintenance_request_repository import MaintenanceRequestRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository
from src.infrastructure.firestore.client import db

class FirestoreMaintenanceRequestRepository(BaseFirestoreRepository[MaintenanceRequest], MaintenanceRequestRepository):
    def __init__(self):
        super().__init__("maintenanceRequests", MaintenanceRequest)

    def create_approval(self, request_id: str, approval: MaintenanceApproval) -> MaintenanceApproval:
        subcol_ref = self._collection_ref.document(request_id).collection("approvals")
        doc_ref = subcol_ref.document()
        
        # Serialize with camelCase aliases
        data = approval.model_dump(by_alias=True, exclude_none=True)
        data.pop("id", None)
        
        data["decidedAt"] = firestore.SERVER_TIMESTAMP
        data["createdAt"] = firestore.SERVER_TIMESTAMP
        data["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        doc_ref.set(data)
        
        snap = doc_ref.get()
        rdata = snap.to_dict() or {}
        rdata["id"] = snap.id
        return MaintenanceApproval.model_validate(rdata)

    def list_approvals(self, request_id: str) -> list[MaintenanceApproval]:
        subcol_ref = self._collection_ref.document(request_id).collection("approvals")
        # Default order by decidedAt
        snapshots = subcol_ref.order_by("decidedAt", direction=firestore.Query.ASCENDING).get()
        
        approvals = []
        for snap in snapshots:
            data = snap.to_dict() or {}
            data["id"] = snap.id
            approvals.append(MaintenanceApproval.model_validate(data))
        return approvals

    def create_log(self, request_id: str, log: MaintenanceLog) -> MaintenanceLog:
        subcol_ref = self._collection_ref.document(request_id).collection("logs")
        doc_ref = subcol_ref.document()
        
        data = log.model_dump(by_alias=True, exclude_none=True)
        data.pop("id", None)
        
        data["createdAt"] = firestore.SERVER_TIMESTAMP
        data["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        doc_ref.set(data)
        
        snap = doc_ref.get()
        rdata = snap.to_dict() or {}
        rdata["id"] = snap.id
        return MaintenanceLog.model_validate(rdata)

    def list_logs(self, request_id: str) -> list[MaintenanceLog]:
        subcol_ref = self._collection_ref.document(request_id).collection("logs")
        snapshots = subcol_ref.order_by("createdAt", direction=firestore.Query.ASCENDING).get()
        
        logs = []
        for snap in snapshots:
            data = snap.to_dict() or {}
            data["id"] = snap.id
            logs.append(MaintenanceLog.model_validate(data))
        return logs

_repository_instance = None

def get_maintenance_request_repository() -> MaintenanceRequestRepository:
    """Dependency injection factory for MaintenanceRequestRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreMaintenanceRequestRepository()
    return _repository_instance
