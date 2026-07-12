from datetime import datetime
from typing import Any
from fastapi import Depends
from src.domain.entities.maintenance_request import MaintenanceRequest, MaintenanceApproval, MaintenanceLog
from src.domain.enums import MaintenancePriority, MaintenanceStatus, ApprovalDecision, MaintenanceLogAction, AssetStatus, NotificationType, RelatedEntityType, AuditLogAction
from src.domain.repositories.maintenance_request_repository import MaintenanceRequestRepository
from src.infrastructure.firestore.repositories.firestore_maintenance_request_repository import get_maintenance_request_repository
from src.domain.value_objects.snapshots import AssetSnapshot, EmployeeRequestedBySnapshot, EmployeeTechnicianSnapshot, EmployeeApproverSnapshot, EmployeePerformedBySnapshot
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.firestore.counters import get_next_maintenance_request_number
from src.shared.errors import NotFoundError, ConflictError, ValidationError

class MaintenanceService:
    def __init__(
        self,
        maint_repo: MaintenanceRequestRepository,
        audit_log_service: AuditLogService
    ):
        self.maint_repo = maint_repo
        self.audit_log_service = audit_log_service

    def get_request_by_id(self, request_id: str) -> MaintenanceRequest | None:
        return self.maint_repo.get_by_id(request_id)

    def list_requests(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[MaintenanceRequest], str | None]:
        actual_sort_by = sort_by or "createdAt"
        return self.maint_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def list_approvals(self, request_id: str) -> list[MaintenanceApproval]:
        return self.maint_repo.list_approvals(request_id)

    def list_logs(self, request_id: str) -> list[MaintenanceLog]:
        return self.maint_repo.list_logs(request_id)

    def create_request(
        self,
        asset_id: str,
        requested_by: str,
        issue_description: str,
        priority: MaintenancePriority,
        actor_id: str
    ) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            # 1. Fetch & Verify Asset
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found or is deleted")
            asset_data = asset_snap.to_dict() or {}
            
            # 2. Fetch & Verify Requester
            emp_ref = db.collection("employees").document(requested_by)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Requester Employee {requested_by} not found or is deleted")
            emp_data = emp_snap.to_dict() or {}

            # 3. Generate Request Number (MR-YYYY-#####)
            req_number = get_next_maintenance_request_number(transaction)

            # Snapshots
            asset_snapshot = AssetSnapshot(
                asset_tag=asset_data.get("assetTag", asset_id),
                name=asset_data.get("name", "")
            )
            requested_by_snapshot = EmployeeRequestedBySnapshot(
                full_name=emp_data.get("fullName", "")
            )

            # 4. Create request
            req = MaintenanceRequest(
                id=req_number,
                request_number=req_number,
                asset_id=asset_id,
                asset_snapshot=asset_snapshot,
                requested_by=requested_by,
                requested_by_snapshot=requested_by_snapshot,
                issue_description=issue_description,
                priority=priority,
                status=MaintenanceStatus.PENDING_APPROVAL,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_req = self.maint_repo.create(req)

            # 5. Append Log subcollection entry
            performer_snap = EmployeePerformedBySnapshot(full_name=emp_data.get("fullName", ""))
            log_entry = MaintenanceLog(
                action=MaintenanceLogAction.CREATED,
                performed_by=requested_by,
                performed_by_snapshot=performer_snap,
                details="Maintenance request submitted.",
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(req_number, log_entry)

            # 6. Global audit log
            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=req_number,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_req.model_dump(by_alias=True, exclude_none=True)
            )
            return created_req

        return run_in_transaction(tx)

    def approve_request(self, request_id: str, comments: str, actor_id: str) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            # 1. Fetch request
            req_ref = db.collection("maintenanceRequests").document(request_id)
            req_snap = transaction.get(req_ref)
            if not req_snap.exists or req_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Maintenance request {request_id} not found")
                
            req_data = req_snap.to_dict() or {}
            old_status = req_data.get("status")
            if old_status != MaintenanceStatus.PENDING_APPROVAL.value:
                raise ConflictError(f"Cannot approve maintenance request in status '{old_status}'")
                
            asset_id = req_data.get("assetId")
            requester_id = req_data.get("requestedBy")

            # 2. Fetch actor (approver) info
            actor_ref = db.collection("employees").document(actor_id)
            actor_snap = transaction.get(actor_ref)
            actor_name = actor_snap.to_dict().get("fullName", "") if actor_snap.exists else "System"

            # 3. Create approval subcollection entry
            approver_snapshot = EmployeeApproverSnapshot(full_name=actor_name)
            approval = MaintenanceApproval(
                approver_id=actor_id,
                approver_snapshot=approver_snapshot,
                decision=ApprovalDecision.APPROVED,
                comments=comments,
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_approval(request_id, approval)

            # 4. Update request status to APPROVED
            updates = {
                "status": MaintenanceStatus.APPROVED.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(req_ref, updates)

            # 5. Update asset status to IN_MAINTENANCE
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if asset_snap.exists:
                transaction.update(asset_ref, {
                    "status": AssetStatus.IN_MAINTENANCE.value,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "updatedBy": actor_id
                })

            # 6. Append Log entry
            performer_snap = EmployeePerformedBySnapshot(full_name=actor_name)
            log = MaintenanceLog(
                action=MaintenanceLogAction.APPROVED,
                performed_by=actor_id,
                performed_by_snapshot=performer_snap,
                details=f"Approved. Comments: {comments}",
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(request_id, log)

            # 7. Create notification for requester
            notif_ref = db.collection("notifications").document()
            notif_dict = {
                "recipientId": requester_id,
                "type": NotificationType.MAINTENANCE_STATUS_CHANGE.value,
                "title": "Maintenance Request Approved",
                "body": f"Your maintenance request {request_id} has been approved and the asset is scheduled for service.",
                "relatedEntityType": RelatedEntityType.MAINTENANCE_REQUEST.value,
                "relatedEntityId": request_id,
                "isRead": False,
                "readAt": None,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "createdBy": "system",
                "updatedBy": "system",
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None
            }
            transaction.set(notif_ref, notif_dict)

            # 8. Audit trail
            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=request_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": MaintenanceStatus.APPROVED.value}
            )
            if asset_snap.exists:
                self.audit_log_service.log_action(
                    entity_type="assets",
                    entity_id=asset_id,
                    action=AuditLogAction.UPDATE,
                    performed_by=actor_id,
                    before_snapshot={"status": asset_snap.to_dict().get("status")},
                    after_snapshot={"status": AssetStatus.IN_MAINTENANCE.value}
                )

            # Re-read
            updated_snap = req_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = request_id
            return MaintenanceRequest.model_validate(updated_data)

        return run_in_transaction(tx)

    def reject_request(self, request_id: str, comments: str, actor_id: str) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            req_ref = db.collection("maintenanceRequests").document(request_id)
            req_snap = transaction.get(req_ref)
            if not req_snap.exists or req_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Maintenance request {request_id} not found")
                
            req_data = req_snap.to_dict() or {}
            old_status = req_data.get("status")
            if old_status != MaintenanceStatus.PENDING_APPROVAL.value:
                raise ConflictError(f"Cannot reject maintenance request in status '{old_status}'")
                
            requester_id = req_data.get("requestedBy")

            # Fetch actor (approver) info
            actor_ref = db.collection("employees").document(actor_id)
            actor_snap = transaction.get(actor_ref)
            actor_name = actor_snap.to_dict().get("fullName", "") if actor_snap.exists else "System"

            # Create rejection entry in approvals subcollection
            approver_snapshot = EmployeeApproverSnapshot(full_name=actor_name)
            approval = MaintenanceApproval(
                approver_id=actor_id,
                approver_snapshot=approver_snapshot,
                decision=ApprovalDecision.REJECTED,
                comments=comments,
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_approval(request_id, approval)

            # Update request status to REJECTED
            updates = {
                "status": MaintenanceStatus.REJECTED.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(req_ref, updates)

            # Append Log entry
            performer_snap = EmployeePerformedBySnapshot(full_name=actor_name)
            log = MaintenanceLog(
                action=MaintenanceLogAction.REJECTED,
                performed_by=actor_id,
                performed_by_snapshot=performer_snap,
                details=f"Rejected. Comments: {comments}",
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(request_id, log)

            # Create notification for requester
            notif_ref = db.collection("notifications").document()
            notif_dict = {
                "recipientId": requester_id,
                "type": NotificationType.MAINTENANCE_STATUS_CHANGE.value,
                "title": "Maintenance Request Rejected",
                "body": f"Your maintenance request {request_id} has been rejected. Comments: {comments}",
                "relatedEntityType": RelatedEntityType.MAINTENANCE_REQUEST.value,
                "relatedEntityId": request_id,
                "isRead": False,
                "readAt": None,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "createdBy": "system",
                "updatedBy": "system",
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None
            }
            transaction.set(notif_ref, notif_dict)

            # Audit
            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=request_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": MaintenanceStatus.REJECTED.value}
            )

            updated_snap = req_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = request_id
            return MaintenanceRequest.model_validate(updated_data)

        return run_in_transaction(tx)

    def assign_technician(self, request_id: str, technician_id: str, actor_id: str) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            req_ref = db.collection("maintenanceRequests").document(request_id)
            req_snap = transaction.get(req_ref)
            if not req_snap.exists or req_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Maintenance request {request_id} not found")
                
            req_data = req_snap.to_dict() or {}
            old_status = req_data.get("status")
            if old_status in (MaintenanceStatus.REJECTED.value, MaintenanceStatus.CANCELLED.value, MaintenanceStatus.COMPLETED.value):
                raise ConflictError(f"Cannot assign technician in request status '{old_status}'")

            # Fetch technician info
            tech_ref = db.collection("employees").document(technician_id)
            tech_snap = transaction.get(tech_ref)
            if not tech_snap.exists or tech_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Technician Employee {technician_id} not found or is deleted")
            tech_data = tech_snap.to_dict() or {}
            tech_name = tech_data.get("fullName", "")

            # Update assigned tech
            updates = {
                "assignedTechnicianId": technician_id,
                "assignedTechnicianSnapshot": {
                    "fullName": tech_name
                },
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(req_ref, updates)

            # Append Log entry
            actor_snap = db.collection("employees").document(actor_id).get(transaction=transaction)
            actor_name = actor_snap.to_dict().get("fullName", "System") if actor_snap.exists else "System"
            performer_snap = EmployeePerformedBySnapshot(full_name=actor_name)
            
            log = MaintenanceLog(
                action=MaintenanceLogAction.ASSIGNED,
                performed_by=actor_id,
                performed_by_snapshot=performer_snap,
                details=f"Assigned technician: {tech_name}.",
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(request_id, log)

            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=request_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"assignedTechnicianId": req_data.get("assignedTechnicianId")},
                after_snapshot={"assignedTechnicianId": technician_id}
            )

            updated_snap = req_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = request_id
            return MaintenanceRequest.model_validate(updated_data)

        return run_in_transaction(tx)

    def progress_status(self, request_id: str, new_status: MaintenanceStatus, actual_cost: int | None, actor_id: str) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            req_ref = db.collection("maintenanceRequests").document(request_id)
            req_snap = transaction.get(req_ref)
            if not req_snap.exists or req_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Maintenance request {request_id} not found")
                
            req_data = req_snap.to_dict() or {}
            old_status = req_data.get("status")
            asset_id = req_data.get("assetId")
            requester_id = req_data.get("requestedBy")

            # Validate transitions
            if old_status == MaintenanceStatus.APPROVED.value and new_status == MaintenanceStatus.IN_PROGRESS:
                pass
            elif old_status == MaintenanceStatus.IN_PROGRESS.value and new_status == MaintenanceStatus.COMPLETED:
                if actual_cost is None:
                    raise ValidationError("actual_cost is required to complete a maintenance request")
            else:
                raise ConflictError(f"Invalid maintenance status transition from '{old_status}' to '{new_status.value}'")

            updates: dict[str, Any] = {
                "status": new_status.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }

            completed_at = None
            if new_status == MaintenanceStatus.COMPLETED:
                completed_at = datetime.utcnow()
                updates["completedAt"] = completed_at
                updates["actualCost"] = actual_cost
                
                # Release asset status to AVAILABLE
                asset_ref = db.collection("assets").document(asset_id)
                asset_snap = transaction.get(asset_ref)
                if asset_snap.exists:
                    transaction.update(asset_ref, {
                        "status": AssetStatus.AVAILABLE.value,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                        "updatedBy": actor_id
                    })

            # Perform write
            transaction.update(req_ref, updates)

            # Append Log entry
            actor_snap = db.collection("employees").document(actor_id).get(transaction=transaction)
            actor_name = actor_snap.to_dict().get("fullName", "System") if actor_snap.exists else "System"
            performer_snap = EmployeePerformedBySnapshot(full_name=actor_name)
            
            log = MaintenanceLog(
                action=MaintenanceLogAction.STATUS_CHANGED,
                performed_by=actor_id,
                performed_by_snapshot=performer_snap,
                details=f"Status changed from '{old_status}' to '{new_status.value}'.",
                previous_status=old_status,
                new_status=new_status.value,
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(request_id, log)

            # Notification if status changed to Completed
            if new_status == MaintenanceStatus.COMPLETED:
                notif_ref = db.collection("notifications").document()
                notif_dict = {
                    "recipientId": requester_id,
                    "type": NotificationType.MAINTENANCE_STATUS_CHANGE.value,
                    "title": "Maintenance Request Completed",
                    "body": f"Your maintenance request {request_id} has been completed.",
                    "relatedEntityType": RelatedEntityType.MAINTENANCE_REQUEST.value,
                    "relatedEntityId": request_id,
                    "isRead": False,
                    "readAt": None,
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "createdBy": "system",
                    "updatedBy": "system",
                    "isDeleted": False,
                    "deletedAt": None,
                    "deletedBy": None
                }
                transaction.set(notif_ref, notif_dict)

            # Audit
            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=request_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": new_status.value}
            )
            if new_status == MaintenanceStatus.COMPLETED:
                self.audit_log_service.log_action(
                    entity_type="assets",
                    entity_id=asset_id,
                    action=AuditLogAction.UPDATE,
                    performed_by=actor_id,
                    before_snapshot={"status": AssetStatus.IN_MAINTENANCE.value},
                    after_snapshot={"status": AssetStatus.AVAILABLE.value}
                )

            updated_snap = req_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = request_id
            return MaintenanceRequest.model_validate(updated_data)

        return run_in_transaction(tx)

    def cancel_request(self, request_id: str, actor_id: str) -> MaintenanceRequest:
        def tx(transaction) -> MaintenanceRequest:
            req_ref = db.collection("maintenanceRequests").document(request_id)
            req_snap = transaction.get(req_ref)
            if not req_snap.exists or req_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Maintenance request {request_id} not found")
                
            req_data = req_snap.to_dict() or {}
            old_status = req_data.get("status")
            
            # Capped strictly to pending_approval or approved
            if old_status not in (MaintenanceStatus.PENDING_APPROVAL.value, MaintenanceStatus.APPROVED.value):
                raise ConflictError(f"Cannot cancel maintenance request in status '{old_status}'")
                
            asset_id = req_data.get("assetId")

            updates = {
                "status": MaintenanceStatus.CANCELLED.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(req_ref, updates)

            # If it was already approved, release the asset status back to AVAILABLE
            if old_status == MaintenanceStatus.APPROVED.value:
                asset_ref = db.collection("assets").document(asset_id)
                asset_snap = transaction.get(asset_ref)
                if asset_snap.exists:
                    transaction.update(asset_ref, {
                        "status": AssetStatus.AVAILABLE.value,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                        "updatedBy": actor_id
                    })

            # Append Log entry
            actor_snap = db.collection("employees").document(actor_id).get(transaction=transaction)
            actor_name = actor_snap.to_dict().get("fullName", "System") if actor_snap.exists else "System"
            performer_snap = EmployeePerformedBySnapshot(full_name=actor_name)
            
            log = MaintenanceLog(
                action=MaintenanceLogAction.CANCELLED,
                performed_by=actor_id,
                performed_by_snapshot=performer_snap,
                details="Request cancelled.",
                created_by=actor_id,
                updated_by=actor_id
            )
            self.maint_repo.create_log(request_id, log)

            self.audit_log_service.log_action(
                entity_type="maintenanceRequests",
                entity_id=request_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": MaintenanceStatus.CANCELLED.value}
            )

            updated_snap = req_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = request_id
            return MaintenanceRequest.model_validate(updated_data)

        return run_in_transaction(tx)

def get_maintenance_service(
    maint_repo: MaintenanceRequestRepository = Depends(get_maintenance_request_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> MaintenanceService:
    """Dependency injection factory for MaintenanceService."""
    return MaintenanceService(maint_repo, audit_log_service)
