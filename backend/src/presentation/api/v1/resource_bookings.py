from fastapi import APIRouter, HTTPException, Body
from datetime import datetime, timezone
from src.infrastructure.firestore.client import db

router = APIRouter()


@router.get("", tags=["Resource Bookings"])
async def get_bookings():
    try:
        bookings_ref = db.collection("resourceBookings").stream()
        bookings = []
        for doc in bookings_ref:
            data = doc.to_dict()
            data["id"] = doc.id
            bookings.append(data)
        return {"data": bookings}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch bookings") from exc


@router.post("", tags=["Resource Bookings"])
async def create_booking(payload: dict = Body(...)):
    try:
        now = datetime.now(timezone.utc)
        booking_doc = {
            "resourceId": payload.get("resourceId", "room-01"),
            "resourceName": payload.get("resourceName", "Conference Room"),
            "bookedBy": payload.get("bookedBy", "admin"),
            "bookedByName": payload.get("bookedByName", "Admin"),
            "startTime": payload.get("startTime"),
            "endTime": payload.get("endTime"),
            "status": payload.get("status", "confirmed"),
            "notes": payload.get("notes", ""),
            "createdAt": now,
            "updatedAt": now,
        }
        ref = db.collection("resourceBookings").document()
        ref.set(booking_doc)
        booking_doc["id"] = ref.id
        return {"message": "Booking created successfully", "data": booking_doc}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create booking") from exc
