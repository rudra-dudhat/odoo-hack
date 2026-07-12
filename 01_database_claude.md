# 01_database_claude.md
## Database Architect Instruction Document
### Enterprise Asset & Resource Management ERP — Firestore Database Architecture

**Status:** Single Source of Truth (SSOT) for all database decisions
**Applies to:** Firebase Firestore (Native Mode), Backend in Python (FastAPI/Firebase Admin SDK), Frontend in React
**Audience:** Any AI or engineer implementing the backend, without needing to ask database-related questions

---

## 1. Project Overview

This project is an **Enterprise Asset & Resource Management ERP** designed to manage organizational assets, shared resources, employees, departments, maintenance workflows, audits, notifications, and executive dashboards.

**Tech Stack:**
- **Frontend:** React (SPA), consuming REST/HTTPS callable APIs
- **Backend:** Python (FastAPI recommended), using Firebase Admin SDK for Firestore access
- **Database:** Firebase Firestore (Native Mode, NoSQL document database)
- **Auth:** Firebase Authentication (custom claims used for RBAC — roles/permissions)
- **Storage:** Firebase Storage (for asset images, documents, maintenance attachments, audit evidence)

**Core Modules Supported:**
1. Departments
2. Employees
3. Roles & Permissions (RBAC)
4. Asset Categories
5. Assets
6. Asset Allocations
7. Shared Resources
8. Resource Bookings
9. Maintenance Requests, Approvals, Logs
10. Audit Cycles & Audit Reports
11. Notifications
12. Dashboard KPIs (aggregated analytics)

This document defines **every collection, document shape, field, datatype, validation rule, relationship, index, and lifecycle** required to implement the backend with zero ambiguity.

---

## 2. Responsibilities of the Database AI

Any AI or engineer acting as "Database Architect" on this project must:

1. Treat this document as **law**. Do not invent new top-level collections, rename fields, or change datatypes without updating this document first.
2. Ensure every write operation from the backend enforces the validation rules defined here (Firestore has no native schema enforcement — validation is a **backend responsibility**, reinforced by Firestore Security Rules as a second layer).
3. Ensure every collection follows the **naming, ID, timestamp, soft-delete, and audit conventions** defined in Section 4 and Section 6.
4. Design all queries to be satisfiable by the **indexes defined in Section 9** — never require an index that isn't declared here; if a new query pattern is needed, this document must be updated with the new composite index first.
5. Keep documents **denormalized where read performance matters** and **normalized (referenced) where write consistency matters**, per the Reference Strategy (Section 8).
6. Never perform destructive hard deletes on business-critical data — follow the Soft Delete & Archive Strategy (Section 11).
7. Ensure every mutating operation stamps `createdBy`/`updatedBy`/`createdAt`/`updatedAt` per Section 12.
8. Keep Dashboard KPIs backed by **precomputed aggregation documents**, never by scanning full collections at read time (Section 18).
9. Flag any feature request that cannot be cleanly modeled in Firestore's NoSQL/document constraints (e.g., needing multi-collection ACID transactions beyond Firestore's 500-doc/1-transaction limit) rather than silently working around it.
10. Extend this document (never a parallel one) when new modules are added, preserving backward compatibility of existing collections.

---

## 3. Database Design Philosophy

1. **Collection-per-entity, subcollection-per-owned-child.** Top-level collections represent independent entities queried across the whole org (assets, employees, bookings). Subcollections are used only for data that is always accessed in the context of its parent and would otherwise bloat the parent document (e.g., `maintenanceLogs` under a `maintenanceRequests` document).
2. **Flat is better than deep.** Firestore query and security-rule complexity grows with nesting depth. This project caps nesting at **2 levels** (`collection/doc/subcollection/doc`) — no deeper.
3. **Read-optimized denormalization.** Since Firestore charges per document read and has no JOINs, frequently-displayed reference data (e.g., employee name+avatar on an allocation, asset name+tag on a booking) is **duplicated (denormalized snapshot)** into the referencing document at write time. Denormalized copies are treated as **read cache**, not source of truth — the source of truth is always the referenced document's own collection.
4. **IDs are stable references.** Every relationship is stored as the referenced document's Firestore Document ID (a string), never as a full path or DocumentReference object, to keep data portable and backend-language-agnostic.
5. **Every collection is auditable.** Every document has lifecycle timestamps and actor stamps (Section 12) and, where applicable, emits an entry into the central `auditLogs` collection (Section 16.5) — distinct from the ERP's own "Audit Cycles" business module.
6. **Soft delete by default.** Nothing that has ever been referenced by another document (assets, employees, resources) is hard-deleted. See Section 11.
7. **Enums are backend-enforced strings.** Firestore has no native enum type. All enum fields are `string` and validated against the fixed value sets defined in this document, both in backend code and in Firestore Security Rules (`request.resource.data.status in [...]`).
8. **Aggregation over ad-hoc computation.** Counts, sums, and KPI figures are maintained incrementally (via Cloud Functions / backend transactions) in dedicated aggregate documents rather than computed by scanning collections on every dashboard load.
9. **Multi-tenancy-ready, single-tenant initial scope.** All collections include an implicit single-organization scope for v1, but field/collection design avoids anything that would block adding an `orgId` partition key later (see Section 20).

---

## 4. Firestore Best Practices Applied in This Project

- **Document size:** Keep every document well under the 1 MiB Firestore limit. Large free-text fields (e.g., maintenance descriptions) are capped at the application layer (e.g., 5,000 characters) and large binary content (images, PDFs) is **never stored in Firestore** — only Firebase Storage URLs/paths are stored.
- **Array growth:** Never use unbounded arrays that grow forever (e.g., "list of all bookings for a resource" is NOT stored as an array on the resource document). Use subcollections or separate top-level collections with a reference field instead.
- **Hot document avoidance:** Global counters (e.g., "total assets") are NOT stored as a single field incremented on every write from every client. Use **distributed counters** (sharded aggregation documents) for high-write-frequency counters, or Cloud Functions-triggered aggregation for moderate-write-frequency ones. This project's expected write volume (enterprise internal tool, not consumer-scale) allows **single aggregation documents updated via Cloud Function triggers**, with a documented upgrade path to sharded counters (Section 19).
- **Composite indexes declared upfront:** All required composite indexes are listed in Section 9 and must be captured in `firestore.indexes.json` before deployment.
- **Security Rules as second line of defense:** Backend Python code is the primary validation layer (source of truth for business logic), but Firestore Security Rules must independently enforce: authentication required, role-based field-level restrictions, and enum/status whitelist checks, so that no client can bypass the backend and write directly to Firestore in an invalid state.
- **Timestamps use Firestore native `Timestamp` type** (not string dates), enabling correct range queries and ordering.
- **Server-side timestamp generation:** All `createdAt`/`updatedAt` fields are set via `firestore.SERVER_TIMESTAMP` (Python Admin SDK) — never client-supplied — to avoid clock-skew and manipulation.
- **Pagination:** All list queries use cursor-based pagination (`start_after` with `orderBy` + `limit`), never offset-based, for performance at scale.
- **Batched writes / transactions:** Any operation that touches multiple documents that must stay consistent (e.g., approving a maintenance request: update request status + create log entry + update asset status) is wrapped in a Firestore transaction or batched write.

---

## 5. Collection Naming Conventions

- All collection names are **camelCase, plural nouns**: `employees`, `assets`, `assetAllocations`, `resourceBookings`, `maintenanceRequests`, `auditCycles`, `notifications`.
- Subcollections follow the same camelCase-plural convention and are named for what they contain, not repeating the parent name: `maintenanceRequests/{id}/logs` (not `maintenanceRequests/{id}/maintenanceLogs`) — **exception**: where the subcollection name alone would be ambiguous out of context (e.g., generic `logs` used in two different parents), the fuller name is used. This project uses fuller explicit names everywhere for clarity — see Section 7 tree.
- No abbreviations in collection names (`assetCategories`, not `assetCats`).
- Enum-like static/config data that rarely changes (e.g., `roles`, `permissions`) is still a full top-level collection, not a hardcoded backend constant, so it can be managed via admin UI.

---

## 6. Document ID Conventions

