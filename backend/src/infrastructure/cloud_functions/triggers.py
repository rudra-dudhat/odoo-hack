from typing import Any
from google.cloud import firestore
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.shared.logging import logger

def _update_counter(transaction, collection: str, doc_id: str, field: str, delta: int) -> None:
    """Helper to update a numeric counter field inside a transaction."""
    if not doc_id:
        return
    ref = db.collection(collection).document(doc_id)
    snap = transaction.get(ref)
    if snap.exists:
        current_val = snap.to_dict().get(field, 0)
        new_val = max(0, current_val + delta)
        transaction.update(ref, {
            field: new_val,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

def _update_dashboard_kpis(transaction, aggregate_id: str, status_field: str, delta_assets: int, status_deltas: dict[str, int]) -> None:
    """Helper to update dashboard aggregates kpis status maps inside a transaction."""
    ref = db.collection("dashboardAggregates").document(aggregate_id)
    snap = transaction.get(ref)
    if not snap.exists:
        return
        
    data = snap.to_dict() or {}
    total_assets = max(0, data.get("totalAssets", 0) + delta_assets)
    assets_by_status = data.get("assetsByStatus", {})
    
    # Apply status deltas
    for status, delta in status_deltas.items():
        assets_by_status[status] = max(0, assets_by_status.get(status, 0) + delta)
        
    transaction.update(ref, {
        "totalAssets": total_assets,
        "assetsByStatus": assets_by_status,
        "lastComputedAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

def handle_employee_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: employees/{employeeId}
    Maintains: departments/{departmentId}.employeeCount
    """
    before_active = before and not before.get("isDeleted") and before.get("status") == "active"
    after_active = after and not after.get("isDeleted") and after.get("status") == "active"
    
    before_dept = before.get("departmentId") if before else None
    after_dept = after.get("departmentId") if after else None
    
    if before_active == after_active and before_dept == after_dept:
        return
        
    def tx(transaction) -> None:
        # Subtract from old department count
        if before_active and before_dept:
            _update_counter(transaction, "departments", before_dept, "employeeCount", -1)
        # Add to new department count
        if after_active and after_dept:
            _update_counter(transaction, "departments", after_dept, "employeeCount", 1)
            
    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_employee_write trigger: {e}")


def handle_asset_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: assets/{assetId}
    Maintains: 
      - assetCategories/{categoryId}.assetCount
      - departments/{departmentId}.assetCount
      - dashboardAggregates/global_kpis (totalAssets & assetsByStatus)
      - dashboardAggregates/dept_{departmentId} (totalAssets & assetsByStatus)
    """
    before_active = before and not before.get("isDeleted")
    after_active = after and not after.get("isDeleted")
    
    before_cat = before.get("categoryId") if before else None
    after_cat = after.get("categoryId") if after else None
    
    before_dept = before.get("departmentId") if before else None
    after_dept = after.get("departmentId") if after else None
    
    before_status = before.get("status") if before else None
    after_status = after.get("status") if after else None
    
    if (before_active == after_active and 
        before_cat == after_cat and 
        before_dept == after_dept and 
        before_status == after_status):
        return
        
    def tx(transaction) -> None:
        # 1. Update Asset Category counters
        if before_active and before_cat:
            _update_counter(transaction, "assetCategories", before_cat, "assetCount", -1)
        if after_active and after_cat:
            _update_counter(transaction, "assetCategories", after_cat, "assetCount", 1)
            
        # 2. Update Department counters
        if before_active and before_dept:
            _update_counter(transaction, "departments", before_dept, "assetCount", -1)
        if after_active and after_dept:
            _update_counter(transaction, "departments", after_dept, "assetCount", 1)
            
        # 3. Update Dashboard Aggregates (global and dept scopes)
        # Calculate global status map modifications
        delta_assets = 0
        status_deltas: dict[str, int] = {}
        
        if before_active and before_status:
            delta_assets -= 1
            status_deltas[before_status] = status_deltas.get(before_status, 0) - 1
        if after_active and after_status:
            delta_assets += 1
            status_deltas[after_status] = status_deltas.get(after_status, 0) + 1
            
        # Write Global dashboard KPIs
        _update_dashboard_kpis(transaction, "global_kpis", "assetsByStatus", delta_assets, status_deltas)
        
        # Write Dept-specific dashboard KPIs
        # If transferred department, subtract from old and add to new
        if before_active and before_dept:
            dept_deltas = {before_status: -1} if before_status else {}
            _update_dashboard_kpis(transaction, f"dept_{before_dept}", "assetsByStatus", -1, dept_deltas)
        if after_active and after_dept:
            dept_deltas = {after_status: 1} if after_status else {}
            _update_dashboard_kpis(transaction, f"dept_{after_dept}", "assetsByStatus", 1, dept_deltas)

    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_asset_write trigger: {e}")


def handle_allocation_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: assetAllocations/{allocationId}
    Maintains: dashboardAggregates active & overdue allocations counts (global and dept scope)
    """
    before_active = before and not before.get("isDeleted") and before.get("status") in ("active", "overdue")
    after_active = after and not after.get("isDeleted") and after.get("status") in ("active", "overdue")
    
    before_overdue = before and before.get("status") == "overdue"
    after_overdue = after and after.get("status") == "overdue"
    
    # We resolve the department belonging to the allocated asset
    before_asset = before.get("assetId") if before else None
    after_asset = after.get("assetId") if after else None
    
    def tx(transaction) -> None:
        # Load asset department to scope department dashboard
        before_dept = None
        if before_asset:
            asn = transaction.get(db.collection("assets").document(before_asset))
            if asn.exists:
                before_dept = asn.to_dict().get("departmentId")
                
        after_dept = None
        if after_asset:
            asn = transaction.get(db.collection("assets").document(after_asset))
            if asn.exists:
                after_dept = asn.to_dict().get("departmentId")

        # Global aggregates doc update helper
        def apply_alloc_deltas(agg_id, active_d, overdue_d):
            ref = db.collection("dashboardAggregates").document(agg_id)
            snap = transaction.get(ref)
            if snap.exists:
                d = snap.to_dict() or {}
                transaction.update(ref, {
                    "totalActiveAllocations": max(0, d.get("totalActiveAllocations", 0) + active_d),
                    "totalOverdueAllocations": max(0, d.get("totalOverdueAllocations", 0) + overdue_d),
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })

        # Calculate deltas
        active_delta = 0
        overdue_delta = 0
        if before_active:
            active_delta -= 1
        if before_overdue:
            overdue_delta -= 1
        if after_active:
            active_delta += 1
        if after_overdue:
            overdue_delta += 1
            
        if active_delta == 0 and overdue_delta == 0 and before_dept == after_dept:
            return

        # Update global
        apply_alloc_deltas("global_kpis", active_delta, overdue_delta)
        
        # Update department
        if before_dept:
            apply_alloc_deltas(f"dept_{before_dept}", -1 if before_active else 0, -1 if before_overdue else 0)
        if after_dept:
            apply_alloc_deltas(f"dept_{after_dept}", 1 if after_active else 0, 1 if after_overdue else 0)

    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_allocation_write trigger: {e}")


def handle_booking_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: resourceBookings/{bookingId}
    Maintains: totalBookingsToday count on dashboards (global & dept scopes)
    """
    # Bookings today are confirmed bookings starting today
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    today_end = datetime(now.year, now.month, now.day, 23, 59, 59)
    
    def is_today_booking(data: dict | None) -> bool:
        if not data or data.get("isDeleted") or data.get("status") != "confirmed":
            return False
        st = data.get("startTime")
        # Handle string timestamps parsing if returned as string from snapshot dictionary
        if isinstance(st, str):
            st = datetime.fromisoformat(st.replace("Z", "+00:00")).replace(tzinfo=None)
        return st is not None and today_start <= st <= today_end

    before_today = is_today_booking(before)
    after_today = is_today_booking(after)
    
    if before_today == after_today:
        return
        
    delta = 1 if after_today else -1
    
    def tx(transaction) -> None:
        # Update global
        g_ref = db.collection("dashboardAggregates").document("global_kpis")
        g_snap = transaction.get(g_ref)
        if g_snap.exists:
            count = max(0, g_snap.to_dict().get("totalBookingsToday", 0) + delta)
            transaction.update(g_ref, {"totalBookingsToday": count})
            
        # Update department of the booked resource
        res_id = (after or before).get("resourceId")
        if res_id:
            res_snap = transaction.get(db.collection("sharedResources").document(res_id))
            if res_snap.exists:
                dept_id = res_snap.to_dict().get("location") # location corresponds to departmentId scope
                if dept_id:
                    d_ref = db.collection("dashboardAggregates").document(f"dept_{dept_id}")
                    d_snap = transaction.get(d_ref)
                    if d_snap.exists:
                        count = max(0, d_snap.to_dict().get("totalBookingsToday", 0) + delta)
                        transaction.update(d_ref, {"totalBookingsToday": count})

    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_booking_write trigger: {e}")


def handle_maintenance_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: maintenanceRequests/{requestId}
    Maintains: openMaintenanceRequests count and priority map (global and dept scope)
    """
    # Open request statuses: pending_approval, approved, in_progress
    open_statuses = ("pending_approval", "approved", "in_progress")
    
    before_open = before and not before.get("isDeleted") and before.get("status") in open_statuses
    after_open = after and not after.get("isDeleted") and after.get("status") in open_statuses
    
    before_pri = before.get("priority") if before else None
    after_pri = after.get("priority") if after else None
    
    before_asset = before.get("assetId") if before else None
    after_asset = after.get("assetId") if after else None
    
    if before_open == after_open and before_pri == after_pri and before_asset == after_asset:
        return
        
    def tx(transaction) -> None:
        # Load departments
        before_dept = None
        if before_asset:
            asn = transaction.get(db.collection("assets").document(before_asset))
            if asn.exists:
                before_dept = asn.to_dict().get("departmentId")
                
        after_dept = None
        if after_asset:
            asn = transaction.get(db.collection("assets").document(after_asset))
            if asn.exists:
                after_dept = asn.to_dict().get("departmentId")

        def apply_maint_deltas(agg_id, open_d, priority_d):
            ref = db.collection("dashboardAggregates").document(agg_id)
            snap = transaction.get(ref)
            if snap.exists:
                d = snap.to_dict() or {}
                open_count = max(0, d.get("openMaintenanceRequests", 0) + open_d)
                pri_map = d.get("maintenanceByPriority", {})
                for pri, del_val in priority_d.items():
                    pri_map[pri] = max(0, pri_map.get(pri, 0) + del_val)
                transaction.update(ref, {
                    "openMaintenanceRequests": open_count,
                    "maintenanceByPriority": pri_map,
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })

        open_delta = 0
        priority_deltas = {}
        
        if before_open and before_pri:
            open_delta -= 1
            priority_deltas[before_pri] = priority_deltas.get(before_pri, 0) - 1
        if after_open and after_pri:
            open_delta += 1
            priority_deltas[after_pri] = priority_deltas.get(after_pri, 0) + 1

        apply_maint_deltas("global_kpis", open_delta, priority_deltas)
        
        if before_dept:
            before_pri_deltas = {before_pri: -1} if before_pri else {}
            apply_maint_deltas(f"dept_{before_dept}", -1 if before_open else 0, before_pri_deltas)
        if after_dept:
            after_pri_deltas = {after_pri: 1} if after_pri else {}
            apply_maint_deltas(f"dept_{after_dept}", 1 if after_open else 0, after_pri_deltas)

    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_maintenance_write trigger: {e}")


def handle_notification_write(before: dict | None, after: dict | None) -> None:
    """
    Triggers on: notifications/{notificationId}
    Maintains: global_kpis.pendingNotificationsCount (unread notifications)
    """
    before_unread = before and not before.get("isDeleted") and not before.get("isRead")
    after_unread = after and not after.get("isDeleted") and not after.get("isRead")
    
    if before_unread == after_unread:
        return
        
    delta = 1 if after_unread else -1
    
    def tx(transaction) -> None:
        ref = db.collection("dashboardAggregates").document("global_kpis")
        snap = transaction.get(ref)
        if snap.exists:
            count = max(0, snap.to_dict().get("pendingNotificationsCount", 0) + delta)
            transaction.update(ref, {"pendingNotificationsCount": count})

    try:
        run_in_transaction(tx)
    except Exception as e:
        logger.error(f"Error executing handle_notification_write trigger: {e}")
