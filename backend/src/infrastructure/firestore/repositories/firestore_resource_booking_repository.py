from datetime import datetime
from src.domain.entities.resource_booking import ResourceBooking
from src.domain.repositories.resource_booking_repository import ResourceBookingRepository
from src.infrastructure.firestore.repositories.base_firestore_repository import BaseFirestoreRepository

class FirestoreResourceBookingRepository(BaseFirestoreRepository[ResourceBooking], ResourceBookingRepository):
    def __init__(self):
        super().__init__("resourceBookings", ResourceBooking)

    def find_confirmed_bookings_for_resource(
        self, resource_id: str, start_time: datetime, end_time: datetime
    ) -> list[ResourceBooking]:
        # Fetch confirmed bookings for the resource starting before end_time (satisfies composite index)
        snapshots = self._collection_ref.where("resourceId", "==", resource_id)\
                                        .where("status", "==", "confirmed")\
                                        .where("isDeleted", "==", False)\
                                        .where("startTime", "<", end_time).get()
        
        overlapping = []
        for snap in snapshots:
            data = snap.to_dict() or {}
            data["id"] = snap.id
            booking = ResourceBooking.model_validate(data)
            
            # Verify overlap in application memory: existing.startTime < end_time AND existing.endTime > start_time
            if booking.start_time < end_time and booking.end_time > start_time:
                overlapping.append(booking)
                
        return overlapping

_repository_instance = None

def get_resource_booking_repository() -> ResourceBookingRepository:
    """Dependency injection factory for ResourceBookingRepository."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = FirestoreResourceBookingRepository()
    return _repository_instance
