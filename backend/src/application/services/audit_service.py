from datetime import datetime
from typing import Any
from fastapi import Depends
from src.domain.entities.audit_cycle import AuditCycle, AuditReport
from src.domain.entities.maintenance_request import MaintenanceRequest, MaintenanceLog
from src.domain.enums import AuditCycleStatus, AssetCondition, AssetStatus, NotificationType, RelatedEntityType, MaintenancePriority, MaintenanceStatus, MaintenanceLogAction, AuditLogAction
from src.domain.repositories.audit_cycle_repository import AuditCycleRepository
from src.infrastructure.firestore.repositories.firestore_audit_cycle_repository import get_audit_cycle_repository
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.firestore.counters import get_next_maintenance_request_number
from src.shared.errors import NotFoundError, ConflictError, ValidationError

class AuditService:
    def __init__(
        self,
        audit_repo: AuditCycleRepository,
        audit_log_service: AuditLogService
    ):
        self.audit_repo = audit_repo
        self.audit_log_service = audit_log_service

    def get_cycle_by_id(self, cycle_id: str) -> AuditCycle | None:
        return self.audit_repo.get_by_id(cycle_id)

    def list_cycles(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[AuditCycle], str | None]:
        actual_sort_by = sort_by or "scheduledStart"
        return self.audit_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def list_reports(self, cycle_id: str) -> list[AuditReport]:
        return self.audit_repo.list_reports(cycle_id)

    def create_cycle(
        self,
        cycle_code: str, # E.g., AC-2026-Q3
        name: str,
        department_ids: list[str],
        category_ids: list[str],
        scheduled_start: datetime,
        scheduled_end: datetime,
        assigned_auditor_ids: list[str],
        actor_id: str
    ) -> AuditCycle:
        if not department_ids:
            raise ValidationError("At least one department ID must be selected to scope the audit")
            
        def tx(transaction) -> AuditCycle:
            # 1. Check uniqueness of cycle_code
            cycle_ref = db.collection("auditCycles").document(cycle_code)
            if transaction.get(cycle_ref).exists:
                raise ConflictError(f"Audit cycle with code '{cycle_code}' already exists")

            # 2. Verify departments
            for dept_id in department_ids:
                dept_ref = db.collection("departments").document(dept_id)
                if not transaction.get(dept_ref).exists:
                    raise NotFoundError(f"Department {dept_id} not found")
                    
            # 3. Verify auditors
            for aud_id in assigned_auditor_ids:
                aud_ref = db.collection("employees").document(aud_id)
                if not transaction.get(aud_ref).exists:
                    raise NotFoundError(f"Auditor employee {aud_id} not found")

            # 4. Compute assets in scope
            # Firestore requires "IN" operator constraints (limit of 30, which fits standard org dept scopes)
            assets_query = db.collection("assets").where("isDeleted", "==", False)\
                                                  .where("departmentId", "in", department_ids)
            assets_snaps = assets_query.get(transaction=transaction)
            
            total_scope = 0
            for snap in assets_snaps:
                adata = snap.to_dict() or {}
                # Filter categories in memory if category scoped
                if not category_ids or adata.get("categoryId") in category_ids:
                    total_scope += 1

            # 5. Create Cycle
            cycle = AuditCycle(
                id=cycle_code,
                cycle_code=cycle_code,
                name=name,
                department_ids=department_ids,
                category_ids=category_ids,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                status=AuditCycleStatus.PLANNED,
                assigned_auditor_ids=assigned_auditor_ids,
                total_assets_in_scope=total_scope,
                assets_audited=0,
                discrepancies_found=0,
                created_by=actor_id,
                updated_by=actor_id
            )
            
            created_cycle = self.audit_repo.create(cycle)

            # 6. Notify auditors
            for auditor_id in assigned_auditor_ids:
                notif_ref = db.collection("notifications").document()
                notif_dict = {
                    "recipientId": auditor_id,
                    "type": NotificationType.AUDIT_ASSIGNED.value,
                    "title": "New Audit Cycle Assigned",
                    "body": f"You have been assigned as an auditor for '{name}' ({cycle_code}).",
                    "relatedEntityType": RelatedEntityType.AUDIT_CYCLE.value,
                    "relatedEntityId": cycle_code,
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

            # 7. Audit log
            self.audit_log_service.log_action(
                entity_type="auditCycles",
                entity_id=cycle_code,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_cycle.model_dump(by_alias=True, exclude_none=True)
            )
            return created_cycle

        return run_in_transaction(tx)

    def start_cycle(self, cycle_id: str, actor_id: str) -> AuditCycle:
        def tx(transaction) -> AuditCycle:
            cycle_ref = db.collection("auditCycles").document(cycle_id)
            cycle_snap = transaction.get(cycle_ref)
            if not cycle_snap.exists or cycle_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Audit cycle {cycle_id} not found")
                
            old_status = cycle_snap.to_dict().get("status")
            if old_status != AuditCycleStatus.PLANNED.value:
                raise ConflictError(f"Cannot start audit cycle in status '{old_status}'")
                
            updates = {
                "status": AuditCycleStatus.IN_PROGRESS.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(cycle_ref, updates)

            self.audit_log_service.log_action(
                entity_type="auditCycles",
                entity_id=cycle_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": AuditCycleStatus.IN_PROGRESS.value}
            )

            updated_snap = cycle_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = cycle_id
            return AuditCycle.model_validate(updated_data)

        return run_in_transaction(tx)

    def submit_report(
        self,
        cycle_id: str,
        asset_id: str,
        audited_by: str,
        actual_location: str,
        actual_condition: AssetCondition,
        found: bool,
        discrepancy_notes: str,
        photo_urls: list[str],
        actor_id: str
    ) -> AuditReport:
        def tx(transaction) -> AuditReport:
            # 1. Fetch & Verify Cycle
            cycle_ref = db.collection("auditCycles").document(cycle_id)
            cycle_snap = transaction.get(cycle_ref)
            if not cycle_snap.exists or cycle_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Audit cycle {cycle_id} not found")
            cycle_data = cycle_snap.to_dict() or {}
            if cycle_data.get("status") != AuditCycleStatus.IN_PROGRESS.value:
                raise ConflictError(f"Cannot submit audit report: cycle status is '{cycle_data.get('status')}'")

            # 2. Fetch & Verify Asset
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found or is deleted")
            asset_data = asset_snap.to_dict() or {}
            expected_location = asset_data.get("location", "")
            expected_condition = asset_data.get("condition", AssetCondition.GOOD.value)

            # 3. Check if asset already audited in this cycle
            existing_report = self.audit_repo.find_report_by_asset(cycle_id, asset_id)
            if existing_report:
                raise ConflictError(f"Asset '{asset_id}' has already been audited in cycle '{cycle_id}'")

            # 4. Fetch Auditor info
            aud_ref = db.collection("employees").document(audited_by)
            aud_snap = transaction.get(aud_ref)
            auditor_name = aud_snap.to_dict().get("fullName", "Auditor") if aud_snap.exists else "Auditor"

            # 5. Create Report subcollection document
            report = AuditReport(
                asset_id=asset_id,
                asset_snapshot={
                    "assetTag": asset_data.get("assetTag", asset_id),
                    "name": asset_data.get("name", "")
                },
                audited_by=audited_by,
                audited_by_snapshot={"fullName": auditor_name},
                expected_location=expected_location,
                actual_location=actual_location,
                expected_condition=expected_condition,
                actual_condition=actual_condition,
                found=found,
                discrepancy_notes=discrepancy_notes,
                photo_urls=photo_urls,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_report = self.audit_repo.create_report(cycle_id, report)

            # 6. Check for discrepancies
            is_discrepancy = (not found) or (expected_condition != actual_condition.value)
            
            discrepancy_count_increment = 0
            if is_discrepancy:
                discrepancy_count_increment = 1
                
                # Fetch department head to notify
                dept_id = asset_data.get("departmentId")
                recipient_ids = []
                if dept_id:
                    dept_snap = transaction.get(db.collection("departments").document(dept_id))
                    if dept_snap.exists:
                        head_id = dept_snap.to_dict().get("headEmployeeId")
                        if head_id:
                            recipient_ids.append(head_id)
                
                # If no head, fallback or send to admins (recipientIds query can load admin users claims)
                # For this baseline, notify the department head
                for recipient in recipient_ids:
                    notif_ref = db.collection("notifications").document()
                    notif_dict = {
                        "recipientId": recipient,
                        "type": NotificationType.AUDIT_DISCREPANCY.value,
                        "title": "Audit Discrepancy Flagged",
                        "body": f"A discrepancy has been reported for asset {asset_id} in audit {cycle_id}.",
                        "relatedEntityType": RelatedEntityType.AUDIT_CYCLE.value,
                        "relatedEntityId": cycle_id,
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

                # Auto-trigger maintenance request creation if discrepancy involves damage
                if actual_condition in (AssetCondition.DAMAGED, AssetCondition.POOR):
                    maint_number = get_next_maintenance_request_number(transaction)
                    maint_ref = db.collection("maintenanceRequests").document(maint_number)
                    
                    maint_dict = {
                        "requestNumber": maint_number,
                        "assetId": asset_id,
                        "assetSnapshot": {
                            "assetTag": asset_data.get("assetTag", asset_id),
                            "name": asset_data.get("name", "")
                        },
                        "requestedBy": audited_by,
                        "requestedBySnapshot": {
                            "fullName": auditor_name
                        },
                        "issueDescription": f"[AUTO-GENERATED BY AUDIT {cycle_id}] Discrepancy report: asset condition is {actual_condition.value}. Auditor notes: {discrepancy_notes}",
                        "priority": MaintenancePriority.HIGH.value,
                        "status": MaintenanceStatus.PENDING_APPROVAL.value,
                        "assignedTechnicianId": None,
                        "assignedTechnicianSnapshot": None,
                        "estimatedCost": None,
                        "actualCost": None,
                        "attachmentUrls": photo_urls,
                        "completedAt": None,
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                        "createdBy": actor_id,
                        "updatedBy": actor_id,
                        "isDeleted": False,
                        "deletedAt": None,
                        "deletedBy": None
                    }
                    transaction.set(maint_ref, maint_dict)

                    # Initial maintenance log
                    log_ref = maint_ref.collection("logs").document()
                    log_dict = {
                        "action": MaintenanceLogAction.CREATED.value,
                        "performedBy": audited_by,
                        "performedBySnapshot": {"fullName": auditor_name},
                        "details": "Auto-created by audit discrepancy report.",
                        "createdAt": firestore.SERVER_TIMESTAMP,
                        "updatedAt": firestore.SERVER_TIMESTAMP,
                        "createdBy": actor_id,
                        "updatedBy": actor_id,
                        "isDeleted": False
                    }
                    transaction.set(log_ref, log_dict)

            # 7. Increment cycle counters
            cycle_updates = {
                "assetsAudited": cycle_data.get("assetsAudited", 0) + 1,
                "discrepanciesFound": cycle_data.get("discrepanciesFound", 0) + discrepancy_count_increment,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(cycle_ref, cycle_updates)

            # 8. Update Asset location & condition (or status to lost if found=false)
            asset_updates = {
                "location": actual_location,
                "condition": actual_condition.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            if not found:
                asset_updates["status"] = AssetStatus.LOST.value
                
            transaction.update(asset_ref, asset_updates)

            # 9. Audit trail
            # Report log
            rep_dict = created_report.model_dump(by_alias=True, exclude_none=True)
            rep_dict["id"] = created_report.id
            self.audit_log_service.log_action(
                entity_type="auditReports",
                entity_id=created_report.id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=rep_dict
            )
            # Asset log
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"location": expected_location, "condition": expected_condition},
                after_snapshot={"location": actual_location, "condition": actual_condition.value}
            )

            return created_report

        return run_in_transaction(tx)

    def close_cycle(self, cycle_id: str, actor_id: str) -> AuditCycle:
        def tx(transaction) -> AuditCycle:
            cycle_ref = db.collection("auditCycles").document(cycle_id)
            cycle_snap = transaction.get(cycle_ref)
            if not cycle_snap.exists or cycle_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Audit cycle {cycle_id} not found")
                
            cycle_data = cycle_snap.to_dict() or {}
            old_status = cycle_data.get("status")
            if old_status != AuditCycleStatus.IN_PROGRESS.value:
                raise ConflictError(f"Cannot close audit cycle in status '{old_status}'")

            assets_audited = cycle_data.get("assetsAudited", 0)
            discrepancies_found = cycle_data.get("discrepanciesFound", 0)
            total_scope = cycle_data.get("totalAssetsInScope", 0)
            
            # Compliance rate math
            compliance_rate = 100.0
            if total_scope > 0:
                compliance_rate = ((assets_audited - discrepancies_found) / total_scope) * 100.0
                compliance_rate = max(0.0, min(100.0, compliance_rate)) # Bound rate

            updates = {
                "status": AuditCycleStatus.COMPLETED.value,
                "actualEnd": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(cycle_ref, updates)

            # Update dashboard aggregates global kpi compliance rate
            global_kpi_ref = db.collection("dashboardAggregates").document("global_kpis")
            if transaction.get(global_kpi_ref).exists:
                transaction.update(global_kpi_ref, {
                    "auditComplianceRate": compliance_rate,
                    "lastComputedAt": firestore.SERVER_TIMESTAMP
                })

            # Audit
            self.audit_log_service.log_action(
                entity_type="auditCycles",
                entity_id=cycle_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": AuditCycleStatus.COMPLETED.value, "complianceRate": compliance_rate}
            )

            updated_snap = cycle_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = cycle_id
            return AuditCycle.model_validate(updated_data)

        return run_in_transaction(tx)

def get_audit_service(
    audit_repo: AuditCycleRepository = Depends(get_audit_cycle_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> AuditService:
    """Dependency injection factory for AuditService."""
    return AuditService(audit_repo, audit_log_service)
