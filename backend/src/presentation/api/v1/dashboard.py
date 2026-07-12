from fastapi import APIRouter, HTTPException
from src.infrastructure.firestore.client import db

router = APIRouter()


@router.get("", tags=["Dashboard"])
async def get_dashboard_summary():
    try:
        assets_ref = db.collection("assets")
        allocations_ref = db.collection("assetAllocations")
        bookings_ref = db.collection("resourceBookings")
        maintenance_ref = db.collection("maintenanceRequests")

        total_assets = sum(1 for doc in assets_ref.stream() if not doc.to_dict().get("isDeleted", False))
        active_allocations = sum(1 for doc in allocations_ref.stream() if doc.to_dict().get("status") == "active")
        overdue_allocations = sum(1 for doc in allocations_ref.stream() if doc.to_dict().get("status") == "overdue")
        bookings_today = sum(1 for doc in bookings_ref.stream() if doc.to_dict().get("status") == "confirmed")
        open_maintenance_requests = sum(1 for doc in maintenance_ref.stream() if doc.to_dict().get("status") in {"pending", "approved", "in_progress"})

        return {
            "totalAssets": total_assets,
            "activeAllocations": active_allocations,
            "overdueAllocations": overdue_allocations,
            "bookingsToday": bookings_today,
            "openMaintenanceRequests": open_maintenance_requests,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to load dashboard summary") from exc
