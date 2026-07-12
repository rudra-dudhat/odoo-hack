from datetime import datetime
from google.cloud import firestore
from src.infrastructure.firestore.client import db
from src.infrastructure.firestore.transactions import run_in_transaction
from src.domain.enums import AllocationStatus, BookingStatus, NotificationType, RelatedEntityType, AuditLogAction
from src.application.services.audit_log_service import get_audit_log_service
from src.shared.logging import logger

def check_overdue_allocations() -> int:
    """
    Cron Job (Daily).
    Queries active allocations past expectedReturnDate, flags them 'overdue',
    notifies the holder, and writes audit trails.
    Returns count of updated allocations.
    """
    now = datetime.utcnow()
    logger.info(f"Starting overdue allocations checker at {now.isoformat()}")
    
    # Query all active allocations where expectedReturnDate < now
    query = db.collection("assetAllocations")\
              .where("status", "==", AllocationStatus.ACTIVE.value)\
              .where("isDeleted", "==", False)\
              .where("expectedReturnDate", "<", now)
              
    snapshots = query.get()
    updated_count = 0
    
    audit_service = get_audit_log_service()

    for snap in snapshots:
        alloc_id = snap.id
        alloc_data = snap.to_dict() or {}
        emp_id = alloc_data.get("employeeId")
        asset_tag = alloc_data.get("assetSnapshot", {}).get("assetTag", "")
        expected_date = alloc_data.get("expectedReturnDate")
        
        def tx(transaction) -> bool:
            ref = db.collection("assetAllocations").document(alloc_id)
            cur_snap = transaction.get(ref)
            if not cur_snap.exists or cur_snap.to_dict().get("status") != AllocationStatus.ACTIVE.value:
                return False
                
            # Update allocation status to OVERDUE
            transaction.update(ref, {
                "status": AllocationStatus.OVERDUE.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": "system"
            })
            
            # Emit notification
            notif_ref = db.collection("notifications").document()
            transaction.set(notif_ref, {
                "recipientId": emp_id,
                "type": NotificationType.ALLOCATION_DUE.value,
                "title": "Asset Return Overdue",
                "body": f"The return for asset {asset_tag} was expected on {expected_date} and is now overdue. Please return it as soon as possible.",
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
            })
            
            # Write audit trail
            audit_service.log_action(
                entity_type="assetAllocations",
                entity_id=alloc_id,
                action=AuditLogAction.UPDATE,
                performed_by="system",
                before_snapshot={"status": AllocationStatus.ACTIVE.value},
                after_snapshot={"status": AllocationStatus.OVERDUE.value}
            )
            return True

        try:
            success = run_in_transaction(tx)
            if success:
                updated_count += 1
        except Exception as e:
            logger.error(f"Failed to flag overdue allocation {alloc_id}: {e}")

    logger.info(f"Completed overdue allocations checker. Flagged {updated_count} allocations.")
    return updated_count


def autocomplete_resource_bookings() -> int:
    """
    Cron Job (Hourly).
    Queries confirmed resourceBookings past endTime, transitions them 'completed',
    and records audit trail events.
    Returns count of completed bookings.
    """
    now = datetime.utcnow()
    logger.info(f"Starting resource bookings autocompleter at {now.isoformat()}")
    
    query = db.collection("resourceBookings")\
              .where("status", "==", BookingStatus.CONFIRMED.value)\
              .where("isDeleted", "==", False)\
              .where("endTime", "<", now)
              
    snapshots = query.get()
    updated_count = 0
    
    audit_service = get_audit_log_service()

    for snap in snapshots:
        booking_id = snap.id
        
        def tx(transaction) -> bool:
            ref = db.collection("resourceBookings").document(booking_id)
            cur_snap = transaction.get(ref)
            if not cur_snap.exists or cur_snap.to_dict().get("status") != BookingStatus.CONFIRMED.value:
                return False
                
            # Update status to COMPLETED
            transaction.update(ref, {
                "status": BookingStatus.COMPLETED.value,
                "updatedAt": firestore.SERVER_TIMESTAMP,
                "updatedBy": "system"
            })
            
            # Log audit
            audit_service.log_action(
                entity_type="resourceBookings",
                entity_id=booking_id,
                action=AuditLogAction.UPDATE,
                performed_by="system",
                before_snapshot={"status": BookingStatus.CONFIRMED.value},
                after_snapshot={"status": BookingStatus.COMPLETED.value}
            )
            return True

        try:
            success = run_in_transaction(tx)
            if success:
                updated_count += 1
        except Exception as e:
            logger.error(f"Failed to autocomplete booking {booking_id}: {e}")

    logger.info(f"Completed bookings autocompleter. Autocompleted {updated_count} bookings.")
    return updated_count
