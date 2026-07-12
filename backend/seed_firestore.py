"""
seed_firestore.py
=================
Populates all Firestore collections defined in 01_database_claude.md
with realistic sample data for the ERP system.

Usage:
  1. Place your Firebase service-account key at:
       backend/serviceAccountKey.json
  2. Install deps:
       pip install firebase-admin
  3. Run:
       python backend/seed_firestore.py

The script is idempotent — running it again will overwrite the same document IDs.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# ─── Initialise SDK ────────────────────────────────────────────────────────────
KEY_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
if not os.path.exists(KEY_PATH):
    print("ERROR: serviceAccountKey.json not found in backend/")
    print("Download it from Firebase Console → Project Settings → Service Accounts")
    sys.exit(1)

cred = credentials.Certificate(KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ─── Helpers ───────────────────────────────────────────────────────────────────
SERVER_TS = firestore.SERVER_TIMESTAMP

def ts(dt: datetime):
    """Convert a datetime to a Firestore-compatible value."""
    return dt

def now():
    return datetime.now(timezone.utc)

def audit(created_by="system", updated_by="system"):
    return {
        "createdAt": SERVER_TS,
        "updatedAt": SERVER_TS,
        "createdBy": created_by,
        "updatedBy": updated_by,
        "isDeleted": False,
        "deletedAt": None,
        "deletedBy": None,
    }

def set_doc(collection: str, doc_id: str, data: dict):
    db.collection(collection).document(doc_id).set(data)
    print(f"  ✔  {collection}/{doc_id}")

def set_subdoc(col1, id1, col2, id2, data):
    db.collection(col1).document(id1).collection(col2).document(id2).set(data)
    print(f"  ✔  {col1}/{id1}/{col2}/{id2}")

# ─── 1. PERMISSIONS ────────────────────────────────────────────────────────────
print("\n── permissions ──")
PERMISSIONS = [
    ("perm_dept_view",         "department.view",         "View Departments",           "department"),
    ("perm_dept_manage",       "department.manage",       "Manage Departments",         "department"),
    ("perm_emp_view",          "employee.view",           "View Employees",             "employee"),
    ("perm_emp_manage",        "employee.manage",         "Manage Employees",           "employee"),
    ("perm_role_manage",       "role.manage",             "Manage Roles",               "role"),
    ("perm_asset_view",        "asset.view",              "View Assets",                "asset"),
    ("perm_asset_create",      "asset.create",            "Create Asset",               "asset"),
    ("perm_asset_edit",        "asset.edit",              "Edit Asset",                 "asset"),
    ("perm_asset_delete",      "asset.delete",            "Delete Asset",               "asset"),
    ("perm_asset_allocate",    "asset.allocate",          "Allocate Asset",             "allocation"),
    ("perm_booking_view",      "booking.view",            "View Bookings",              "booking"),
    ("perm_booking_create",    "booking.create",          "Create Booking",             "booking"),
    ("perm_booking_cancel",    "booking.cancel",          "Cancel Booking",             "booking"),
    ("perm_maintenance_view",  "maintenance.view",        "View Maintenance",           "maintenance"),
    ("perm_maintenance_create","maintenance.create",      "Create Maintenance Request", "maintenance"),
    ("perm_maintenance_approve","maintenance.approve",    "Approve Maintenance Request","maintenance"),
    ("perm_audit_view",        "audit.view",              "View Audit Cycles",          "audit"),
    ("perm_audit_manage",      "audit.manage",            "Manage Audit Cycles",        "audit"),
    ("perm_dashboard_view",    "dashboard.view",          "View Dashboard",             "dashboard"),
    ("perm_notif_view",        "notification.view",       "View Notifications",         "notification"),
]
for pid, key, label, module in PERMISSIONS:
    set_doc("permissions", pid, {"key": key, "label": label, "module": module, **audit()})

# ─── 2. ROLES ──────────────────────────────────────────────────────────────────
print("\n── roles ──")
ALL_PERMS = [p[0] for p in PERMISSIONS]
MANAGER_PERMS = [p[0] for p in PERMISSIONS if p[0] not in ("perm_dept_manage","perm_role_manage","perm_emp_manage","perm_asset_delete")]
EMPLOYEE_PERMS = ["perm_asset_view","perm_booking_view","perm_booking_create","perm_booking_cancel",
                  "perm_maintenance_view","perm_maintenance_create","perm_notif_view","perm_dashboard_view"]

ROLES = [
    ("role_admin",    "Administrator", "Full system access",          ALL_PERMS,      True),
    ("role_manager",  "Manager",       "Department manager with approval rights", MANAGER_PERMS, True),
    ("role_employee", "Employee",      "Standard employee access",    EMPLOYEE_PERMS, True),
    ("role_auditor",  "Auditor",       "Can conduct and manage audits",
     ["perm_asset_view","perm_audit_view","perm_audit_manage","perm_notif_view","perm_dashboard_view"], False),
    ("role_technician","Technician",   "Handles maintenance requests",
     ["perm_asset_view","perm_maintenance_view","perm_maintenance_create","perm_notif_view"], False),
]
for rid, name, desc, perms, is_sys in ROLES:
    set_doc("roles", rid, {"name": name, "description": desc, "permissionIds": perms,
                           "isSystemRole": is_sys, **audit()})

# ─── 3. DEPARTMENTS ────────────────────────────────────────────────────────────
print("\n── departments ──")
DEPARTMENTS = [
    ("dep_eng",    "Engineering",       "ENG", "Software and hardware engineering"),
    ("dep_fin",    "Finance",           "FIN", "Financial operations and accounting"),
    ("dep_hr",     "Human Resources",   "HR",  "People operations"),
    ("dep_ops",    "Operations",        "OPS", "Facilities and day-to-day operations"),
    ("dep_it",     "IT & Infrastructure","IT", "IT support and infrastructure"),
]
for did, name, code, desc in DEPARTMENTS:
    set_doc("departments", did, {
        "name": name, "code": code, "description": desc,
        "headEmployeeId": None, "status": "active",
        "employeeCount": 0, "assetCount": 0, **audit("uid_admin001"),
    })

# ─── 4. ASSET CATEGORIES ───────────────────────────────────────────────────────
print("\n── assetCategories ──")
CATEGORIES = [
    ("cat_laptops",   "Laptops",       "LAP", "Portable computers",       None,          "straight_line", 36),
    ("cat_desktops",  "Desktops",      "DSK", "Desktop workstations",      None,          "straight_line", 48),
    ("cat_monitors",  "Monitors",      "MON", "Display monitors",          None,          "straight_line", 60),
    ("cat_phones",    "Mobile Phones", "PHN", "Company mobile phones",     None,          "straight_line", 24),
    ("cat_furniture", "Furniture",     "FUR", "Office furniture",          None,          "none",          120),
    ("cat_vehicles",  "Vehicles",      "VEH", "Company vehicles",          None,          "declining_balance", 60),
    ("cat_projectors","Projectors",    "PRJ", "Projection equipment",      None,          "straight_line", 36),
    ("cat_servers",   "Servers",       "SRV", "Rack-mount and blade servers", None,       "straight_line", 60),
]
for cid, name, code, desc, parent, dep_method, life in CATEGORIES:
    set_doc("assetCategories", cid, {
        "name": name, "code": code, "description": desc,
        "parentCategoryId": parent, "depreciationMethod": dep_method,
        "defaultUsefulLifeMonths": life, "assetCount": 0, **audit("uid_admin001"),
    })

# ─── 5. COUNTERS ───────────────────────────────────────────────────────────────
print("\n── counters ──")
COUNTERS = [
    ("assets",               "AST", 6, 5),
    ("resources",            "RES", 6, 3),
    ("maintenanceRequests",  "MR",  5, 2),
    ("auditCycles",          "AC",  2, 1),
    ("employees",            "EMP", 5, 8),
]
for cid, prefix, padding, value in COUNTERS:
    set_doc("counters", cid, {
        "value": value, "prefix": prefix, "padding": padding,
        "updatedAt": SERVER_TS,
    })

# ─── 6. EMPLOYEES (sample — no real Auth UIDs yet) ─────────────────────────────
print("\n── employees ──")
# NOTE: In production, employeeId MUST equal the Firebase Auth UID.
# These IDs are placeholders — replace with real Auth UIDs after users sign up.
EMPLOYEES = [
    ("uid_admin001",  "Admin User",    "admin@erp.local",    "dep_eng", "role_admin",     "EMP-00001", "System Administrator", "+910000000001"),
    ("uid_mgr_eng",   "Arjun Mehta",   "arjun@erp.local",    "dep_eng", "role_manager",   "EMP-00002", "Engineering Manager",  "+919876543210"),
    ("uid_emp_priya", "Priya Sharma",  "priya@erp.local",    "dep_eng", "role_employee",  "EMP-00003", "Senior Developer",     "+919876543211"),
    ("uid_emp_ravi",  "Ravi Kumar",    "ravi@erp.local",     "dep_it",  "role_technician","EMP-00004", "IT Technician",        "+919876543212"),
    ("uid_mgr_fin",   "Sunita Rao",    "sunita@erp.local",   "dep_fin", "role_manager",   "EMP-00005", "Finance Manager",      "+919876543213"),
    ("uid_emp_deepa", "Deepa Nair",    "deepa@erp.local",    "dep_hr",  "role_employee",  "EMP-00006", "HR Executive",         "+919876543214"),
    ("uid_aud001",    "Kiran Patel",   "kiran@erp.local",    "dep_ops", "role_auditor",   "EMP-00007", "Senior Auditor",       "+919876543215"),
    ("uid_emp_anil",  "Anil Singh",    "anil@erp.local",     "dep_eng", "role_employee",  "EMP-00008", "Developer",            "+919876543216"),
]
DEPT_SNAP = {
    "dep_eng": {"name":"Engineering","code":"ENG"},
    "dep_fin": {"name":"Finance","code":"FIN"},
    "dep_hr":  {"name":"Human Resources","code":"HR"},
    "dep_ops": {"name":"Operations","code":"OPS"},
    "dep_it":  {"name":"IT & Infrastructure","code":"IT"},
}
ROLE_SNAP = {
    "role_admin":     {"name":"Administrator"},
    "role_manager":   {"name":"Manager"},
    "role_employee":  {"name":"Employee"},
    "role_auditor":   {"name":"Auditor"},
    "role_technician":{"name":"Technician"},
}
JOIN = datetime(2023, 1, 1, tzinfo=timezone.utc)
for uid, name, email, dept, role, emp_code, designation, phone in EMPLOYEES:
    set_doc("employees", uid, {
        "fullName": name, "email": email, "phone": phone,
        "avatarUrl": None,
        "departmentId": dept, "departmentSnapshot": DEPT_SNAP[dept],
        "roleId": role,       "roleSnapshot": ROLE_SNAP[role],
        "designation": designation, "employeeCode": emp_code,
        "joinDate": JOIN, "status": "active",
        **audit("uid_admin001", "uid_admin001"),
    })

# Update department headEmployeeId
db.collection("departments").document("dep_eng").update({"headEmployeeId": "uid_mgr_eng"})
db.collection("departments").document("dep_fin").update({"headEmployeeId": "uid_mgr_fin"})

# ─── 7. ASSETS ─────────────────────────────────────────────────────────────────
print("\n── assets ──")
ASSETS = [
    ("AST-000001","Dell Latitude 5440","cat_laptops", "dep_eng","SN-11001","Dell","Latitude 5440","available","good"),
    ("AST-000002","Dell Latitude 5440","cat_laptops", "dep_eng","SN-11002","Dell","Latitude 5440","allocated","good"),
    ("AST-000003","MacBook Pro 14",    "cat_laptops", "dep_eng","SN-11003","Apple","MacBook Pro","available","new"),
    ("AST-000004","HP EliteDesk 800",  "cat_desktops","dep_fin","SN-22001","HP","EliteDesk 800","available","good"),
    ("AST-000005","LG 27UK850",        "cat_monitors","dep_eng","SN-33001","LG","27UK850","allocated","good"),
]
CAT_SNAP = {
    "cat_laptops":  {"name":"Laptops","code":"LAP"},
    "cat_desktops": {"name":"Desktops","code":"DSK"},
    "cat_monitors": {"name":"Monitors","code":"MON"},
}
for aid, name, cat, dept, sn, mfr, model, status, condition in ASSETS:
    set_doc("assets", aid, {
        "assetTag": aid, "name": name,
        "categoryId": cat, "categorySnapshot": CAT_SNAP[cat],
        "departmentId": dept, "departmentSnapshot": DEPT_SNAP[dept],
        "serialNumber": sn, "manufacturer": mfr, "model": model,
        "purchaseDate": datetime(2025,6,1,tzinfo=timezone.utc),
        "purchaseCost": 120000, "currency": "INR",
        "warrantyExpiryDate": datetime(2028,6,1,tzinfo=timezone.utc),
        "location": "HQ - Floor 3",
        "imageUrls": [], "status": status, "condition": condition,
        "currentAllocationId": None, "currentHolderSnapshot": None,
        **audit("uid_admin001"),
    })

# ─── 8. ASSET ALLOCATIONS ──────────────────────────────────────────────────────
print("\n── assetAllocations ──")
ALLOCS = [
    ("alloc_001","AST-000002","uid_emp_priya","uid_mgr_eng"),
    ("alloc_002","AST-000005","uid_emp_anil", "uid_mgr_eng"),
]
for aid, asset_id, emp_id, created_by in ALLOCS:
    set_doc("assetAllocations", aid, {
        "assetId": asset_id,
        "assetSnapshot": {"assetTag": asset_id, "name": "Dell Latitude 5440"},
        "employeeId": emp_id,
        "employeeSnapshot": {"fullName": "Priya Sharma" if emp_id=="uid_emp_priya" else "Anil Singh", "employeeCode": "EMP-00003" if emp_id=="uid_emp_priya" else "EMP-00008"},
        "allocatedAt": SERVER_TS,
        "expectedReturnDate": None, "returnedAt": None,
        "status": "active", "conditionAtAllocation": "good",
        "conditionAtReturn": None, "notes": "Standard allocation",
        **audit(created_by),
    })
# Update asset pointers
db.collection("assets").document("AST-000002").update({
    "currentAllocationId": "alloc_001",
    "currentHolderSnapshot": {"employeeId":"uid_emp_priya","fullName":"Priya Sharma"},
})
db.collection("assets").document("AST-000005").update({
    "currentAllocationId": "alloc_002",
    "currentHolderSnapshot": {"employeeId":"uid_emp_anil","fullName":"Anil Singh"},
})

# ─── 9. SHARED RESOURCES ───────────────────────────────────────────────────────
print("\n── sharedResources ──")
RESOURCES = [
    ("RES-000001","Conference Room Alpha","conference_room",12,"HQ - Floor 2",["projector","whiteboard","video_conf"]),
    ("RES-000002","Conference Room Beta", "conference_room", 8,"HQ - Floor 3",["whiteboard"]),
    ("RES-000003","Toyota Innova",        "vehicle",         7,"Basement Parking",[]),
]
for rid, name, rtype, cap, loc, amenities in RESOURCES:
    set_doc("sharedResources", rid, {
        "resourceCode": rid, "name": name, "type": rtype,
        "capacity": cap, "location": loc, "amenities": amenities,
        "imageUrls": [], "status": "active",
        "bookingRules": {"minDurationMinutes":30,"maxDurationMinutes":240,"advanceBookingDays":30},
        **audit("uid_admin001"),
    })

# ─── 10. RESOURCE BOOKINGS ─────────────────────────────────────────────────────
print("\n── resourceBookings ──")
start = datetime(2026, 7, 15, 9, 0, tzinfo=timezone.utc)
set_doc("resourceBookings","booking_001",{
    "resourceId":"RES-000001",
    "resourceSnapshot":{"resourceCode":"RES-000001","name":"Conference Room Alpha"},
    "employeeId":"uid_emp_priya",
    "employeeSnapshot":{"fullName":"Priya Sharma"},
    "title":"Sprint Planning", "startTime":start,
    "endTime": start + timedelta(hours=1.5),
    "attendeeIds":["uid_mgr_eng","uid_emp_anil"],
    "status":"confirmed","cancellationReason":None,
    **audit("uid_emp_priya","uid_emp_priya"),
})

# ─── 11. MAINTENANCE REQUESTS ──────────────────────────────────────────────────
print("\n── maintenanceRequests ──")
set_doc("maintenanceRequests","MR-2026-00001",{
    "requestNumber":"MR-2026-00001",
    "assetId":"AST-000002",
    "assetSnapshot":{"assetTag":"AST-000002","name":"Dell Latitude 5440"},
    "requestedBy":"uid_emp_priya",
    "requestedBySnapshot":{"fullName":"Priya Sharma"},
    "issueDescription":"Laptop screen flickers intermittently during use.",
    "priority":"high", "status":"pending_approval",
    "assignedTechnicianId":None,"assignedTechnicianSnapshot":None,
    "estimatedCost":None,"actualCost":None,
    "attachmentUrls":[],"completedAt":None,
    **audit("uid_emp_priya","uid_emp_priya"),
})
set_subdoc("maintenanceRequests","MR-2026-00001","logs","log_001",{
    "action":"created",
    "performedBy":"uid_emp_priya",
    "performedBySnapshot":{"fullName":"Priya Sharma"},
    "details":"Maintenance request submitted.",
    "previousStatus":None,"newStatus":"pending_approval",
    **audit("uid_emp_priya","uid_emp_priya"),
})

# ─── 12. AUDIT CYCLES ──────────────────────────────────────────────────────────
print("\n── auditCycles ──")
set_doc("auditCycles","AC-2026-Q3",{
    "cycleCode":"AC-2026-Q3",
    "name":"Q3 2026 Asset Verification",
    "departmentIds":["dep_eng","dep_fin"],
    "categoryIds":["cat_laptops"],
    "scheduledStart": datetime(2026,7,1,tzinfo=timezone.utc),
    "scheduledEnd":   datetime(2026,7,15,tzinfo=timezone.utc),
    "actualEnd":None, "status":"in_progress",
    "assignedAuditorIds":["uid_aud001"],
    "totalAssetsInScope":5, "assetsAudited":2, "discrepanciesFound":0,
    **audit("uid_admin001"),
})
set_subdoc("auditCycles","AC-2026-Q3","reports","rpt_001",{
    "assetId":"AST-000001",
    "assetSnapshot":{"assetTag":"AST-000001","name":"Dell Latitude 5440"},
    "auditedBy":"uid_aud001",
    "auditedBySnapshot":{"fullName":"Kiran Patel"},
    "auditedAt":SERVER_TS,
    "expectedLocation":"HQ - Floor 3","actualLocation":"HQ - Floor 3",
    "expectedCondition":"good","actualCondition":"good",
    "found":True,"discrepancyNotes":"","photoUrls":[],
    **audit("uid_aud001","uid_aud001"),
})

# ─── 13. NOTIFICATIONS ─────────────────────────────────────────────────────────
print("\n── notifications ──")
set_doc("notifications","notif_001",{
    "recipientId":"uid_mgr_eng",
    "type":"maintenance_approval_needed",
    "title":"Maintenance Request Awaiting Your Approval",
    "body":"MR-2026-00001: Laptop screen flicker reported by Priya Sharma.",
    "relatedEntityType":"maintenanceRequest",
    "relatedEntityId":"MR-2026-00001",
    "isRead":False,"readAt":None,
    **audit("system","system"),
})
set_doc("notifications","notif_002",{
    "recipientId":"uid_emp_priya",
    "type":"allocation_assigned",
    "title":"Asset Allocated to You",
    "body":"Dell Latitude 5440 (AST-000002) has been allocated to you.",
    "relatedEntityType":"allocation",
    "relatedEntityId":"alloc_001",
    "isRead":True,"readAt":SERVER_TS,
    **audit("system","system"),
})

# ─── 14. DASHBOARD AGGREGATES ──────────────────────────────────────────────────
print("\n── dashboardAggregates ──")
set_doc("dashboardAggregates","global_kpis",{
    "scope":"global","scopeRefId":None,
    "totalAssets":5,
    "assetsByStatus":{"available":3,"allocated":2,"in_maintenance":0,"retired":0,"lost":0},
    "totalActiveAllocations":2, "totalOverdueAllocations":0,
    "totalBookingsToday":1, "openMaintenanceRequests":1,
    "maintenanceByPriority":{"low":0,"medium":0,"high":1,"critical":0},
    "auditComplianceRate":0.0, "pendingNotificationsCount":1,
    "lastComputedAt":SERVER_TS,
    **audit(),
})

# ─── 15. AUDIT LOGS ────────────────────────────────────────────────────────────
print("\n── auditLogs ──")
set_doc("auditLogs","al_001",{
    "entityType":"assets","entityId":"AST-000001",
    "action":"create",
    "performedBy":"uid_admin001",
    "changedFields":[],
    "beforeSnapshot":None,
    "afterSnapshot":{"status":"available","condition":"good"},
    "createdAt":SERVER_TS,
    "ipAddress":None,
})

print("\n✅  Seed complete! All collections populated.")
print("\nNOTE: Replace placeholder employee UIDs (uid_admin001, uid_emp_priya, etc.)")
print("      with real Firebase Auth UIDs before using this in production.")
