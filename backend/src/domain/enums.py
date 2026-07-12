from enum import Enum

class DepartmentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"

class DepreciationMethod(str, Enum):
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    NONE = "none"

class AssetStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    IN_MAINTENANCE = "in_maintenance"
    RETIRED = "retired"
    LOST = "lost"

class AssetCondition(str, Enum):
    NEW = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DAMAGED = "damaged"

class AllocationStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"

class ResourceType(str, Enum):
    CONFERENCE_ROOM = "conference_room"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    OTHER = "other"

class ResourceStatus(str, Enum):
    ACTIVE = "active"
    UNDER_MAINTENANCE = "under_maintenance"
    INACTIVE = "inactive"

class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class MaintenancePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MaintenanceStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"

class MaintenanceLogAction(str, Enum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    COMMENTED = "commented"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AuditCycleStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class NotificationType(str, Enum):
    ALLOCATION_ASSIGNED = "allocation_assigned"
    ALLOCATION_DUE = "allocation_due"
    MAINTENANCE_STATUS_CHANGE = "maintenance_status_change"
    MAINTENANCE_APPROVAL_NEEDED = "maintenance_approval_needed"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    AUDIT_ASSIGNED = "audit_assigned"
    AUDIT_DISCREPANCY = "audit_discrepancy"
    SYSTEM = "system"

class RelatedEntityType(str, Enum):
    ASSET = "asset"
    ALLOCATION = "allocation"
    RESOURCE = "resource"
    BOOKING = "booking"
    MAINTENANCE_REQUEST = "maintenanceRequest"
    AUDIT_CYCLE = "auditCycle"

class DashboardScope(str, Enum):
    GLOBAL = "global"
    DEPARTMENT = "department"
    DAILY = "daily"

class AuditLogAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"

class PermissionModule(str, Enum):
    DEPARTMENT = "department"
    EMPLOYEE = "employee"
    ROLE = "role"
    ASSET = "asset"
    ALLOCATION = "allocation"
    RESOURCE = "resource"
    BOOKING = "booking"
    MAINTENANCE = "maintenance"
    AUDIT = "audit"
    NOTIFICATION = "notification"
    DASHBOARD = "dashboard"
