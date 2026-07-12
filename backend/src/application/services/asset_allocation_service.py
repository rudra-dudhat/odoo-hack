from datetime import datetime
from typing import Any
from fastapi import Depends
from src.domain.entities.asset_allocation import AssetAllocation
from src.domain.entities.notification import Notification
from src.domain.enums import AllocationStatus, AssetStatus, EmployeeStatus, NotificationType, RelatedEntityType, AssetCondition, AuditLogAction
from src.domain.repositories.asset_allocation_repository import AssetAllocationRepository
from src.infrastructure.firestore.repositories.firestore_asset_allocation_repository import get_asset_allocation_repository
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.shared.errors import NotFoundError, ConflictError

class AssetAllocationService:
    def __init__(
        self,
        allocation_repo: AssetAllocationRepository,
        audit_log_service: AuditLogService
    ):
        self.allocation_repo = allocation_repo
        self.audit_log_service = audit_log_service

    def get_by_id(self, allocation_id: str) -> AssetAllocation | None:
        return self.allocation_repo.get_by_id(allocation_id)

    def list_allocations(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[AssetAllocation], str | None]:
        actual_sort_by = sort_by or "allocatedAt"
        return self.allocation_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def allocate_asset(
        self,
        asset_id: str,
        employee_id: str,
        expected_return_date: datetime | None,
        notes: str,
        actor_id: str
    ) -> AssetAllocation:
        def tx(transaction) -> AssetAllocation:
            # 1. Fetch and verify Asset
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if not asset_snap.exists or asset_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Asset {asset_id} not found or is deleted")
                
            asset_data = asset_snap.to_dict() or {}
            asset_status = asset_data.get("status")
            if asset_status != AssetStatus.AVAILABLE:
                raise ConflictError(f"Asset '{asset_id}' is not available (Current status: {asset_status})")

            # 2. Fetch and verify Employee
            emp_ref = db.collection("employees").document(employee_id)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Employee {employee_id} not found or is deleted")
                
            emp_data = emp_snap.to_dict() or {}
            emp_status = emp_data.get("status")
            if emp_status in (EmployeeStatus.SUSPENDED, EmployeeStatus.INACTIVE):
                raise ForbiddenError(f"Cannot allocate to employee: account is {emp_status}")

            # 3. Create allocation document
            alloc_ref = db.collection("assetAllocations").document()
            alloc_id = alloc_ref.id
            
            allocated_at = datetime.utcnow()
            
            # Snapshots
            asset_snapshot = {
                "assetTag": asset_data.get("assetTag", asset_id),
                "name": asset_data.get("name", "")
            }
            employee_snapshot = {
                "fullName": emp_data.get("fullName", ""),
                "employeeCode": emp_data.get("employeeCode", "")
            }
            
            alloc_dict = {
                "assetId": asset_id,
                "assetSnapshot": asset_snapshot,
                "employeeId": employee_id,
                "employeeSnapshot": employee_snapshot,
                "allocatedAt": allocated_at,
                "expectedReturnDate": expected_return_date,
                "returnedAt": None,
                "status": AllocationStatus.ACTIVE.value,
                "conditionAtAllocation": asset_data.get("condition", AssetCondition.GOOD.value),
                "conditionAtReturn": None,
                "notes": notes,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "createdBy": actor_id,
                "updatedBy": actor_id,
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None
            }
            
            transaction.set(alloc_ref, alloc_dict)

            # 4. Update asset
            asset_update = {
                "status": AssetStatus.ALLOCATED.value,
                "currentAllocationId": alloc_id,
                "currentHolderSnapshot": {
                    "employeeId": employee_id,
                    "fullName": emp_data.get("fullName", "")
                },
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(asset_ref, asset_update)

            # 5. Create notification for recipient
            notif_ref = db.collection("notifications").document()
            notif_dict = {
                "recipientId": employee_id,
                "type": NotificationType.ALLOCATION_ASSIGNED.value,
                "title": "New Asset Allocated",
                "body": f"Asset {asset_snapshot['assetTag']} ({asset_snapshot['name']}) has been allocated to you.",
                "relatedEntityType": RelatedEntityType.ALLOCATION.value,
                "relatedEntityId": alloc_id,
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

            # 6. Log audit logs
            # Allocation log
            alloc_dict["id"] = alloc_id
            alloc_dict["createdAt"] = allocated_at
            alloc_dict["updatedAt"] = allocated_at
            
            self.audit_log_service.log_action(
                entity_type="assetAllocations",
                entity_id=alloc_id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=alloc_dict
            )
            # Asset log
            self.audit_log_service.log_action(
                entity_type="assets",
                entity_id=asset_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": asset_status, "currentAllocationId": None},
                after_snapshot={"status": AssetStatus.ALLOCATED.value, "currentAllocationId": alloc_id}
            )

            # Parse and return
            return AssetAllocation.model_validate(alloc_dict)

        return run_in_transaction(tx)

    def return_asset(
        self,
        allocation_id: str,
        condition_at_return: AssetCondition,
        notes: str,
        actor_id: str
    ) -> AssetAllocation:
        def tx(transaction) -> AssetAllocation:
            # 1. Fetch and verify allocation
            alloc_ref = db.collection("assetAllocations").document(allocation_id)
            alloc_snap = transaction.get(alloc_ref)
            if not alloc_snap.exists or alloc_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Allocation {allocation_id} not found")
                
            alloc_data = alloc_snap.to_dict() or {}
            old_status = alloc_data.get("status")
            if old_status not in (AllocationStatus.ACTIVE, AllocationStatus.OVERDUE):
                raise ConflictError(f"Allocation is already in state '{old_status}'")
                
            asset_id = alloc_data.get("assetId")

            # 2. Update allocation
            returned_at = datetime.utcnow()
            alloc_updates = {
                "status": AllocationStatus.RETURNED.value,
                "returnedAt": returned_at,
                "conditionAtReturn": condition_at_return.value,
                "notes": notes,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(alloc_ref, alloc_updates)

            # 3. Update asset
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if asset_snap.exists:
                asset_updates = {
                    "status": AssetStatus.AVAILABLE.value,
                    "condition": condition_at_return.value,
                    "currentAllocationId": None,
                    "currentHolderSnapshot": None,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "updatedBy": actor_id
                }
                transaction.update(asset_ref, asset_updates)

            # 4. Log audit logs
            # Allocation log
            self.audit_log_service.log_action(
                entity_type="assetAllocations",
                entity_id=allocation_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status, "returnedAt": None},
                after_snapshot={"status": AllocationStatus.RETURNED.value, "returnedAt": returned_at}
            )
            # Asset log
            if asset_snap.exists:
                self.audit_log_service.log_action(
                    entity_type="assets",
                    entity_id=asset_id,
                    action=AuditLogAction.UPDATE,
                    performed_by=actor_id,
                    before_snapshot={"status": AssetStatus.ALLOCATED.value, "currentAllocationId": allocation_id},
                    after_snapshot={"status": AssetStatus.AVAILABLE.value, "currentAllocationId": None}
                )

            # Re-read updated allocation for return
            updated_snap = alloc_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = allocation_id
            return AssetAllocation.model_validate(updated_data)

        return run_in_transaction(tx)

    def report_lost_allocation(self, allocation_id: str, notes: str, actor_id: str) -> AssetAllocation:
        def tx(transaction) -> AssetAllocation:
            # 1. Fetch and verify allocation
            alloc_ref = db.collection("assetAllocations").document(allocation_id)
            alloc_snap = transaction.get(alloc_ref)
            if not alloc_snap.exists or alloc_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Allocation {allocation_id} not found")
                
            alloc_data = alloc_snap.to_dict() or {}
            old_status = alloc_data.get("status")
            if old_status not in (AllocationStatus.ACTIVE, AllocationStatus.OVERDUE):
                raise ConflictError(f"Allocation is already in state '{old_status}'")
                
            asset_id = alloc_data.get("assetId")

            # 2. Update allocation to lost
            returned_at = datetime.utcnow()
            alloc_updates = {
                "status": AllocationStatus.LOST.value,
                "returnedAt": returned_at,
                "notes": notes,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(alloc_ref, alloc_updates)

            # 3. Update asset status to lost
            asset_ref = db.collection("assets").document(asset_id)
            asset_snap = transaction.get(asset_ref)
            if asset_snap.exists:
                asset_updates = {
                    "status": AssetStatus.LOST.value,
                    "currentAllocationId": None,
                    "currentHolderSnapshot": None,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "updatedBy": actor_id
                }
                transaction.update(asset_ref, asset_updates)

            # 4. Log audit logs
            # Allocation log
            self.audit_log_service.log_action(
                entity_type="assetAllocations",
                entity_id=allocation_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status, "returnedAt": None},
                after_snapshot={"status": AllocationStatus.LOST.value, "returnedAt": returned_at}
            )
            # Asset log
            if asset_snap.exists:
                self.audit_log_service.log_action(
                    entity_type="assets",
                    entity_id=asset_id,
                    action=AuditLogAction.UPDATE,
                    performed_by=actor_id,
                    before_snapshot={"status": AssetStatus.ALLOCATED.value, "currentAllocationId": allocation_id},
                    after_snapshot={"status": AssetStatus.LOST.value, "currentAllocationId": None}
                )

            # Re-read
            updated_snap = alloc_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = allocation_id
            return AssetAllocation.model_validate(updated_data)

        return run_in_transaction(tx)

def get_asset_allocation_service(
    allocation_repo: AssetAllocationRepository = Depends(get_asset_allocation_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> AssetAllocationService:
    """Dependency injection factory for AssetAllocationService."""
    return AssetAllocationService(allocation_repo, audit_log_service)