| Collection | ID Strategy | Format / Example |
|---|---|---|
| `departments` | Auto-ID (Firestore auto `push` ID) | `dep_8sK2n...` prefixed via app logic OR raw auto-ID |
| `employees` | **Same as Firebase Auth UID** | `uid` from Firebase Auth |
| `roles` | Human-readable slug (backend-controlled) | `role_admin`, `role_manager`, `role_employee` |
| `permissions` | Human-readable slug | `perm_asset_create`, `perm_booking_approve` |
| `assetCategories` | Auto-ID | Firestore auto-ID |
| `assets` | App-generated Asset Tag as ID | `AST-000123` (see Section 8.2 for generation rule) |
| `assetAllocations` | Auto-ID | Firestore auto-ID |
| `sharedResources` | App-generated Resource Code as ID | `RES-000045` |
| `resourceBookings` | Auto-ID | Firestore auto-ID |
| `maintenanceRequests` | App-generated Request Number as ID | `MR-2026-00042` |
| `maintenanceRequests/{id}/approvals` | Auto-ID | Firestore auto-ID |
| `maintenanceRequests/{id}/logs` | Auto-ID | Firestore auto-ID |
| `auditCycles` | App-generated Cycle Code as ID | `AC-2026-Q3` |
| `auditCycles/{id}/reports` | Auto-ID | Firestore auto-ID |
| `notifications` | Auto-ID | Firestore auto-ID |
| `dashboardAggregates` | Fixed known keys (singleton docs) | `global_kpis`, `dept_{departmentId}`, `daily_{YYYY-MM-DD}` |
| `auditLogs` (system audit trail) | Auto-ID | Firestore auto-ID |
| `counters` | Fixed known keys | `assets`, `resources`, `maintenanceRequests`, `auditCycles` |

**Rule:** Use human-meaningful IDs (Asset Tag, Resource Code, Request Number, Cycle Code) **only** where the ID itself is a business-facing identifier users will search/type/reference. Use Firestore auto-IDs everywhere else to avoid collision-handling complexity.

---

## 7. Complete Firestore Collection Tree

```
firestore-root/
│
├── departments/{departmentId}
│
├── employees/{employeeId}                          (employeeId == Firebase Auth UID)
│
├── roles/{roleId}
│
├── permissions/{permissionId}
│
├── assetCategories/{categoryId}
│
├── assets/{assetId}                                 (assetId == Asset Tag, e.g. AST-000123)
│
├── assetAllocations/{allocationId}
│
├── sharedResources/{resourceId}                     (resourceId == Resource Code, e.g. RES-000045)
│
├── resourceBookings/{bookingId}
│
├── maintenanceRequests/{requestId}                  (requestId == Request Number, e.g. MR-2026-00042)
│   ├── approvals/{approvalId}
│   └── logs/{logId}
│
├── auditCycles/{cycleId}                            (cycleId == Cycle Code, e.g. AC-2026-Q3)
│   └── reports/{reportId}
│
├── notifications/{notificationId}
│
├── dashboardAggregates/{aggregateId}                 (singleton/keyed docs, e.g. global_kpis, dept_{id})
│
├── auditLogs/{logId}                                 (system-wide immutable change trail, distinct from auditCycles)
│
└── counters/{counterId}                              (server-side atomic ID/sequence generators)
```

---

## 8. Relationships & Reference Strategy

### 8.1 General Rule
- Every reference field is named `<entity>Id` (e.g., `departmentId`, `employeeId`, `assetId`) and stores the **string Document ID** of the referenced document.
- Where the UI needs to display referenced info without an extra read, a **denormalized snapshot object** is stored alongside, named `<entity>Snapshot`, containing only display-relevant fields (name, code, avatar/imageUrl). Snapshots are refreshed by the backend whenever the source document's relevant fields change (via Cloud Function trigger on the source collection), or lazily on next write — never assumed to be real-time-perfect; the referenced document remains the source of truth.
- Full DocumentReference objects are **not used** — plain string IDs only, for backend-language portability and simpler security rules.

### 8.2 ID Generation for Business IDs
Business-facing sequential IDs (`AST-000123`, `RES-000045`, `MR-2026-00042`, `AC-2026-Q3`) are generated via the `counters/{counterId}` collection using a Firestore transaction: read current value → increment → write → format string. This guarantees uniqueness without collisions under concurrent writes.

`counters` document shape:
```json
{
  "value": 123,
  "prefix": "AST",
  "padding": 6,
  "updatedAt": "<timestamp>"
}
```

### 8.3 Relationship Map

| From | To | Cardinality | Field |
|---|---|---|---|
| employees | departments | N:1 | `employees.departmentId` |
| employees | roles | N:1 | `employees.roleId` |
| roles | permissions | N:M | `roles.permissionIds[]` (array of permission IDs; roles have few permissions, bounded array is safe) |
| assets | assetCategories | N:1 | `assets.categoryId` |
| assets | departments | N:1 | `assets.departmentId` (owning department) |
| assetAllocations | assets | N:1 | `assetAllocations.assetId` |
| assetAllocations | employees | N:1 | `assetAllocations.employeeId` |
| resourceBookings | sharedResources | N:1 | `resourceBookings.resourceId` |
| resourceBookings | employees | N:1 | `resourceBookings.employeeId` |
| maintenanceRequests | assets | N:1 | `maintenanceRequests.assetId` |
| maintenanceRequests | employees | N:1 (requester) | `maintenanceRequests.requestedBy` |
| maintenanceRequests/approvals | employees | N:1 (approver) | `approvals.approverId` |
| maintenanceRequests/logs | employees | N:1 (actor) | `logs.performedBy` |
| auditCycles | departments | N:M | `auditCycles.departmentIds[]` (scope of audit) |
| auditCycles/reports | assets | N:1 | `reports.assetId` |
| auditCycles/reports | employees | N:1 (auditor) | `reports.auditedBy` |
| notifications | employees | N:1 (recipient) | `notifications.recipientId` |

### 8.4 Why Subcollections for Approvals/Logs/Reports
`approvals`, `logs`, and `reports` are always fetched **in the context of their parent** (a specific maintenance request or audit cycle), are unbounded in count over time, and never need cross-parent querying at scale that a top-level `collectionGroup` query can't solve. Firestore **Collection Group Queries** are used when cross-parent querying IS needed (e.g., "all logs performed by employee X across all maintenance requests" uses `db.collection_group('logs').where('performedBy', '==', x)`).

---

## 9. Index Strategy

### 9.1 Single-field indexes
Firestore auto-creates single-field indexes for every field by default — no manual declaration needed for simple equality/range/orderBy on one field.

### 9.2 Required Composite Indexes (`firestore.indexes.json`)

| Collection | Fields (in order) | Purpose |
|---|---|---|
| `employees` | `departmentId ASC, status ASC, fullName ASC` | List active employees per department, sorted |
| `assets` | `departmentId ASC, status ASC, updatedAt DESC` | Department asset lists |
| `assets` | `categoryId ASC, status ASC, createdAt DESC` | Category-filtered asset lists |
| `assets` | `status ASC, isDeleted ASC, assetTag ASC` | Global asset search excluding deleted |
| `assetAllocations` | `assetId ASC, status ASC, allocatedAt DESC` | Allocation history per asset |
| `assetAllocations` | `employeeId ASC, status ASC, allocatedAt DESC` | Allocation history per employee |
| `resourceBookings` | `resourceId ASC, status ASC, startTime ASC` | Availability/conflict check per resource |
| `resourceBookings` | `employeeId ASC, startTime DESC` | "My bookings" |
| `resourceBookings` | `status ASC, startTime ASC` | Upcoming bookings dashboard |
| `maintenanceRequests` | `assetId ASC, status ASC, createdAt DESC` | Maintenance history per asset |
| `maintenanceRequests` | `status ASC, priority DESC, createdAt ASC` | Maintenance queue (triage view) |
| `maintenanceRequests` | `requestedBy ASC, status ASC, createdAt DESC` | "My requests" |
| `auditCycles` | `status ASC, scheduledStart ASC` | Active/upcoming audit cycles |
| `auditCycles/reports` (collection group) | `assetId ASC, auditedAt DESC` | Audit history per asset |
| `notifications` | `recipientId ASC, isRead ASC, createdAt DESC` | Inbox unread-first list |
| `auditLogs` | `entityType ASC, entityId ASC, createdAt DESC` | Change history per entity |
| `auditLogs` | `performedBy ASC, createdAt DESC` | Activity by user |

