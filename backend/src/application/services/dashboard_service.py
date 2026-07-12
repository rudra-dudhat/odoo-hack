from datetime import datetime, time
from typing import Any
from fastapi import Depends
from src.domain.entities.dashboard_aggregate import DashboardAggregate
from src.domain.enums import DashboardScope, AssetStatus, MaintenancePriority, BookingStatus, MaintenanceStatus, AllocationStatus, AuditLogAction
from src.domain.repositories.dashboard_aggregate_repository import DashboardAggregateRepository
from src.infrastructure.firestore.repositories.firestore_dashboard_aggregate_repository import get_dashboard_aggregate_repository
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.shared.errors import NotFoundError, ValidationError

class DashboardService:
    def __init__(
        self,
        dashboard_repo: DashboardAggregateRepository,
        audit_log_service: AuditLogService
    ):
        self.dashboard_repo = dashboard_repo
        self.audit_log_service = audit_log_service

    def get_aggregate(self, aggregate_id: str) -> DashboardAggregate | None:
        """Fetch precomputed KPI aggregate. O(1) performance."""
        return self.dashboard_repo.get_by_id(aggregate_id)

    def recompute_aggregate(
        self,
        scope: DashboardScope,
        scope_ref_id: str | None,
        actor_id: str
    ) -> DashboardAggregate:
        """
        Triggers a full, offline-style scan of source collections to rebuild
        the KPI aggregate document. (Admin only)
        """
        # Determine aggregate ID
        if scope == DashboardScope.GLOBAL:
            aggregate_id = "global_kpis"
        elif scope == DashboardScope.DEPARTMENT:
            if not scope_ref_id:
                raise ValidationError("scope_ref_id (departmentId) is required for department scope")
            # Verify department exists
            dept_snap = db.collection("departments").document(scope_ref_id).get()
            if not dept_snap.exists:
                raise NotFoundError(f"Department {scope_ref_id} not found")
            aggregate_id = f"dept_{scope_ref_id}"
        elif scope == DashboardScope.DAILY:
            # daily aggregates represent historical snapshots and are not recomputed, 
            # but we allow constructing one for current date if requested.
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            aggregate_id = f"daily_{today_str}"
        else:
            raise ValidationError(f"Invalid scope: {scope}")

        # Initialize counters
        total_assets = 0
        assets_by_status = {status.value: 0 for status in AssetStatus}
        total_active_allocations = 0
        total_overdue_allocations = 0
        total_bookings_today = 0
        open_maintenance_requests = 0
        maintenance_by_priority = {priority.value: 0 for priority in MaintenancePriority}
        pending_notifications_count = 0
        audit_compliance_rate = 0.0

        # --- 1. SCAN ASSETS & ALLOCATIONS ---
        # Fetch assets
        assets_query = db.collection("assets").where("isDeleted", "==", False)
        if scope == DashboardScope.DEPARTMENT:
            assets_query = assets_query.where("departmentId", "==", scope_ref_id)
        assets_snaps = assets_query.get()
        
        asset_ids = []
        for snap in assets_snaps:
            total_assets += 1
            data = snap.to_dict() or {}
            status = data.get("status")
            if status in assets_by_status:
                assets_by_status[status] += 1
            asset_ids.append(snap.id)

        # Fetch allocations (only relevant for scoped assets)
        if asset_ids:
            # Firestore supports "IN" operator up to 30 items. If asset list is larger, 
            # we query all active/overdue allocations and filter in-memory for the department assets,
            # or query them globally.
            alloc_query = db.collection("assetAllocations")\
                            .where("status", "in", [AllocationStatus.ACTIVE.value, AllocationStatus.OVERDUE.value])\
                            .where("isDeleted", "==", False)
                            
            alloc_snaps = alloc_query.get()
            for snap in alloc_snaps:
                data = snap.to_dict() or {}
                ast_id = data.get("assetId")
                status = data.get("status")
                
                # Check if asset belongs to scope
                if scope == DashboardScope.GLOBAL or ast_id in asset_ids:
                    total_active_allocations += 1
                    if status == AllocationStatus.OVERDUE.value:
                        total_overdue_allocations += 1

        # --- 2. SCAN BOOKINGS (Today) ---
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)
        
        booking_query = db.collection("resourceBookings")\
                          .where("status", "==", BookingStatus.CONFIRMED.value)\
                          .where("isDeleted", "==", False)\
                          .where("startTime", ">=", today_start)\
                          .where("startTime", "<=", today_end)
                          
        booking_snaps = booking_query.get()
        # For department scope, filter bookings for resources owned by the department
        if scope == DashboardScope.DEPARTMENT:
            # Find resources in this department
            res_snaps = db.collection("sharedResources")\
                          .where("location", "==", scope_ref_id)\
                          .where("isDeleted", "==", False).get() # assuming department location matches ref
            res_ids = {snap.id for snap in res_snaps}
            
            for snap in booking_snaps:
                data = snap.to_dict() or {}
                if data.get("resourceId") in res_ids:
                    total_bookings_today += 1
        else:
            total_bookings_today = len(booking_snaps)

        # --- 3. SCAN MAINTENANCE ---
        maint_query = db.collection("maintenanceRequests")\
                        .where("isDeleted", "==", False)\
                        .where("status", "in", [
                            MaintenanceStatus.PENDING_APPROVAL.value,
                            MaintenanceStatus.APPROVED.value,
                            MaintenanceStatus.IN_PROGRESS.value
                        ])
        maint_snaps = maint_query.get()
        for snap in maint_snaps:
            data = snap.to_dict() or {}
            ast_id = data.get("assetId")
            priority = data.get("priority")
            
            # Check scope
            if scope == DashboardScope.GLOBAL or ast_id in asset_ids:
                open_maintenance_requests += 1
                if priority in maintenance_by_priority:
                    maintenance_by_priority[priority] += 1

        # --- 4. SCAN NOTIFICATIONS (Unread) ---
        # Scoped only for global/daily, department doesn't track unread notifications directly
        if scope in (DashboardScope.GLOBAL, DashboardScope.DAILY):
            notif_query = db.collection("notifications")\
                            .where("isRead", "==", False)\
                            .where("isDeleted", "==", False)
            pending_notifications_count = len(notif_query.get())

        # --- 5. RESOLVE COMPLIANCE RATE (From completed cycles) ---
        # Fetch compliance rate from latest completed cycle
        cycle_query = db.collection("auditCycles")\
                        .where("status", "==", "completed")\
                        .where("isDeleted", "==", False)\
                        .order_by("actualEnd", direction=firestore.Query.DESCENDING)\
                        .limit(1)
        cycle_snaps = cycle_query.get()
        if cycle_snaps:
            cdata = cycle_snaps[0].to_dict() or {}
            c_audited = cdata.get("assetsAudited", 0)
            c_disc = cdata.get("discrepanciesFound", 0)
            c_scope = cdata.get("totalAssetsInScope", 0)
            if c_scope > 0:
                audit_compliance_rate = ((c_audited - c_disc) / c_scope) * 100.0
                audit_compliance_rate = max(0.0, min(100.0, audit_compliance_rate))

        # --- 6. WRITE AGGREGATE ---
        def tx(transaction) -> DashboardAggregate:
            agg_ref = db.collection("dashboardAggregates").document(aggregate_id)
            
            # Preserve old compliance rate if no completed cycles exist
            nonlocal audit_compliance_rate
            if audit_compliance_rate == 0.0:
                old_snap = transaction.get(agg_ref)
                if old_snap.exists:
                    audit_compliance_rate = old_snap.to_dict().get("auditComplianceRate", 0.0)
                    
            agg_dict = {
                "scope": scope.value,
                "scopeRefId": scope_ref_id,
                "totalAssets": total_assets,
                "assetsByStatus": assets_by_status,
                "totalActiveAllocations": total_active_allocations,
                "totalOverdueAllocations": total_overdue_allocations,
                "totalBookingsToday": total_bookings_today,
                "openMaintenanceRequests": open_maintenance_requests,
                "maintenanceByPriority": maintenance_by_priority,
                "auditComplianceRate": audit_compliance_rate,
                "pendingNotificationsCount": pending_notifications_count,
                "lastComputedAt": firestore.SERVER_TIMESTAMP,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "createdBy": "system",
                "updatedBy": "system",
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None
            }
            transaction.set(agg_ref, agg_dict)
            
            # Read back
            agg_dict["id"] = aggregate_id
            agg_dict["lastComputedAt"] = datetime.utcnow() # local timestamp for parsing
            
            # Log audit
            self.audit_log_service.log_action(
                entity_type="dashboardAggregates",
                entity_id=aggregate_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                after_snapshot=agg_dict
            )
            
            return DashboardAggregate.model_validate(agg_dict)

        return run_in_transaction(tx)

def get_dashboard_service(
    dashboard_repo: DashboardAggregateRepository = Depends(get_dashboard_aggregate_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> DashboardService:
    """Dependency injection factory for DashboardService."""
    return DashboardService(dashboard_repo, audit_log_service)
