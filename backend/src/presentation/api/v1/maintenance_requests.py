from fastapi import APIRouter, HTTPException, Body
from datetime import datetime, timezone
from src.infrastructure.firestore.client import db

router = APIRouter()


@router.get("", tags=["Maintenance Requests"])
async def get_maintenance_requests():
    try:
        requests_ref = db.collection("maintenanceRequests").stream()
        items = []
        for doc in requests_ref:
            data = doc.to_dict()
            data["id"] = doc.id
            items.append(data)
        return {"data": items}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch maintenance requests") from exc


@router.post("", tags=["Maintenance Requests"])
async def create_maintenance_request(payload: dict = Body(...)):
    try:
        now = datetime.now(timezone.utc)
        request_doc = {
            "assetId": payload.get("assetId", "AST-001"),
            "assetName": payload.get("assetName", "Unknown Asset"),
            "title": payload.get("title", "Maintenance Request"),
            "description": payload.get("description", ""),
            "priority": payload.get("priority", "medium"),
            "status": payload.get("status", "pending"),
            "createdAt": now,
            "updatedAt": now,
        }
        ref = db.collection("maintenanceRequests").document()
        ref.set(request_doc)
        request_doc["id"] = ref.id
        return {"message": "Maintenance request created successfully", "data": request_doc}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create maintenance request") from exc