### 9.3 Search Fields
Firestore has no native full-text search. This project uses:
- **Prefix search** on indexed string fields (e.g., `assetTag`, `fullName`, `resourceCode`) using range queries (`>=` value `<=` value + `\uf8ff`), for simple "starts with" search boxes.
- For true full-text/fuzzy search (e.g., searching asset descriptions), the backend integrates **Algolia or Typesense** (or Elasticsearch) synced via Cloud Functions on document write. This document only defines the Firestore-side data model; search-index sync is a backend responsibility mirroring the collections in Section 7 for: `assets`, `employees`, `sharedResources`, `maintenanceRequests`.

### 9.4 Filter Fields (per collection, defined per-collection in Section 10)
Every collection's `status` and relevant enum fields are always indexed for filtering — declared explicitly in each field table below.

### 9.5 Sort Fields
Default sort per collection is documented in Section 10 per-collection ("Default Sort" row). All sortable fields are Timestamp or short indexed strings — never unindexed computed fields.

---

## 10. Collections — Full Field Definitions

> Legend: **R** = Required, **O** = Optional. All documents include the **Standard Audit Fields** block from Section 12 unless noted otherwise — shown once here and referenced thereafter as `[STANDARD_AUDIT_FIELDS]`.

### 10.0 Standard Audit Fields (embedded in nearly every document)
| Field | Type | R/O | Default | Notes |
|---|---|---|---|---|
| `createdAt` | Timestamp | R | `SERVER_TIMESTAMP` | Set once, immutable |
| `updatedAt` | Timestamp | R | `SERVER_TIMESTAMP` | Updated on every write |
| `createdBy` | string (employeeId) | R | — | UID of creator |
| `updatedBy` | string (employeeId) | R | — | UID of last modifier |
| `isDeleted` | boolean | R | `false` | Soft-delete flag (Section 11) |
| `deletedAt` | Timestamp \| null | O | `null` | Set when soft-deleted |
| `deletedBy` | string (employeeId) \| null | O | `null` | Who soft-deleted |

---

### 10.1 `departments/{departmentId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `name` | string | R | — | 2–100 chars, unique (enforced by backend pre-check) |
| `code` | string | R | — | Uppercase, 2–10 chars, unique, e.g. `"ENG"` |
| `description` | string | O | `""` | max 1000 chars |
| `headEmployeeId` | string \| null | O | `null` | must reference existing `employees` doc |
| `status` | string (enum) | R | `"active"` | `["active", "inactive"]` |
| `employeeCount` | number | R | `0` | denormalized counter, updated via Cloud Function trigger on employee create/delete |
| `assetCount` | number | R | `0` | denormalized counter |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `status`. **Sort fields:** `name ASC` (default), `createdAt DESC`. **Search fields:** `name`, `code` (prefix search).

