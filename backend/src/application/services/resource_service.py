from datetime import datetime, timedelta
from typing import Any
from fastapi import Depends
from src.domain.entities.shared_resource import SharedResource, BookingRules
from src.domain.entities.resource_booking import ResourceBooking
from src.domain.enums import ResourceStatus, BookingStatus, NotificationType, RelatedEntityType, AuditLogAction
from src.domain.repositories.shared_resource_repository import SharedResourceRepository
from src.infrastructure.firestore.repositories.firestore_shared_resource_repository import get_shared_resource_repository
from src.domain.repositories.resource_booking_repository import ResourceBookingRepository
from src.infrastructure.firestore.repositories.firestore_resource_booking_repository import get_resource_booking_repository
from src.domain.value_objects.snapshots import ResourceSnapshot, EmployeeBookingSnapshot
from src.application.services.audit_log_service import AuditLogService, get_audit_log_service
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.infrastructure.firestore.counters import get_next_resource_code
from src.shared.errors import NotFoundError, ConflictError, ValidationError

class ResourceService:
    def __init__(
        self,
        resource_repo: SharedResourceRepository,
        booking_repo: ResourceBookingRepository,
        audit_log_service: AuditLogService
    ):
        self.resource_repo = resource_repo
        self.booking_repo = booking_repo
        self.audit_log_service = audit_log_service

    # --- Shared Resource CRUD ---
    def get_resource_by_id(self, resource_id: str) -> SharedResource | None:
        return self.resource_repo.get_by_id(resource_id)

    def list_resources(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[SharedResource], str | None]:
        actual_sort_by = sort_by or "name"
        return self.resource_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def create_resource(
        self,
        name: str,
        type_str: str,
        capacity: int | None,
        location: str,
        amenities: list[str],
        image_urls: list[str],
        booking_rules: BookingRules,
        actor_id: str
    ) -> SharedResource:
        def tx(transaction) -> SharedResource:
            # Generate sequential Resource Code
            resource_code = get_next_resource_code(transaction)
            
            res = SharedResource(
                id=resource_code,
                resource_code=resource_code,
                name=name,
                type=type_str,
                capacity=capacity,
                location=location,
                amenities=amenities,
                image_urls=image_urls,
                status=ResourceStatus.ACTIVE,
                booking_rules=booking_rules,
                created_by=actor_id,
                updated_by=actor_id
            )
            created_res = self.resource_repo.create(res)
            
            # Audit log
            self.audit_log_service.log_action(
                entity_type="sharedResources",
                entity_id=resource_code,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=created_res.model_dump(by_alias=True, exclude_none=True)
            )
            return created_res

        return run_in_transaction(tx)

    def update_resource(
        self,
        resource_id: str,
        name: str | None,
        type_str: str | None,
        capacity: int | None,
        location: str | None,
        amenities: list[str] | None,
        image_urls: list[str] | None,
        booking_rules: BookingRules | None,
        actor_id: str
    ) -> SharedResource:
        def tx(transaction) -> SharedResource:
            res_ref = db.collection("sharedResources").document(resource_id)
            res_snap = transaction.get(res_ref)
            if not res_snap.exists or res_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Resource {resource_id} not found")
                
            old_data = res_snap.to_dict() or {}
            updates: dict[str, Any] = {}
            
            if name is not None:
                updates["name"] = name
            if type_str is not None:
                updates["type"] = type_str
            if capacity is not None:
                updates["capacity"] = capacity
            if location is not None:
                updates["location"] = location
            if amenities is not None:
                updates["amenities"] = amenities
            if image_urls is not None:
                updates["imageUrls"] = image_urls
            if booking_rules is not None:
                updates["bookingRules"] = booking_rules.model_dump(by_alias=True)
                
            if not updates:
                old_data["id"] = res_snap.id
                return SharedResource.model_validate(old_data)
                
            updated_res = self.resource_repo.update(resource_id, updates, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="sharedResources",
                entity_id=resource_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={k: old_data.get(k) for k in updates.keys()},
                after_snapshot={k: getattr(updated_res, k, None) for k in updates.keys()}
            )
            return updated_res

        return run_in_transaction(tx)

    def soft_delete_resource(self, resource_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            # 1. Fetch resource
            res_ref = db.collection("sharedResources").document(resource_id)
            res_snap = transaction.get(res_ref)
            if not res_snap.exists or res_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Resource {resource_id} not found")
                
            # 2. Block if any active confirmed bookings exist
            active_bookings = db.collection("resourceBookings")\
                                .where("resourceId", "==", resource_id)\
                                .where("status", "==", BookingStatus.CONFIRMED.value)\
                                .where("isDeleted", "==", False)\
                                .limit(1).get(transaction=transaction)
            if active_bookings:
                raise ConflictError(f"Resource '{resource_id}' cannot be deleted: it has active confirmed bookings")
                
            self.resource_repo.soft_delete(resource_id, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="sharedResources",
                entity_id=resource_id,
                action=AuditLogAction.SOFT_DELETE,
                performed_by=actor_id
            )

        run_in_transaction(tx)

    def restore_resource(self, resource_id: str, actor_id: str) -> None:
        def tx(transaction) -> None:
            res_ref = db.collection("sharedResources").document(resource_id)
            res_snap = transaction.get(res_ref)
            if not res_snap.exists:
                raise NotFoundError(f"Resource {resource_id} not found")
                
            self.resource_repo.restore(resource_id)
            self.resource_repo.update(resource_id, {}, actor_id)
            
            self.audit_log_service.log_action(
                entity_type="sharedResources",
                entity_id=resource_id,
                action=AuditLogAction.RESTORE,
                performed_by=actor_id
            )

        run_in_transaction(tx)


    # --- Resource Booking Operations ---
    def get_booking_by_id(self, booking_id: str) -> ResourceBooking | None:
        return self.booking_repo.get_by_id(booking_id)

    def list_bookings(
        self,
        limit: int = 25,
        cursor: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        filters: dict | None = None,
        include_deleted: bool = False
    ) -> tuple[list[ResourceBooking], str | None]:
        actual_sort_by = sort_by or "startTime"
        return self.booking_repo.list(
            limit=limit,
            cursor=cursor,
            sort_by=actual_sort_by,
            sort_dir=sort_dir,
            filters=filters,
            include_deleted=include_deleted
        )

    def create_booking(
        self,
        resource_id: str,
        employee_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendee_ids: list[str],
        actor_id: str
    ) -> ResourceBooking:
        def tx(transaction) -> ResourceBooking:
            # 1. Fetch resource and validate
            res_ref = db.collection("sharedResources").document(resource_id)
            res_snap = transaction.get(res_ref)
            if not res_snap.exists or res_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Resource {resource_id} not found or is deleted")
                
            res_data = res_snap.to_dict() or {}
            if res_data.get("status") != ResourceStatus.ACTIVE.value:
                raise ConflictError(f"Resource '{resource_id}' is currently not active")

            # 2. Validate booking rules
            booking_rules = res_data.get("bookingRules", {})
            min_dur = booking_rules.get("minDurationMinutes", RESOURCE_DEFAULT_MIN_DURATION)
            max_dur = booking_rules.get("maxDurationMinutes", RESOURCE_DEFAULT_MAX_DURATION)
            advance_days = booking_rules.get("advanceBookingDays", RESOURCE_DEFAULT_ADVANCE_DAYS)
            
            duration_minutes = (end_time - start_time).total_seconds() / 60.0
            if duration_minutes < min_dur or duration_minutes > max_dur:
                raise ValidationError(
                    f"Booking duration ({duration_minutes} mins) must be between {min_dur} and {max_dur} minutes"
                )
                
            max_advance_date = datetime.utcnow() + timedelta(days=advance_days)
            if start_time > max_advance_date:
                raise ValidationError(
                    f"Booking cannot be made more than {advance_days} days in advance"
                )

            # 3. Verify booking employee
            emp_ref = db.collection("employees").document(employee_id)
            emp_snap = transaction.get(emp_ref)
            if not emp_snap.exists or emp_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Employee {employee_id} not found or is deleted")
            emp_data = emp_snap.to_dict() or {}

            # 4. Verify attendees
            if attendee_ids:
                attendee_refs = [db.collection("employees").document(aid) for aid in attendee_ids]
                attendee_snaps = transaction.get(attendee_refs)
                for i, snap in enumerate(attendee_snaps):
                    if not snap.exists or snap.to_dict().get("isDeleted", False):
                        raise NotFoundError(f"Attendee employee {attendee_ids[i]} not found or is deleted")

            # 5. Overlap checking (concurrency conflict prevention)
            # Find confirmed bookings for the resource starting before end_time
            query = db.collection("resourceBookings")\
                      .where("resourceId", "==", resource_id)\
                      .where("status", "==", BookingStatus.CONFIRMED.value)\
                      .where("isDeleted", "==", False)\
                      .where("startTime", "<", end_time)
            
            snapshots = query.get(transaction=transaction)
            for snap in snapshots:
                bdata = snap.to_dict() or {}
                bstart = bdata.get("startTime")
                bend = bdata.get("endTime")
                if bstart and bend:
                    # check range intersection in memory: bstart < end_time AND bend > start_time
                    if bstart < end_time and bend > start_time:
                        raise ConflictError(
                            f"Booking conflict: Resource '{resource_id}' is already booked from {bstart} to {bend}"
                        )

            # 6. Create booking
            booking_ref = db.collection("resourceBookings").document()
            booking_id = booking_ref.id
            
            resource_snapshot = {
                "resourceCode": res_data.get("resourceCode", resource_id),
                "name": res_data.get("name", "")
            }
            employee_snapshot = {
                "fullName": emp_data.get("fullName", "")
            }
            
            booking_dict = {
                "resourceId": resource_id,
                "resourceSnapshot": resource_snapshot,
                "employeeId": employee_id,
                "employeeSnapshot": employee_snapshot,
                "title": title,
                "startTime": start_time,
                "endTime": end_time,
                "attendeeIds": attendee_ids,
                "status": BookingStatus.CONFIRMED.value,
                "cancellationReason": None,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "createdBy": actor_id,
                "updatedBy": actor_id,
                "isDeleted": False,
                "deletedAt": None,
                "deletedBy": None
            }
            transaction.set(booking_ref, booking_dict)

            # 7. Send notifications to booking employee and attendees
            notification_recipients = list(set([employee_id] + attendee_ids))
            for recipient in notification_recipients:
                notif_ref = db.collection("notifications").document()
                notif_dict = {
                    "recipientId": recipient,
                    "type": NotificationType.BOOKING_CONFIRMED.value,
                    "title": "Resource Booking Confirmed",
                    "body": f"Booking '{title}' for {resource_snapshot['name']} from {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')} has been confirmed.",
                    "relatedEntityType": RelatedEntityType.BOOKING.value,
                    "relatedEntityId": booking_id,
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

            # 8. Log audit
            booking_dict["id"] = booking_id
            booking_dict["startTime"] = start_time
            booking_dict["endTime"] = end_time
            booking_dict["createdAt"] = start_time # dummy stamps representation
            booking_dict["updatedAt"] = start_time
            self.audit_log_service.log_action(
                entity_type="resourceBookings",
                entity_id=booking_id,
                action=AuditLogAction.CREATE,
                performed_by=actor_id,
                after_snapshot=booking_dict
            )
            return ResourceBooking.model_validate(booking_dict)

        return run_in_transaction(tx)

    def cancel_booking(self, booking_id: str, cancellation_reason: str, actor_id: str) -> ResourceBooking:
        def tx(transaction) -> ResourceBooking:
            # 1. Fetch booking
            booking_ref = db.collection("resourceBookings").document(booking_id)
            booking_snap = transaction.get(booking_ref)
            if not booking_snap.exists or booking_snap.to_dict().get("isDeleted", False):
                raise NotFoundError(f"Booking {booking_id} not found")
                
            booking_data = booking_snap.to_dict() or {}
            old_status = booking_data.get("status")
            if old_status != BookingStatus.CONFIRMED.value:
                raise ConflictError(f"Cannot cancel booking in '{old_status}' status")

            if not cancellation_reason:
                raise ValidationError("Cancellation reason is required to cancel a booking")

            # 2. Update status
            updates = {
                "status": BookingStatus.CANCELLED.value,
                "cancellationReason": cancellation_reason,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": actor_id
            }
            transaction.update(booking_ref, updates)

            # 3. Notify participants
            recipient_ids = list(set([booking_data.get("employeeId")] + booking_data.get("attendeeIds", [])))
            res_name = booking_data.get("resourceSnapshot", {}).get("name", "Resource")
            
            for recipient in recipient_ids:
                if not recipient:
                    continue
                notif_ref = db.collection("notifications").document()
                notif_dict = {
                    "recipientId": recipient,
                    "type": NotificationType.BOOKING_CANCELLED.value,
                    "title": "Resource Booking Cancelled",
                    "body": f"Booking '{booking_data.get('title')}' for {res_name} has been cancelled. Reason: {cancellation_reason}",
                    "relatedEntityType": RelatedEntityType.BOOKING.value,
                    "relatedEntityId": booking_id,
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

            # 4. Log audit
            self.audit_log_service.log_action(
                entity_type="resourceBookings",
                entity_id=booking_id,
                action=AuditLogAction.UPDATE,
                performed_by=actor_id,
                before_snapshot={"status": old_status},
                after_snapshot={"status": BookingStatus.CANCELLED.value}
            )

            updated_snap = booking_ref.get()
            updated_data = updated_snap.to_dict() or {}
            updated_data["id"] = booking_id
            return ResourceBooking.model_validate(updated_data)

        return run_in_transaction(tx)

def get_shared_resource_service(
    resource_repo: SharedResourceRepository = Depends(get_shared_resource_repository),
    booking_repo: ResourceBookingRepository = Depends(get_resource_booking_repository),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
) -> ResourceService:
    """Dependency injection factory for ResourceService."""
    return ResourceService(resource_repo, booking_repo, audit_log_service)
