from abc import abstractmethod
from datetime import datetime
from src.domain.entities.resource_booking import ResourceBooking
from src.domain.repositories.base_repository import BaseRepository

class ResourceBookingRepository(BaseRepository[ResourceBooking]):
    @abstractmethod
    def find_confirmed_bookings_for_resource(
        self, resource_id: str, start_time: datetime, end_time: datetime
    ) -> list[ResourceBooking]:
        """Find all confirmed resource bookings overlapping the given timeframe."""
        pass