**Example JSON:**
```json
{
  "name": "Engineering",
  "code": "ENG",
  "description": "Software and hardware engineering department",
  "headEmployeeId": "uid_abc123",
  "status": "active",
  "employeeCount": 42,
  "assetCount": 118,
  "createdAt": "2026-01-10T09:00:00Z",
  "updatedAt": "2026-06-01T11:20:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_admin001",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.2 `employees/{employeeId}`
`employeeId` MUST equal the Firebase Auth UID.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `fullName` | string | R | — | 2–150 chars |
| `email` | string | R | — | valid email format, unique |
| `phone` | string | O | `""` | E.164 format preferred |
| `avatarUrl` | string \| null | O | `null` | Firebase Storage URL |
| `departmentId` | string | R | — | must reference `departments` |
| `departmentSnapshot` | map | R | — | `{ "name": string, "code": string }` denormalized |
| `roleId` | string | R | — | must reference `roles` |
| `roleSnapshot` | map | R | — | `{ "name": string }` denormalized |
| `designation` | string | O | `""` | job title, max 100 chars |
| `employeeCode` | string | R | — | unique, e.g. `"EMP-00231"` (generated via `counters`) |
| `joinDate` | Timestamp | R | — | — |
| `status` | string (enum) | R | `"active"` | `["active", "on_leave", "suspended", "inactive"]` |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `departmentId`, `roleId`, `status`. **Sort fields:** `fullName ASC` (default), `joinDate DESC`. **Search fields:** `fullName`, `email`, `employeeCode` (prefix search; fuzzy search via external index).

**Relationships:** owns `assetAllocations` (as `employeeId`), `resourceBookings` (as `employeeId`), `maintenanceRequests` (as `requestedBy`), `notifications` (as `recipientId`).

**Example JSON:**
```json
{
  "fullName": "Priya Sharma",
  "email": "priya.sharma@company.com",
  "phone": "+919876543210",
  "avatarUrl": "https://storage.googleapis.com/.../avatars/uid_abc123.jpg",
  "departmentId": "dep_eng001",
  "departmentSnapshot": { "name": "Engineering", "code": "ENG" },
  "roleId": "role_manager",
  "roleSnapshot": { "name": "Manager" },
  "designation": "Engineering Manager",
  "employeeCode": "EMP-00231",
  "joinDate": "2023-04-15T00:00:00Z",
  "status": "active",
  "createdAt": "2023-04-15T09:00:00Z",
  "updatedAt": "2026-05-20T10:00:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_hr002",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.3 `roles/{roleId}`
`roleId` is a controlled slug (e.g., `role_admin`).

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `name` | string | R | — | 2–50 chars, unique |
| `description` | string | O | `""` | max 500 chars |
| `permissionIds` | array\<string\> | R | `[]` | each must reference `permissions`; bounded (< 200 items expected) |
| `isSystemRole` | boolean | R | `false` | `true` for built-in roles (admin/manager/employee) that cannot be deleted |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `isSystemRole`. **Sort fields:** `name ASC`.

**Example JSON:**
```json
{
  "name": "Manager",
  "description": "Department managers with approval rights",
  "permissionIds": ["perm_asset_view", "perm_asset_allocate", "perm_maintenance_approve"],
  "isSystemRole": true,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "createdBy": "system",
  "updatedBy": "system",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.4 `permissions/{permissionId}`
`permissionId` is a controlled slug (e.g., `perm_asset_create`).

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `key` | string | R | — | machine key, e.g. `"asset.create"`, unique |
| `label` | string | R | — | human-readable, e.g. `"Create Asset"` |
| `module` | string (enum) | R | — | `["department","employee","role","asset","allocation","resource","booking","maintenance","audit","notification","dashboard"]` |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | (no `isDeleted` lifecycle needed in practice, but field present for consistency) |

**Filter fields:** `module`. **Sort fields:** `module ASC, key ASC`.

**Example JSON:**
```json
{
  "key": "maintenance.approve",
  "label": "Approve Maintenance Request",
  "module": "maintenance",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "createdBy": "system",
  "updatedBy": "system",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.5 `assetCategories/{categoryId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `name` | string | R | — | 2–100 chars, unique |
| `code` | string | R | — | uppercase 2–10 chars, unique |
| `description` | string | O | `""` | max 1000 chars |
| `parentCategoryId` | string \| null | O | `null` | self-reference to `assetCategories` for hierarchy (1 level deep max recommended) |
| `depreciationMethod` | string (enum) | O | `"straight_line"` | `["straight_line", "declining_balance", "none"]` |
| `defaultUsefulLifeMonths` | number | O | `36` | integer, > 0 |
| `assetCount` | number | R | `0` | denormalized counter |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `parentCategoryId`. **Sort fields:** `name ASC`.

**Example JSON:**
```json
{
  "name": "Laptops",
  "code": "LAP",
  "description": "Portable computers",
  "parentCategoryId": "cat_electronics",
  "depreciationMethod": "straight_line",
  "defaultUsefulLifeMonths": 36,
  "assetCount": 87,
  "createdAt": "2026-01-05T00:00:00Z",
  "updatedAt": "2026-01-05T00:00:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_admin001",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.6 `assets/{assetId}`
`assetId` = Asset Tag (e.g., `AST-000123`), generated via `counters/assets`.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `assetTag` | string | R | — | equals document ID, immutable |
| `name` | string | R | — | 2–150 chars |
| `categoryId` | string | R | — | must reference `assetCategories` |
| `categorySnapshot` | map | R | — | `{ "name": string, "code": string }` |
| `departmentId` | string | R | — | owning department; must reference `departments` |
| `departmentSnapshot` | map | R | — | `{ "name": string, "code": string }` |
| `serialNumber` | string | O | `""` | manufacturer serial |
| `manufacturer` | string | O | `""` | max 100 chars |
| `model` | string | O | `""` | max 100 chars |
| `purchaseDate` | Timestamp \| null | O | `null` | — |
| `purchaseCost` | number | O | `0` | >= 0, currency in base unit (e.g., cents) — see note below |
| `currency` | string | O | `"USD"` | ISO 4217 code |
| `warrantyExpiryDate` | Timestamp \| null | O | `null` | — |
| `location` | string | O | `""` | free text or site code |
| `imageUrls` | array\<string\> | O | `[]` | Firebase Storage URLs, max 10 |
| `status` | string (enum) | R | `"available"` | `["available", "allocated", "in_maintenance", "retired", "lost"]` |
| `condition` | string (enum) | R | `"good"` | `["new", "good", "fair", "poor", "damaged"]` |
| `currentAllocationId` | string \| null | O | `null` | denormalized pointer to active `assetAllocations` doc when `status == "allocated"` |
| `currentHolderSnapshot` | map \| null | O | `null` | `{ "employeeId": string, "fullName": string }` when allocated |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

*Note on money fields:* All monetary fields (`purchaseCost`, etc., across this document) are stored as **integers in the smallest currency unit** (e.g., cents) to avoid floating-point rounding errors, and formatted to decimal only at the presentation layer.

**Filter fields:** `categoryId`, `departmentId`, `status`, `condition`. **Sort fields:** `assetTag ASC` (default), `createdAt DESC`, `purchaseDate DESC`. **Search fields:** `assetTag`, `name`, `serialNumber` (prefix; fuzzy via external index).

**Example JSON:**
```json
{
  "assetTag": "AST-000123",
  "name": "Dell Latitude 5440",
  "categoryId": "cat_laptops",
  "categorySnapshot": { "name": "Laptops", "code": "LAP" },
  "departmentId": "dep_eng001",
  "departmentSnapshot": { "name": "Engineering", "code": "ENG" },
  "serialNumber": "SN-88213X",
  "manufacturer": "Dell",
  "model": "Latitude 5440",
  "purchaseDate": "2025-11-01T00:00:00Z",
  "purchaseCost": 125000,
  "currency": "USD",
  "warrantyExpiryDate": "2028-11-01T00:00:00Z",
  "location": "HQ - Floor 3",
  "imageUrls": ["https://storage.googleapis.com/.../assets/AST-000123-1.jpg"],
  "status": "allocated",
  "condition": "good",
  "currentAllocationId": "alloc_9f8e7d",
  "currentHolderSnapshot": { "employeeId": "uid_abc123", "fullName": "Priya Sharma" },
  "createdAt": "2025-11-02T09:00:00Z",
  "updatedAt": "2026-06-10T14:00:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_manager002",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.7 `assetAllocations/{allocationId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `assetId` | string | R | — | must reference `assets` |
| `assetSnapshot` | map | R | — | `{ "assetTag": string, "name": string }` |
| `employeeId` | string | R | — | must reference `employees` |
| `employeeSnapshot` | map | R | — | `{ "fullName": string, "employeeCode": string }` |
| `allocatedAt` | Timestamp | R | `SERVER_TIMESTAMP` | — |
| `expectedReturnDate` | Timestamp \| null | O | `null` | must be >= `allocatedAt` if set |
| `returnedAt` | Timestamp \| null | O | `null` | set on return |
| `status` | string (enum) | R | `"active"` | `["active", "returned", "overdue", "lost"]` |
| `conditionAtAllocation` | string (enum) | R | — | same enum as `assets.condition` |
| `conditionAtReturn` | string (enum) \| null | O | `null` | same enum, set on return |
| `notes` | string | O | `""` | max 1000 chars |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `assetId`, `employeeId`, `status`. **Sort fields:** `allocatedAt DESC` (default).

**Business rule:** Only one `assetAllocations` document with `status == "active"` may exist per `assetId` at a time (enforced via Firestore transaction that checks the asset's `status` field before creating a new allocation).

**Example JSON:**
```json
{
  "assetId": "AST-000123",
  "assetSnapshot": { "assetTag": "AST-000123", "name": "Dell Latitude 5440" },
  "employeeId": "uid_abc123",
  "employeeSnapshot": { "fullName": "Priya Sharma", "employeeCode": "EMP-00231" },
  "allocatedAt": "2026-06-10T14:00:00Z",
  "expectedReturnDate": null,
  "returnedAt": null,
  "status": "active",
  "conditionAtAllocation": "good",
  "conditionAtReturn": null,
  "notes": "Allocated for new hire onboarding",
  "createdAt": "2026-06-10T14:00:00Z",
  "updatedAt": "2026-06-10T14:00:00Z",
  "createdBy": "uid_manager002",
  "updatedBy": "uid_manager002",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.8 `sharedResources/{resourceId}`
`resourceId` = Resource Code (e.g., `RES-000045`), generated via `counters/resources`. Represents bookable shared assets like conference rooms, projectors, vehicles.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `resourceCode` | string | R | — | equals document ID |
| `name` | string | R | — | 2–150 chars |
| `type` | string (enum) | R | — | `["conference_room", "vehicle", "equipment", "other"]` |
| `capacity` | number \| null | O | `null` | integer > 0, relevant for rooms/vehicles |
| `location` | string | O | `""` | — |
| `amenities` | array\<string\> | O | `[]` | free-form tags, e.g. `["projector","whiteboard"]` |
| `imageUrls` | array\<string\> | O | `[]` | max 10 |
| `status` | string (enum) | R | `"active"` | `["active", "under_maintenance", "inactive"]` |
| `bookingRules` | map | O | see below | `{ "minDurationMinutes": number, "maxDurationMinutes": number, "advanceBookingDays": number }` defaults: `{60, 480, 30}` |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `type`, `status`. **Sort fields:** `name ASC` (default). **Search fields:** `name`, `resourceCode`.

**Example JSON:**
```json
{
  "resourceCode": "RES-000045",
  "name": "Conference Room Alpha",
  "type": "conference_room",
  "capacity": 12,
  "location": "HQ - Floor 2",
  "amenities": ["projector", "whiteboard", "video_conf"],
  "imageUrls": [],
  "status": "active",
  "bookingRules": { "minDurationMinutes": 30, "maxDurationMinutes": 240, "advanceBookingDays": 30 },
  "createdAt": "2026-01-15T00:00:00Z",
  "updatedAt": "2026-01-15T00:00:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_admin001",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.9 `resourceBookings/{bookingId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `resourceId` | string | R | — | must reference `sharedResources` |
| `resourceSnapshot` | map | R | — | `{ "resourceCode": string, "name": string }` |
| `employeeId` | string | R | — | must reference `employees` (booked by) |
| `employeeSnapshot` | map | R | — | `{ "fullName": string }` |
| `title` | string | R | — | 2–200 chars, purpose of booking |
| `startTime` | Timestamp | R | — | must be < `endTime` |
| `endTime` | Timestamp | R | — | must be > `startTime`, and duration within resource's `bookingRules` |
| `attendeeIds` | array\<string\> | O | `[]` | list of `employees` IDs, bounded (< 100) |
| `status` | string (enum) | R | `"confirmed"` | `["confirmed", "cancelled", "completed"]` |
| `cancellationReason` | string \| null | O | `null` | required if `status == "cancelled"` |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `resourceId`, `employeeId`, `status`. **Sort fields:** `startTime ASC` (default for upcoming), `startTime DESC` (for history).

**Business rule (conflict prevention):** Before creating/updating a booking, backend runs a query on `resourceBookings` filtered by `resourceId == X AND status == "confirmed"` and checks for time-range overlap in application code (Firestore cannot do range-overlap queries natively), executed inside a transaction to prevent race conditions on the same resource.

**Example JSON:**
```json
{
  "resourceId": "RES-000045",
  "resourceSnapshot": { "resourceCode": "RES-000045", "name": "Conference Room Alpha" },
  "employeeId": "uid_abc123",
  "employeeSnapshot": { "fullName": "Priya Sharma" },
  "title": "Sprint Planning",
  "startTime": "2026-07-15T09:00:00Z",
  "endTime": "2026-07-15T10:30:00Z",
  "attendeeIds": ["uid_def456", "uid_ghi789"],
  "status": "confirmed",
  "cancellationReason": null,
  "createdAt": "2026-07-01T08:00:00Z",
  "updatedAt": "2026-07-01T08:00:00Z",
  "createdBy": "uid_abc123",
  "updatedBy": "uid_abc123",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.10 `maintenanceRequests/{requestId}`
`requestId` = Request Number (e.g., `MR-2026-00042`), generated via `counters/maintenanceRequests`.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `requestNumber` | string | R | — | equals document ID |
| `assetId` | string | R | — | must reference `assets` |
| `assetSnapshot` | map | R | — | `{ "assetTag": string, "name": string }` |
| `requestedBy` | string | R | — | must reference `employees` |
| `requestedBySnapshot` | map | R | — | `{ "fullName": string }` |
| `issueDescription` | string | R | — | 10–5000 chars |
| `priority` | string (enum) | R | `"medium"` | `["low", "medium", "high", "critical"]` |
| `status` | string (enum) | R | `"pending_approval"` | `["pending_approval", "approved", "rejected", "in_progress", "completed", "cancelled"]` |
| `assignedTechnicianId` | string \| null | O | `null` | must reference `employees` if set |
| `assignedTechnicianSnapshot` | map \| null | O | `null` | `{ "fullName": string }` |
| `estimatedCost` | number \| null | O | `null` | integer, smallest currency unit, >= 0 |
| `actualCost` | number \| null | O | `null` | integer, smallest currency unit, >= 0 |
| `attachmentUrls` | array\<string\> | O | `[]` | max 10, Firebase Storage URLs |
| `completedAt` | Timestamp \| null | O | `null` | set when `status == "completed"` |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `assetId`, `requestedBy`, `status`, `priority`, `assignedTechnicianId`. **Sort fields:** `createdAt DESC` (default), `priority DESC` (triage queue).

#### 10.10.1 Subcollection: `maintenanceRequests/{requestId}/approvals/{approvalId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `approverId` | string | R | — | must reference `employees`, must hold `perm_maintenance_approve` |
| `approverSnapshot` | map | R | — | `{ "fullName": string }` |
| `decision` | string (enum) | R | — | `["approved", "rejected"]` |
| `comments` | string | O | `""` | max 1000 chars |
| `decidedAt` | Timestamp | R | `SERVER_TIMESTAMP` | — |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | (immutable record — `updatedAt`/`updatedBy` typically equal created values) |

#### 10.10.2 Subcollection: `maintenanceRequests/{requestId}/logs/{logId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `action` | string (enum) | R | — | `["created", "approved", "rejected", "assigned", "status_changed", "commented", "completed", "cancelled"]` |
| `performedBy` | string | R | — | must reference `employees` |
| `performedBySnapshot` | map | R | — | `{ "fullName": string }` |
| `details` | string | O | `""` | max 2000 chars, free text description of the change |
| `previousStatus` | string \| null | O | `null` | for `status_changed` actions |
| `newStatus` | string \| null | O | `null` | for `status_changed` actions |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | append-only, immutable |

**Example JSON (maintenanceRequests document):**
```json
{
  "requestNumber": "MR-2026-00042",
  "assetId": "AST-000123",
  "assetSnapshot": { "assetTag": "AST-000123", "name": "Dell Latitude 5440" },
  "requestedBy": "uid_abc123",
  "requestedBySnapshot": { "fullName": "Priya Sharma" },
  "issueDescription": "Laptop screen flickers intermittently.",
  "priority": "high",
  "status": "in_progress",
  "assignedTechnicianId": "uid_tech001",
  "assignedTechnicianSnapshot": { "fullName": "Ravi Kumar" },
  "estimatedCost": 5000,
  "actualCost": null,
  "attachmentUrls": [],
  "completedAt": null,
  "createdAt": "2026-06-20T10:00:00Z",
  "updatedAt": "2026-06-21T09:00:00Z",
  "createdBy": "uid_abc123",
  "updatedBy": "uid_tech001",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.11 `auditCycles/{cycleId}`
`cycleId` = Cycle Code (e.g., `AC-2026-Q3`). Represents periodic physical/verification audits of assets (distinct from the system `auditLogs` change trail).

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `cycleCode` | string | R | — | equals document ID |
| `name` | string | R | — | 2–150 chars, e.g. "Q3 2026 Asset Verification" |
| `departmentIds` | array\<string\> | R | `[]` | scope of departments included; each must reference `departments` |
| `categoryIds` | array\<string\> | O | `[]` | optional scope narrowing by category |
| `scheduledStart` | Timestamp | R | — | — |
| `scheduledEnd` | Timestamp | R | — | must be >= `scheduledStart` |
| `actualEnd` | Timestamp \| null | O | `null` | set when cycle closed |
| `status` | string (enum) | R | `"planned"` | `["planned", "in_progress", "completed", "cancelled"]` |
| `assignedAuditorIds` | array\<string\> | R | `[]` | must reference `employees` |
| `totalAssetsInScope` | number | R | `0` | denormalized, computed at cycle start |
| `assetsAudited` | number | R | `0` | denormalized counter, incremented as `reports` are added |
| `discrepanciesFound` | number | R | `0` | denormalized counter |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | — |

**Filter fields:** `status`. **Sort fields:** `scheduledStart ASC` (default upcoming), `scheduledStart DESC` (history).

#### 10.11.1 Subcollection: `auditCycles/{cycleId}/reports/{reportId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `assetId` | string | R | — | must reference `assets` |
| `assetSnapshot` | map | R | — | `{ "assetTag": string, "name": string }` |
| `auditedBy` | string | R | — | must reference `employees` |
| `auditedBySnapshot` | map | R | — | `{ "fullName": string }` |
| `auditedAt` | Timestamp | R | `SERVER_TIMESTAMP` | — |
| `expectedLocation` | string | O | `""` | from asset record at audit time |
| `actualLocation` | string | O | `""` | as found |
| `expectedCondition` | string (enum) | O | — | asset condition enum, snapshot at audit time |
| `actualCondition` | string (enum) | R | — | asset condition enum |
| `found` | boolean | R | `true` | `false` if asset could not be located |
| `discrepancyNotes` | string | O | `""` | max 2000 chars, required if `found == false` or condition mismatch |
| `photoUrls` | array\<string\> | O | `[]` | max 10, evidence photos |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | append-only, immutable |

**Example JSON (auditCycles document):**
```json
{
  "cycleCode": "AC-2026-Q3",
  "name": "Q3 2026 Asset Verification",
  "departmentIds": ["dep_eng001", "dep_fin002"],
  "categoryIds": ["cat_laptops"],
  "scheduledStart": "2026-07-01T00:00:00Z",
  "scheduledEnd": "2026-07-15T00:00:00Z",
  "actualEnd": null,
  "status": "in_progress",
  "assignedAuditorIds": ["uid_aud001"],
  "totalAssetsInScope": 205,
  "assetsAudited": 140,
  "discrepanciesFound": 6,
  "createdAt": "2026-06-15T00:00:00Z",
  "updatedAt": "2026-07-10T00:00:00Z",
  "createdBy": "uid_admin001",
  "updatedBy": "uid_aud001",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.12 `notifications/{notificationId}`

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `recipientId` | string | R | — | must reference `employees` |
| `type` | string (enum) | R | — | `["allocation_assigned","allocation_due","maintenance_status_change","maintenance_approval_needed","booking_confirmed","booking_cancelled","audit_assigned","audit_discrepancy","system"]` |
| `title` | string | R | — | 2–150 chars |
| `body` | string | R | — | max 1000 chars |
| `relatedEntityType` | string (enum) \| null | O | `null` | `["asset","allocation","resource","booking","maintenanceRequest","auditCycle",null]` |
| `relatedEntityId` | string \| null | O | `null` | ID of related doc, for deep-linking |
| `isRead` | boolean | R | `false` | — |
| `readAt` | Timestamp \| null | O | `null` | — |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | (`isDeleted` here means user-dismissed/cleared) |

**Filter fields:** `recipientId`, `isRead`, `type`. **Sort fields:** `createdAt DESC` (default).

**Example JSON:**
```json
{
  "recipientId": "uid_abc123",
  "type": "maintenance_status_change",
  "title": "Maintenance Request Updated",
  "body": "Your maintenance request MR-2026-00042 is now In Progress.",
  "relatedEntityType": "maintenanceRequest",
  "relatedEntityId": "MR-2026-00042",
  "isRead": false,
  "readAt": null,
  "createdAt": "2026-06-21T09:00:05Z",
  "updatedAt": "2026-06-21T09:00:05Z",
  "createdBy": "system",
  "updatedBy": "system",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.13 `dashboardAggregates/{aggregateId}`
Precomputed KPI documents, updated incrementally by backend Cloud Functions/transactions whenever source data changes (never computed live by scanning collections). See Section 18 for full strategy.

Known keys: `global_kpis`, `dept_{departmentId}`, `daily_{YYYY-MM-DD}`.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `scope` | string (enum) | R | — | `["global", "department", "daily"]` |
| `scopeRefId` | string \| null | O | `null` | `departmentId` if `scope == "department"`, date string if `daily` |
| `totalAssets` | number | R | `0` | — |
| `assetsByStatus` | map\<string, number\> | R | `{}` | keys are `assets.status` enum values |
| `totalActiveAllocations` | number | R | `0` | — |
| `totalOverdueAllocations` | number | R | `0` | — |
| `totalBookingsToday` | number | R | `0` | — |
| `openMaintenanceRequests` | number | R | `0` | — |
| `maintenanceByPriority` | map\<string, number\> | R | `{}` | keys are `priority` enum values |
| `auditComplianceRate` | number | R | `0` | percentage 0–100, computed from latest completed cycle(s) |
| `pendingNotificationsCount` | number | R | `0` | org-wide unread count, `daily`/`global` scope only |
| `lastComputedAt` | Timestamp | R | `SERVER_TIMESTAMP` | — |
| `[STANDARD_AUDIT_FIELDS]` | — | — | — | `createdBy`/`updatedBy` = `"system"` |

**Example JSON:**
```json
{
  "scope": "global",
  "scopeRefId": null,
  "totalAssets": 1240,
  "assetsByStatus": { "available": 610, "allocated": 540, "in_maintenance": 70, "retired": 18, "lost": 2 },
  "totalActiveAllocations": 540,
  "totalOverdueAllocations": 12,
  "totalBookingsToday": 27,
  "openMaintenanceRequests": 34,
  "maintenanceByPriority": { "low": 10, "medium": 15, "high": 7, "critical": 2 },
  "auditComplianceRate": 92.5,
  "pendingNotificationsCount": 318,
  "lastComputedAt": "2026-07-12T06:00:00Z",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-07-12T06:00:00Z",
  "createdBy": "system",
  "updatedBy": "system",
  "isDeleted": false,
  "deletedAt": null,
  "deletedBy": null
}
```

---

### 10.14 `auditLogs/{logId}`
System-wide immutable change trail across ALL collections (technical audit trail — not to be confused with the `auditCycles` business module). Written by backend on every create/update/delete of any tracked document.

| Field | Type | R/O | Default | Validation |
|---|---|---|---|---|
| `entityType` | string | R | — | collection name, e.g. `"assets"` |
| `entityId` | string | R | — | document ID affected |
| `action` | string (enum) | R | — | `["create", "update", "delete", "soft_delete", "restore"]` |
| `performedBy` | string | R | — | must reference `employees`, or `"system"` |
| `changedFields` | array\<string\> | O | `[]` | list of top-level field names changed (for `update` actions) |
| `beforeSnapshot` | map \| null | O | `null` | prior state of changed fields only (not full doc, to bound size) |
| `afterSnapshot` | map \| null | O | `null` | new state of changed fields only |
| `createdAt` | Timestamp | R | `SERVER_TIMESTAMP` | append-only, no `updatedAt` |
| `ipAddress` | string \| null | O | `null` | for security forensics |

**Filter fields:** `entityType`, `entityId`, `performedBy`. **Sort fields:** `createdAt DESC` (default). Queried via direct path filters and collection-level indexes (Section 9.2).

---

### 10.15 `counters/{counterId}`
See Section 8.2. Internal-only collection, never exposed via API list endpoints, write-access restricted to backend service account only.

---

## 11. Soft Delete & Archive Strategy

1. **Soft delete only** for any document that could realistically be referenced elsewhere: `departments`, `employees`, `assetCategories`, `assets`, `sharedResources`, `roles`, `permissions`.
   - Sets `isDeleted = true`, `deletedAt = SERVER_TIMESTAMP`, `deletedBy = <uid>`.
   - Soft-deleted documents are excluded from all default list queries via `.where("isDeleted", "==", false)` — this is why `isDeleted` is part of every relevant composite index (Section 9.2).
   - Soft-deleted documents remain fetchable by direct ID for historical record display (e.g., showing an old allocation still shows the (deleted) asset's last known name via its `assetSnapshot`).
2. **Hard delete permitted only** for: `notifications` (user-cleared, non-business-critical) and truly erroneous documents created by bugs/duplicate submissions within the same session (admin-only tool, logged to `auditLogs` regardless).
3. **Archival (not deletion)** applies to time-bound transactional records once they are old and closed:
   - `resourceBookings` with `status == "completed"` or `"cancelled"` older than 18 months.
   - `maintenanceRequests` with `status == "completed"` or `"cancelled"` older than 24 months.
   - `notifications` with `isRead == true` older than 6 months.
   - Archival is implemented as a scheduled Cloud Function that **moves** matching documents into a parallel `..._archive` top-level collection (e.g., `resourceBookingsArchive`) with identical schema, then hard-deletes the original — keeping primary collections lean for query performance while preserving full historical data for compliance/reporting.
4. **Restoration:** Soft-deleted documents can be restored (`isDeleted = false`, clear `deletedAt`/`deletedBy`) by an admin; this action is logged to `auditLogs` with `action: "restore"`.

---

## 12. Timestamp Strategy & createdBy/updatedBy Conventions

- All timestamps use the Firestore native `Timestamp` type, set server-side (`firestore.SERVER_TIMESTAMP` in the Python Admin SDK) — client-supplied timestamps are always rejected/overwritten by the backend.
- `createdAt` is set exactly once, at document creation, and never modified thereafter.
- `updatedAt` is set on every subsequent write (including soft-delete/restore actions).
- `createdBy`/`updatedBy` store the `employeeId` (== Firebase Auth UID) of the acting user, taken from the verified Firebase ID token on the backend request — **never trusted from client-submitted payload**.
- System-initiated writes (Cloud Function triggers, scheduled jobs, aggregate recomputation) use the literal string `"system"` for `createdBy`/`updatedBy`.
- Append-only child documents (`approvals`, `logs`, audit `reports`, `auditLogs`) typically only need `createdAt`/`createdBy` semantically, but still carry the full standard block for consistency; `updatedAt`/`updatedBy` simply equal the creation values since these documents are immutable after write.

---

## 13. Validation Rules Summary (Cross-Cutting)

- **String length limits** are enforced as stated per field above; backend rejects with a 400-equivalent error before any Firestore write is attempted.
- **Enum fields** are validated against the exact value lists in this document on both the Python backend (Pydantic models with `Literal`/`Enum` types recommended) and Firestore Security Rules.
- **Reference integrity:** Before writing a document containing a reference field (e.g., `departmentId`), backend performs a existence-check read of the referenced document (or relies on a Firestore transaction that reads-then-writes) to avoid dangling references. Referenced documents that are soft-deleted are still valid to reference for historical display but block **new** relationship creation (e.g., cannot allocate a soft-deleted asset).
- **Uniqueness constraints** (e.g., `departments.code`, `employees.email`, `roles.name`) are not natively enforced by Firestore and are checked via a backend query (`where field == value, where isDeleted == false, limit(1)`) inside a transaction before insert/update.
- **Numeric fields** (`purchaseCost`, `capacity`, counters) validated for correct sign/range in backend Pydantic models.
- **Date range validations** (`startTime < endTime`, `scheduledStart <= scheduledEnd`) enforced in backend business logic before write.

---

## 14. Asset Lifecycle (Data Flow)

```
[Create Asset]
   → assets/{assetId} created, status="available", condition per input
   → assetCategories/{categoryId}.assetCount += 1  (Cloud Function trigger)
   → departments/{departmentId}.assetCount += 1
   → auditLogs entry: action="create"

[Allocate Asset]
   → Transaction:
       - Check assets/{assetId}.status == "available"
       - Create assetAllocations/{newId} status="active"
       - Update assets/{assetId}: status="allocated", currentAllocationId, currentHolderSnapshot
   → notifications created for employee (type: allocation_assigned)
   → dashboardAggregates recomputation queued

[Return Asset]
   → Transaction:
       - Update assetAllocations/{id}: status="returned", returnedAt, conditionAtReturn
       - Update assets/{assetId}: status="available", currentAllocationId=null, currentHolderSnapshot=null, condition=conditionAtReturn
   → auditLogs entry

[Send to Maintenance] (triggered by maintenanceRequests approval — see Section 15.4)
   → assets/{assetId}.status = "in_maintenance"

[Retire / Lost Asset]
   → assets/{assetId}.status = "retired" | "lost"
   → If active allocation exists, it is force-closed (status="lost" mirrored, or "returned" with note) as part of same transaction
   → auditLogs entry

[Soft Delete Asset]
   → Only permitted when status is "retired" or "lost" (no active allocation)
   → isDeleted=true, deletedAt, deletedBy
   → assetCategories/departments counters decremented
```

---

## 15. Allocation Lifecycle (Data Flow)

```
pending (implicit, allocation created directly as active — no separate "requested" pre-state
         in v1; a "request to allocate" workflow can be added later as
         `assetAllocationRequests` collection without breaking this model)
   ↓
active — asset in employee's possession, assets.status="allocated"
   ↓
   ├── returned — normal return flow, assets.status back to "available"
   ├── overdue — scheduled Cloud Function flips status when now() > expectedReturnDate
   │              and status still "active"; triggers notification (type: allocation_due)
   └── lost — employee/manager reports asset lost during allocation;
              assets.status → "lost", allocation.status → "lost"
```
Every status transition writes to `auditLogs` and, where the employee is affected, to `notifications`.

---

## 16. Booking Lifecycle (Data Flow)

```
[Create Booking]
   → Transaction:
       - Query resourceBookings where resourceId==X, status=="confirmed",
         check for time overlap with [startTime, endTime) in app code
       - If conflict found → reject with 409-equivalent error
       - Else create resourceBookings/{id} status="confirmed"
   → notifications created for booking employee + attendees (type: booking_confirmed)

[Cancel Booking]
   → Update status="cancelled", cancellationReason required
   → notifications created (type: booking_cancelled)

[Auto-Complete]
   → Scheduled Cloud Function flips status="confirmed" → "completed"
     for bookings where endTime < now()

[Archive]
   → Per Section 11.3, completed/cancelled bookings older than 18 months
     moved to resourceBookingsArchive
```

---

## 17. Maintenance Lifecycle (Data Flow)

```
pending_approval  (created by requestedBy; assets.status untouched until approved)
   ↓ (approvals subdoc created with decision)
   ├── approved → status="approved"
   │      → logs subdoc: action="approved"
   │      → assets/{assetId}.status = "in_maintenance"
   │      → notification to requester (maintenance_status_change)
   │      ↓
   │   assigned to technician (assignedTechnicianId set) → status stays "approved" or moves to
   │      "in_progress" once technician starts work
   │      ↓
   │   in_progress
   │      ↓ (technician completes work, sets actualCost, logs subdoc)
   │   completed
   │      → completedAt set
   │      → assets/{assetId}.status = "available" (or "retired" if unrepairable — separate action)
   │      → notification to requester
   │
   └── rejected → status="rejected"
          → logs subdoc: action="rejected"
          → assets/{assetId}.status unchanged (remains "available")
          → notification to requester

[Cancellation] — requester or admin cancels while still "pending_approval" or "approved"
   → status="cancelled", logs subdoc appended
```
Every transition is mirrored into the `logs` subcollection (immutable audit trail specific to that request) AND into the global `auditLogs` collection (cross-entity trail).

---

## 18. Audit Lifecycle (Data Flow)

```
[Create Audit Cycle]
   → auditCycles/{cycleId} status="planned"
   → Backend computes totalAssetsInScope by querying assets where departmentId in [...]
     and categoryId in [...] (if specified) and isDeleted==false
   → notifications sent to assignedAuditorIds (type: audit_assigned)

[Start Cycle] (manual or scheduled trigger at scheduledStart)
   → status="in_progress"

[Auditor Submits Report per Asset]
   → auditCycles/{cycleId}/reports/{reportId} created
   → auditCycles/{cycleId}.assetsAudited += 1  (Cloud Function trigger)
   → If found==false OR actualCondition != expectedCondition:
       auditCycles/{cycleId}.discrepanciesFound += 1
       notification sent to asset's departmentId head / admins (type: audit_discrepancy)
   → If discrepancy involves damage, may trigger creation of a maintenanceRequests
     document automatically (backend orchestration, not a Firestore-native trigger)

[Close Cycle]
   → status="completed", actualEnd=SERVER_TIMESTAMP
   → dashboardAggregates auditComplianceRate recomputed:
       (assetsAudited - discrepanciesFound) / totalAssetsInScope * 100
```

---

## 19. Notification Lifecycle (Data Flow)

```
[Event occurs in any module] (allocation assigned, allocation overdue, maintenance status
change, maintenance approval needed, booking confirmed/cancelled, audit assigned,
audit discrepancy)
   ↓
Backend (via Cloud Function trigger on the source collection, or inline in the
transaction that caused the event) creates one notifications/{id} document per
recipient, isRead=false
   ↓
Client (React) subscribes via Firestore real-time listener on
notifications where recipientId==currentUser, isRead==false, orderBy createdAt desc
   ↓
User views/opens → backend/client sets isRead=true, readAt=SERVER_TIMESTAMP
   ↓
[Archive] — read notifications older than 6 months moved to notificationsArchive (Section 11.3)
```

---

## 20. Dashboard Aggregation Strategy

1. **Never compute KPIs by scanning full collections at request time.** All dashboard reads hit `dashboardAggregates/{aggregateId}` documents only — O(1) reads regardless of org size.
2. **Aggregates are updated incrementally**, not recomputed from scratch, via Cloud Function triggers on the source collections (`onCreate`/`onUpdate`/`onDelete` of `assets`, `assetAllocations`, `resourceBookings`, `maintenanceRequests`, `auditCycles/reports`, `notifications`). Each trigger applies a small delta (`FieldValue.increment(±1)`) to the relevant counters in the relevant `dashboardAggregates` document(s) (`global_kpis` and the affected `dept_{departmentId}`).
3. **`daily_{YYYY-MM-DD}` snapshots** are written once per day by a scheduled Cloud Function that copies the current `global_kpis` state, enabling historical trend charts (e.g., "assets allocated over the last 30 days") without re-scanning transactional collections.
4. **Consistency model:** Aggregates are **eventually consistent** (typically seconds behind real-time due to trigger latency) — this is an accepted tradeoff and must be communicated in the UI (e.g., "as of {lastComputedAt}") rather than presented as real-time-exact.
5. **Recovery/reconciliation:** A manual/admin-triggered "recompute aggregates" backend job exists to fully rebuild any `dashboardAggregates` document from source collections in case of drift (e.g., after a bulk import or trigger failure) — this is the only place a full collection scan is acceptable, and it runs offline/on-demand, never on the user-facing read path.

---

## 21. Security Considerations

1. **Authentication required for all access** — Firestore Security Rules deny all reads/writes to unauthenticated requests.
2. **RBAC enforced in two layers:**
   - Backend: every API endpoint checks the caller's `roleId` → `permissionIds` (loaded from `roles`/`permissions` collections, cached in memory with short TTL) before performing the operation.
   - Firestore Security Rules: as defense-in-depth, rules check `request.auth.token` custom claims (role/permissions synced to Firebase Auth custom claims on role change) for direct-from-client operations, and generally restrict direct client writes to Firestore in favor of routing all writes through backend API endpoints (recommended: **lock down Firestore Security Rules to read-only for authenticated users on most collections, with all writes going through the Python backend using the Admin SDK**, which bypasses rules by design — this centralizes validation logic in one place, per Section 2 responsibility #2).
3. **Field-level protection:** Sensitive fields (`purchaseCost`, `actualCost`, salary-adjacent data if ever added) are filtered out of API responses for roles without financial-view permission, at the backend serialization layer — Firestore itself has no field-level security, so this must be enforced in application code.
4. **PII minimization:** `employees` documents contain only business-necessary PII (name, email, phone, avatar). No sensitive personal data (SSN, bank details, etc.) is ever stored in this database; if payroll integration is added later, it belongs in a separate, more tightly access-controlled system.
5. **Audit trail immutability:** `auditLogs` and subcollections `approvals`/`logs`/`reports` are never updated or deleted by application logic (Security Rules should deny `update`/`delete` on these paths entirely, only `create` by the backend service account).
6. **Service account scoping:** The backend's Firebase Admin SDK service account is the only writer for `counters`, `dashboardAggregates`, and `auditLogs` — no client-side code path should ever be able to write to these collections directly.

---

## 22. Scalability Considerations

1. **Query patterns are all indexed upfront** (Section 9) — no query in this system requires a collection scan.
2. **Pagination is cursor-based everywhere**, keeping list endpoint latency constant regardless of collection size.
3. **Denormalized snapshots** trade storage for read performance — acceptable because Firestore storage is cheap relative to read operations, and snapshot fields are small (name/code strings only, never full objects).
4. **Hot-document risk is mitigated**: no single document (besides `dashboardAggregates` and `counters`) is written to at high frequency by many concurrent users. If `dashboardAggregates.global_kpis` write contention becomes measurable at scale (>1 write/sec sustained), migrate to **sharded counters** (multiple shard subdocuments summed at read time) — this is a documented, non-breaking upgrade path.
5. **Subcollections keep parent documents small** — `approvals`, `logs`, `reports` grow unbounded over time but never bloat their parent `maintenanceRequests`/`auditCycles` document size.
6. **Archival (Section 11.3)** keeps primary "hot" collections (`resourceBookings`, `maintenanceRequests`, `notifications`) bounded to recent/active data, keeping index size and query latency low indefinitely.
7. **Collection Group Queries** are used sparingly and only on indexed fields (Section 9.2), for legitimate cross-parent reporting needs.

---

## 23. Performance Optimizations

1. **Snapshot listeners used selectively** on the frontend — only for genuinely real-time surfaces (notifications inbox, live booking calendar for the resource currently being viewed), not for every list view, to control read costs and client memory.
2. **Field masks / selective reads:** Backend API responses only project the fields the specific UI view needs, even though Firestore always reads full documents — this controls payload size over the wire, not Firestore read cost (which is per-document regardless of fields used) — so list views favor smaller documents overall (this is why heavy fields like `attachmentUrls`, `photoUrls`, long descriptions are kept on the primary document but UI list views are built from the denormalized snapshot fields where possible instead of hydrating full referenced documents).
3. **Batched reads:** When a view needs multiple related documents (e.g., a maintenance request plus its last 5 logs), use a single subcollection query (`limit(5).orderBy('createdAt','desc')`) rather than N individual reads.
4. **Write batching:** Multi-document mutations (e.g., approval workflow touching request + log + asset status) always use `WriteBatch` or transactions to minimize round trips and guarantee atomicity.
5. **Client-side caching:** React Query (or SWR) caches list/detail reads on the frontend to avoid redundant re-fetches within a session, complementing Firestore's own offline persistence cache.

---

## 24. Future Extensibility

This schema is designed so the following can be added **without breaking existing collections**:

1. **Multi-tenancy:** Add an `orgId` field to every top-level document and prefix `counters`/`dashboardAggregates` keys with `orgId` — all current field names and relationships remain valid; queries simply gain an additional `where('orgId','==', currentOrg)` clause, supported by extending existing composite indexes.
2. **Asset Depreciation Tracking:** `assetCategories.depreciationMethod`/`defaultUsefulLifeMonths` and `assets.purchaseCost`/`purchaseDate` already provide the inputs; a new computed `assets.currentBookValue` field (or a `assetDepreciationSnapshots` subcollection for monthly history) can be layered on later.
3. **Approval Workflows for Allocations/Bookings:** Currently allocations/bookings are created directly; a `status="pending_approval"` pre-state plus `approvals` subcollection (mirroring the `maintenanceRequests` pattern in Section 10.10.1) can be added without changing existing field names.
4. **Vendor/Supplier Management:** A new top-level `vendors` collection can be added and referenced from `assets` (`vendorId`) and `maintenanceRequests` (`vendorId` for external repairs) following the same reference + snapshot pattern used throughout.
5. **Budget/Cost Center Tracking:** A `costCenters` collection referenced from `departments` and `assets`, following the existing relationship conventions.
6. **Mobile Offline Support:** Firestore's native offline persistence already supports this; no schema change required, only client SDK configuration.
7. **Full-Text Search Expansion:** The external search index (Section 9.3) can be extended to additional collections by following the same sync-on-write Cloud Function pattern already established for `assets`/`employees`/`sharedResources`/`maintenanceRequests`.
8. **Additional Notification Channels** (email/SMS/push): `notifications` documents already contain all data needed; a delivery-channel fan-out (Cloud Function reading new `notifications` docs and calling SendGrid/Twilio/FCM) can be added purely as backend infrastructure, no schema change.

---

## 25. Enum Reference (Consolidated)

| Field | Collection | Allowed Values |
|---|---|---|
| `departments.status` | departments | active, inactive |
| `employees.status` | employees | active, on_leave, suspended, inactive |
| `assetCategories.depreciationMethod` | assetCategories | straight_line, declining_balance, none |
| `assets.status` | assets | available, allocated, in_maintenance, retired, lost |
| `assets.condition` | assets / allocations / audit reports | new, good, fair, poor, damaged |
| `assetAllocations.status` | assetAllocations | active, returned, overdue, lost |
| `sharedResources.type` | sharedResources | conference_room, vehicle, equipment, other |
| `sharedResources.status` | sharedResources | active, under_maintenance, inactive |
| `resourceBookings.status` | resourceBookings | confirmed, cancelled, completed |
| `maintenanceRequests.priority` | maintenanceRequests | low, medium, high, critical |
| `maintenanceRequests.status` | maintenanceRequests | pending_approval, approved, rejected, in_progress, completed, cancelled |
| `approvals.decision` | maintenanceRequests/approvals | approved, rejected |
| `logs.action` | maintenanceRequests/logs | created, approved, rejected, assigned, status_changed, commented, completed, cancelled |
| `auditCycles.status` | auditCycles | planned, in_progress, completed, cancelled |
| `notifications.type` | notifications | allocation_assigned, allocation_due, maintenance_status_change, maintenance_approval_needed, booking_confirmed, booking_cancelled, audit_assigned, audit_discrepancy, system |
| `notifications.relatedEntityType` | notifications | asset, allocation, resource, booking, maintenanceRequest, auditCycle |
| `dashboardAggregates.scope` | dashboardAggregates | global, department, daily |
| `auditLogs.action` | auditLogs | create, update, delete, soft_delete, restore |
| `permissions.module` | permissions | department, employee, role, asset, allocation, resource, booking, maintenance, audit, notification, dashboard |

---

**End of Document — this file is the permanent, authoritative database specification for this project. All backend implementation must conform to it exactly. Any change to collections, fields, or relationships must be made here first.**
