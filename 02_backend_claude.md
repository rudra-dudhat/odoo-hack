# 02_backend_claude.md
## Backend Architect Instruction Document
### Enterprise Asset & Resource Management ERP — Python Backend Architecture

**Status:** Single Source of Truth (SSOT) for all backend implementation decisions
**Depends on:** `01_database_claude.md` (Firestore schema — authoritative, immutable from this document's perspective)
**Governed by:** `04_project_rules_claude.md` (AI Agent Master Rulebook — architecture, naming, testing, security baseline)
**Applies to:** Python (FastAPI) backend, Firebase Admin SDK, Firebase Authentication, Firebase Storage, Cloud Functions
**Audience:** Any AI or engineer implementing backend code for this project, without needing to ask backend-related questions

---

## 0. Non-Negotiable Constraints

1. This document is **law** for backend implementation, subordinate only to `01_database_claude.md` (schema) and `04_project_rules_claude.md` (engineering rules). Where they conflict, flag the conflict — never silently deviate.
2. The backend **must never invent new database fields, collections, or enum values**. Every field written or read must already exist in `01_database_claude.md` Section 10 (Collection Schemas) and Section 25 (Enum Reference).
3. The backend **must never change the schema**. Adding a field/collection requires updating `01_database_claude.md` first, in a separate change.
4. The backend **exposes APIs only for features defined in the database specification** — no speculative endpoints, no extra modules, no functionality beyond what Sections 10, 14–20 of the database spec describe.
5. Firestore has no native schema enforcement — **the Python backend is the primary validation and business-logic authority**; Firestore Security Rules are the second line of defense (Section 21 of database spec).
6. All architecture, naming, folder structure, error handling, logging, testing, and Git/commit rules in `04_project_rules_claude.md` apply to this backend without exception. This document specializes those rules for this specific Firestore + FastAPI system; it does not override them.

---

## 1. Backend Architecture

### 1.1 Architectural Style
Layered / Clean Architecture, per `04_project_rules_claude.md` Section 2 and 22, adapted for a Firestore-backed FastAPI service:

```
Presentation (API)  →  Application (Use Cases / Services)  →  Domain (Entities, Rules)  →  Infrastructure (Firestore, Firebase Auth, Storage)
```

- Dependencies point inward only. **Domain never imports Infrastructure or Presentation.**
- **Infrastructure implements interfaces defined by Domain/Application** (Repository interfaces live in domain/application; Firestore-specific repository implementations live in infrastructure) — Dependency Inversion (Section 21 of project rules).
- Business rules (asset lifecycle, allocation rules, booking conflict detection, maintenance workflow, audit workflow) live exclusively in the **Application (service) layer** — never in route handlers, never in repository classes.
- Every service is independently unit-testable with a mocked repository — no live Firestore connection required for unit tests.

### 1.2 Layer Responsibilities

| Layer | Responsibility | Must Not |
|---|---|---|
| **Presentation** (`api/`) | HTTP routing, request parsing, response shaping, status codes, auth/permission dependency wiring | Contain business logic, talk to Firestore directly |
| **Application** (`services/`) | Orchestrate use cases, enforce business rules, coordinate transactions across repositories, trigger notifications/aggregates | Know about HTTP (status codes, request/response models), know about Firestore SDK internals |
| **Domain** (`domain/`) | Entities (Pydantic models mirroring schema exactly), value objects, enums, pure business rule functions with no I/O | Import from application/infrastructure/presentation, perform I/O |
| **Infrastructure** (`infrastructure/`) | Firestore repository implementations, Firebase Admin SDK calls, Storage access, Cloud Functions, counters, external search sync | Contain business rules or validation beyond data-shape/type marshaling |

### 1.3 Request Lifecycle
```
HTTP Request
  → FastAPI route (presentation/api)
  → Auth dependency: verify Firebase ID token → resolve employeeId (uid)
  → RBAC dependency: check permission required for this endpoint
  → Pydantic request model validation (schema-exact field validation)
  → Service (application layer) called with validated DTO + acting employeeId
  → Service enforces business rules, calls one or more Repositories
  → Repository executes Firestore reads/writes/transactions (infrastructure)
  → Service triggers side effects (notifications, aggregate deltas, auditLogs) within same transaction/batch where required
  → Service returns Domain entity/DTO
  → Route maps to standard API Response envelope (Section 8) + status code (Section 9)
```

---

## 2. Folder Structure

Backend lives under `src/` per `04_project_rules_claude.md` Section 4, specialized for this Python service:

```
src/
  domain/
    entities/            # Pydantic models: Department, Employee, Role, Permission, AssetCategory,
                          # Asset, AssetAllocation, SharedResource, ResourceBooking,
                          # MaintenanceRequest, Approval, MaintenanceLog, AuditCycle, AuditReport,
                          # Notification, DashboardAggregate, AuditLogEntry, Counter
    enums/                # Enum classes mirroring database spec Section 25 exactly
    value_objects/        # Snapshot objects (DepartmentSnapshot, EmployeeSnapshot, AssetSnapshot, etc.)
    rules/                # Pure business-rule functions (no I/O): overlap-check, allocation eligibility,
                          # status-transition validity, audit compliance calculation
    repositories/         # Abstract repository interfaces (Protocols/ABCs) — one per top-level collection

  application/
    services/             # One service per module (DepartmentService, EmployeeService, RoleService,
                          # AssetService, AllocationService, ResourceService, BookingService,
                          # MaintenanceService, AuditService, NotificationService, DashboardService,
                          # AuditLogService)
    dtos/                 # Request/response DTOs (Pydantic) — API-facing shapes, may omit fields
                          # per field-level protection (Section 21.3 of database spec)
    use_cases/            # Multi-service orchestrations that don't belong to a single module
                          # (e.g., maintenance-approval-triggers-asset-status-change-and-notification)

  infrastructure/
    firestore/
      client.py           # Firebase Admin SDK / Firestore client bootstrap (singleton)
      repositories/       # Concrete Firestore repository implementations, one per collection
      transactions.py     # Shared transaction/batch-write helpers
      counters.py         # Business ID generator (Section 8.2 of database spec)
    auth/
      firebase_auth.py    # Firebase ID token verification, custom claims sync
    storage/
      firebase_storage.py # Upload/URL generation for images, attachments, evidence photos
    cloud_functions/       # Trigger handlers deployed as Cloud Functions (Section 12)
    search/
      external_index_sync.py  # Sync-on-write to external full-text search index (Section 9.3 of database spec)

  presentation/
    api/
      v1/
        departments.py
        employees.py
        roles.py
        permissions.py
        asset_categories.py
        assets.py
        asset_allocations.py
        shared_resources.py
        resource_bookings.py
        maintenance_requests.py
        audit_cycles.py
        notifications.py
        dashboard.py
        audit_logs.py
    dependencies/
      auth.py              # get_current_employee dependency
      rbac.py               # require_permission(permission_key) dependency
      pagination.py         # cursor-based pagination dependency
    middleware/
      logging_middleware.py
      error_handler.py
      request_id_middleware.py

  shared/
    errors/                # Custom exception classes (Section 16 of project rules)
    constants/             # Named constants (limits, defaults) — no magic numbers (Section 31 of database spec / Section 6+31 of project rules)
    utils/                 # Cross-cutting pure helpers (money formatting, date range overlap util, etc.)
    logging/                # Structured logger configuration

  config/
    settings.py             # Typed, validated config (Pydantic Settings), env var loading
    firebase_config.py

tests/
  unit/                     # Mirrors src/ tree; mocks repositories, tests services and domain rules
  integration/               # Tests against Firestore emulator; tests repositories and transactions
  e2e/                        # Full API tests via test client + Firestore emulator + Auth emulator

docs/
  02_backend_claude.md       # this document
```

No file lives outside its designated layer folder (project rules Section 4). No parallel structures for new features (database spec Section 24 / project rules Section 32).

---

## 3. Python Project Structure

- **Language/Framework:** Python 3.12+, FastAPI, Pydantic v2, Firebase Admin SDK (`firebase-admin`), Uvicorn/Gunicorn for serving.
- **Dependency management:** single lockfile (`pyproject.toml` + `poetry.lock` or `uv.lock`) — one source of truth, no mixed `requirements.txt` + lockfile.
- **App entrypoint:** `src/main.py` — builds the FastAPI app, registers routers under `/api/v1`, registers middleware, registers exception handlers, validates required env vars at startup (fail fast, per project rules Section 12).
- **Dependency Injection:** FastAPI's `Depends()` used to inject repository instances into services and services into routes, via factory functions in `infrastructure/` and `presentation/dependencies/` — never module-level global service instances.
- **No new libraries/frameworks** may be introduced without first updating database spec Section 1 (Tech Stack) or this document's stack notes, per project rules Section 3 and Section 26 (AI Collaboration Rules).

---

## 4. Firebase Integration

1. **Firestore access exclusively through the Firebase Admin SDK**, initialized once as a singleton client (`infrastructure/firestore/client.py`), reused across the app (no per-request client construction).
2. **The Admin SDK service account is the only writer** for `counters`, `dashboardAggregates`, and `auditLogs` — enforced both by never exposing client-write paths for these collections in the API layer and by Firestore Security Rules (database spec Section 21.6).
3. **Firestore Security Rules are locked down to read-only for authenticated users on most collections**; all writes route through this backend (database spec Section 21.2). The backend does not rely on Security Rules for business validation — it is defense-in-depth only.
4. **Timestamps:** every `createdAt`/`updatedAt` write uses `firestore.SERVER_TIMESTAMP` — the backend never accepts client-supplied timestamp values for these fields, even if present in a request payload (silently stripped/ignored at the DTO layer).
5. **Business ID generation** (`AST-######`, `RES-######`, `MR-YYYY-#####`, `AC-YYYY-Qn`) goes exclusively through `infrastructure/firestore/counters.py`, using a Firestore transaction against `counters/{counterId}` (read → increment → write → format), per database spec Section 8.2. Application code never constructs these IDs by string formatting outside this module.
6. **Storage:** Firebase Storage is used only for binary content (asset images, avatars, maintenance attachments, audit evidence photos). Firestore documents store only the resulting Storage URLs/paths, never binary data, per database spec Section 4.
7. **Cloud Functions** (Section 12 below) are deployed as separate functions but share domain/application logic where possible via a common installable package or shared module import, to avoid duplicating business rules between the FastAPI service and the Functions runtime (DRY, project rules Section 20).

---

## 5. Authentication

1. **Firebase Authentication** is the sole identity provider. Every API request (except health checks) must carry a valid Firebase ID token in the `Authorization: Bearer <token>` header.
2. Backend verifies the token via Firebase Admin SDK (`auth.verify_id_token`) in the `get_current_employee` dependency (`presentation/dependencies/auth.py`).
3. On success, the token's `uid` is resolved to the corresponding `employees/{employeeId}` document (`employeeId == uid`, per database spec Section 6). This document must exist, have `isDeleted == false`, and `status` must not block access per business rule (`suspended`/`inactive` employees are denied — see Section 7 below).
4. Unauthenticated or invalid-token requests receive `401 Unauthorized` before any business logic executes.
5. **No client-supplied identity fields are ever trusted.** `createdBy`, `updatedBy`, `requestedBy`, `performedBy`, `recipientId` (self-notifications aside) etc. are always derived from the verified token server-side, never taken from the request body (database spec Section 12).

---

## 6. Authorization & RBAC

### 6.1 Model
Mirrors database spec Sections 10.3, 10.4, 21.2 exactly:
- `employees.roleId` → `roles/{roleId}`
- `roles.permissionIds[]` → `permissions/{permissionId}`
- `permissions.key` (e.g., `"asset.create"`, `"maintenance.approve"`) and `permissions.module` are the atomic authorization units.

### 6.2 Enforcement
1. On each request, after authentication resolves the acting employee, the `require_permission(permission_key)` dependency (`presentation/dependencies/rbac.py`) loads the employee's `roleId` → `roles.permissionIds[]` → checks the required `permissions.key` is present.
2. Role/permission lookups are **cached in memory with a short TTL** (per database spec Section 21.2) to avoid a Firestore read on every request; cache is invalidated on role/permission mutation.
3. Missing permission → `403 Forbidden`. Missing/invalid auth → `401 Unauthorized`.
4. **Firestore custom claims** (role/permission summary) are synced to the Firebase Auth user record whenever an employee's `roleId` or the role's `permissionIds` change, so Security Rules (defense-in-depth) stay consistent with backend RBAC state.
5. **Field-level protection:** DTOs for `assets` (`purchaseCost`, `currency`) and `maintenanceRequests` (`estimatedCost`, `actualCost`) strip these fields from API responses for callers lacking a financial-view permission, at the serialization layer in `application/dtos/` — never relying on Firestore for field-level security (database spec Section 21.3).
6. **PII minimization:** employee-facing responses never include fields beyond what's defined in Section 10.2 of the database spec — no ad-hoc PII fields are ever added to response DTOs.

---

## 7. Validation

1. **Every write DTO is a Pydantic model whose fields, types, `Literal`/`Enum` constraints, and length/range limits match the corresponding table in database spec Section 10 exactly.** No DTO may include a field absent from the schema; no DTO may omit a required (`R`) field without a default.
2. **Enum validation:** all enum fields use Python `Enum`/`Literal` types populated from database spec Section 25 verbatim. Any enum value not in that list is rejected with `400 Bad Request` before any Firestore write.
3. **String length limits** enforced via Pydantic `constr`/`Field(min_length=…, max_length=…)` matching each field's documented range (e.g., `departments.name` 2–100 chars, `maintenanceRequests.issueDescription` 10–5000 chars).
4. **Numeric fields** (`purchaseCost`, `capacity`, `defaultUsefulLifeMonths`, etc.) validated for sign/range per schema (e.g., `purchaseCost >= 0`, stored as integer smallest-currency-unit).
5. **Date range validation** enforced in the service layer before write: `startTime < endTime` (bookings), `scheduledStart <= scheduledEnd` (audit cycles), `expectedReturnDate >= allocatedAt` (allocations).
6. **Reference integrity:** before writing any document containing a reference field (`departmentId`, `employeeId`, `assetId`, `roleId`, `categoryId`, `resourceId`, etc.), the service layer performs an existence check (direct-ID read, or read-then-write inside the same transaction) against the referenced collection. Referencing a soft-deleted document is rejected for **new relationship creation**, but permitted for historical read-only display (database spec Section 13).
7. **Uniqueness constraints** (`departments.code`, `departments.name`, `employees.email`, `roles.name`, `assetCategories.name`/`code`) are checked via a backend query (`where field == value, where isDeleted == false, limit(1)`) inside a transaction immediately before insert/update, per database spec Section 13.
8. **Document size / array bounds:** free-text fields capped per schema (e.g., 5,000 chars for `issueDescription`, 1,000/2,000 for notes/details); array fields capped per schema (`imageUrls` max 10, `attendeeIds` max 100, `permissionIds` < 200).
9. Validation failures return `400 Bad Request` with a structured, field-level error payload (Section 8.3) — no partial writes ever occur.

---

## 8. API Conventions

### 8.1 Naming Conventions (REST Endpoints)
Per project rules Section 5.5 and database spec collection names (Section 5):
- Plural nouns, `kebab-case` in URL segments where multi-word: `/api/v1/asset-categories`, `/api/v1/asset-allocations`, `/api/v1/resource-bookings`, `/api/v1/maintenance-requests`, `/api/v1/audit-cycles`, `/api/v1/dashboard-aggregates`.
- Single-word collections stay as-is: `/api/v1/departments`, `/api/v1/employees`, `/api/v1/roles`, `/api/v1/permissions`, `/api/v1/assets`, `/api/v1/notifications`.
- Subcollections nested under their parent's business ID, matching the database tree (Section 7 of database spec):
  - `/api/v1/maintenance-requests/{requestId}/approvals`
  - `/api/v1/maintenance-requests/{requestId}/logs`
  - `/api/v1/audit-cycles/{cycleId}/reports`
- No verbs in URLs (`/getAssets` is forbidden). HTTP verbs (GET/POST/PUT/PATCH/DELETE) express the action.
- Versioned explicitly: all routes under `/api/v1/`.
- Action-style transitions that are not plain CRUD (allocate, return, cancel, approve, reject, check-in, close-cycle) are modeled as `POST` on a sub-resource/action path, e.g.:
  - `POST /api/v1/assets/{assetId}/allocate`
  - `POST /api/v1/asset-allocations/{allocationId}/return`
  - `POST /api/v1/resource-bookings/{bookingId}/cancel`
  - `POST /api/v1/maintenance-requests/{requestId}/approve`
  - `POST /api/v1/maintenance-requests/{requestId}/reject`
  - `POST /api/v1/maintenance-requests/{requestId}/complete`
  - `POST /api/v1/audit-cycles/{cycleId}/start`
  - `POST /api/v1/audit-cycles/{cycleId}/close`
  - `POST /api/v1/notifications/{notificationId}/mark-read`
  - `POST /api/v1/departments/{departmentId}/restore` (and equivalent `restore` actions for other soft-deletable entities)

  This is the only sanctioned exception to "no verbs in URL" — these are documented workflow transitions with dedicated business rules (Sections 15–20), not generic CRUD, and are named to match the Lifecycle Data Flow diagrams in the database spec exactly.

### 8.2 CRUD Operations (Standard, per Module)
Every module exposes only the operations meaningful for its schema and lifecycle — no module gets a full CRUD set by default if the schema doesn't call for it (e.g., `auditLogs` and `counters` expose **no client-facing write endpoints at all**):

| Operation | HTTP | Applies to |
|---|---|---|
| List (paginated, filtered) | `GET /{collection}` | all client-facing collections |
| Get by ID | `GET /{collection}/{id}` | all client-facing collections |
| Create | `POST /{collection}` | all except `dashboardAggregates`, `auditLogs`, `counters` |
| Update (partial) | `PATCH /{collection}/{id}` | all except append-only subcollections (`approvals`, `logs`, `reports`), `auditLogs`, `counters` |
| Soft delete | `DELETE /{collection}/{id}` | only entities listed in database spec Section 11.1: `departments`, `employees`, `assetCategories`, `assets`, `sharedResources`, `roles`, `permissions` |
| Hard delete | `DELETE /{collection}/{id}?hard=true` | only `notifications` (user-cleared) and admin-only erroneous-document cleanup, per database spec Section 11.2 |
| Restore | `POST /{collection}/{id}/restore` | same set as soft delete |

`PUT` (full replace) is **not used** anywhere — Firestore documents are updated via partial field merges only, matching `PATCH` semantics.

### 8.3 API Response Format
Every endpoint returns a consistent envelope:

**Success (single resource):**
```json
{
  "success": true,
  "data": { "...": "resource fields, schema-exact" },
  "meta": null
}
```

**Success (list, cursor-paginated):**
```json
{
  "success": true,
  "data": [ { "...": "..." } ],
  "meta": {
    "nextCursor": "opaque-cursor-string-or-null",
    "hasMore": true
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-safe, generic message",
    "fieldErrors": [
      { "field": "email", "message": "must be a valid email address" }
    ]
  }
}
```
- Internal detail (stack traces, Firestore error internals) never appears in the response — only in structured logs, per project rules Section 16.
- `error.code` values are a fixed enum owned by `shared/errors/` (e.g., `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, `FORBIDDEN`, `UNAUTHENTICATED`, `INTERNAL_ERROR`).

### 8.4 Pagination
- **Cursor-based only**, never offset-based, per database spec Section 4/22.2.
- Query params: `?limit=<n>&cursor=<opaque-cursor>&sortBy=<field>&sortDir=asc|desc`.
- `limit` capped server-side (default 25, max 100) — no unbounded list reads.
- Cursor encodes the last document's sort-field value(s) + document ID, consumed via Firestore's `start_after`.

### 8.5 Filtering
- Only filter fields explicitly declared per collection in database spec Section 10 (`Filter fields:` line for each collection) are accepted as query params. Any other filter param is rejected with `400 Bad Request` — this keeps every query satisfiable by the declared composite indexes (database spec Section 9), never requiring an undeclared index.
- Default list queries always include `isDeleted == false` for soft-deletable entities, unless `?includeDeleted=true` is passed by a caller holding admin-level permission.

---

## 9. Status Codes

| Code | Meaning | Used when |
|---|---|---|
| `200 OK` | Successful GET/PATCH/action | Standard success |
| `201 Created` | Successful POST creating a resource | New document created |
| `204 No Content` | Successful DELETE (hard) with no body | Hard-delete only |
| `400 Bad Request` | Validation error, malformed enum/field, undeclared filter param | Any Pydantic/business validation failure before write |
| `401 Unauthorized` | Missing/invalid/expired Firebase ID token | Auth dependency failure |
| `403 Forbidden` | Authenticated but lacking required permission | RBAC dependency failure |
| `404 Not Found` | Referenced document does not exist (or is soft-deleted and caller lacks access to it) | Get-by-ID / reference-integrity checks |
| `409 Conflict` | Business-rule conflict: booking time overlap, duplicate active allocation on an asset, uniqueness violation (duplicate email/code/name) | Concurrency/business-invariant violations |
| `422 Unprocessable Entity` | Semantically invalid request that passes shape validation but fails cross-field business rules not covered by 400/409 (e.g., `scheduledEnd < scheduledStart`) | Cross-field domain rule failures |
| `500 Internal Server Error` | Unhandled exception, Firestore transaction failure after retries | Bugs, infra failures — always logged with correlation ID |

---

## 10. Service Layer

One service class per module, named `<Module>Service`, in `application/services/`. Responsibilities per module are detailed in Section 13 (Module Specifications). General rules:

1. Services are the **only layer permitted to orchestrate multi-repository operations and Firestore transactions/batches** — routes never call two repositories directly, and repositories never call each other.
2. Services accept the **acting employee's ID** (from the verified token) explicitly as a parameter — never read it from any global/thread-local context — to keep services independently testable.
3. Services return **domain entities or DTOs**, never raw Firestore document snapshots — Firestore-specific types never leak past the infrastructure layer.
4. Services raise **custom domain exceptions** (`shared/errors/`) — never generic `Exception` — for every predictable failure mode (not found, conflict, validation, forbidden), which the presentation layer's exception handler maps to the status codes in Section 9.
5. Every service method that performs a write also performs the corresponding **`auditLogs` write** (via `AuditLogService`, injected) within the same logical operation, per database spec Section 3.5 and 10.14 — this is not optional per-module behavior, it is a cross-cutting service-layer responsibility.

---

## 11. Repository Layer

1. One repository interface (Protocol/ABC) per top-level collection in `domain/repositories/`, with a matching Firestore implementation in `infrastructure/firestore/repositories/`.
2. Repositories expose only **data-access operations** (`get_by_id`, `list`, `create`, `update`, `soft_delete`, `hard_delete`, `restore`, plus collection-specific query methods like `find_active_allocation_for_asset`) — **no business rules, no cross-collection orchestration**.
3. Subcollection repositories (`approvals`, `logs`, `reports`) are scoped to their parent document ID and are **append-only** (`create`, `list`) — no `update`/`delete` methods are exposed, matching their immutability (database spec Sections 10.10.1, 10.10.2, 10.11.1).
4. `auditLogs` and `counters` repositories expose **write methods only to the backend service layer itself** (never reachable from a public route), matching database spec Section 21.6.
5. All repository writes that must stay atomic with other writes (e.g., allocation create + asset status update) are implemented via a shared `transactions.py` helper using Firestore `WriteBatch`/`Transaction`, invoked from the Service layer — repositories provide the individual read/write primitives used inside that transaction, they do not decide when a transaction is needed.
6. Repositories translate raw Firestore documents into Domain entities (Pydantic) on read, and Domain entities into plain dicts (with `SERVER_TIMESTAMP` sentinels for timestamp fields) on write — this translation boundary is the only place Firestore-specific data shapes are visible outside `infrastructure/`.

---

## 12. Background Jobs & Cloud Functions

Every job below exists **because it is explicitly required by a lifecycle in the database spec** — no additional jobs are created.

| Job | Type | Trigger | Source | Action |
|---|---|---|---|---|
| Overdue allocation flip | Scheduled Cloud Function | Daily (or hourly) schedule | Database spec Section 15 | `assetAllocations` where `status=="active" AND expectedReturnDate < now()` → `status="overdue"`; creates `notifications` (`allocation_due`) |
| Booking auto-complete | Scheduled Cloud Function | Periodic schedule | Database spec Section 16 | `resourceBookings` where `status=="confirmed" AND endTime < now()` → `status="completed"` |
| Dashboard aggregate deltas | Firestore-triggered Cloud Function | `onCreate`/`onUpdate`/`onDelete` on `assets`, `assetAllocations`, `resourceBookings`, `maintenanceRequests`, `auditCycles/reports`, `notifications` | Database spec Section 20 | Applies `FieldValue.increment(±1)` deltas to `dashboardAggregates/global_kpis` and the relevant `dashboardAggregates/dept_{departmentId}` |
| Daily KPI snapshot | Scheduled Cloud Function | Once daily | Database spec Section 20.3 | Copies current `global_kpis` state into a new `dashboardAggregates/daily_{YYYY-MM-DD}` document |
| Denormalized counter maintenance | Firestore-triggered Cloud Function | `onCreate`/`onDelete` on `employees`, `assets` | Database spec Sections 10.1, 10.5, 14 | Increments/decrements `departments.employeeCount`/`assetCount`, `assetCategories.assetCount` |
| Snapshot refresh | Firestore-triggered Cloud Function | `onUpdate` of display-relevant fields on `departments`, `employees`, `assets`, `sharedResources` | Database spec Section 8.1 | Refreshes denormalized `<entity>Snapshot` maps on referencing documents (or leaves them to refresh lazily on next write, per spec) |
| Audit-cycle report counters | Firestore-triggered Cloud Function | `onCreate` on `auditCycles/{cycleId}/reports` | Database spec Section 18 | Increments `assetsAudited`, conditionally `discrepanciesFound`; triggers `audit_discrepancy` notification |
| Archival | Scheduled Cloud Function | Periodic (e.g., weekly) | Database spec Section 11.3 | Moves aged `resourceBookings`/`maintenanceRequests`/`notifications` into `..._archive` collections, then hard-deletes originals |
| External search index sync | Firestore-triggered Cloud Function | `onWrite` on `assets`, `employees`, `sharedResources`, `maintenanceRequests` | Database spec Section 9.3 | Syncs fuzzy-searchable fields to the external search index |
| Manual aggregate reconciliation | On-demand backend admin endpoint (not scheduled) | Admin-triggered via `POST /api/v1/dashboard/recompute` (requires elevated permission) | Database spec Section 20.5 | Full collection scan to rebuild a `dashboardAggregates` document from source — the **only** sanctioned full-scan path, never on the user read path |

Cloud Functions share domain/business-rule code with the FastAPI service (Section 4.7) rather than reimplementing rules — this satisfies the DRY principle (project rules Section 20, 27).

---

## 13. Module Specifications

Every module below follows: **Responsibilities → Business Rules → Input Validation → Output → Database Interaction → Possible Errors.** No module exposes functionality beyond what is listed here, and every field/rule referenced maps directly to `01_database_claude.md`.

---

### 13.1 Departments (`departments`)

**Responsibilities:** CRUD for organizational departments; soft-delete/restore; expose denormalized counters read-only.

**Business Rules:**
- `name` and `code` must be unique among non-deleted departments (database spec 10.1, 13).
- `headEmployeeId`, if set, must reference an existing `employees` document.
- `employeeCount`/`assetCount` are **never written by the client** — they are maintained only by Cloud Function triggers (Section 12); write attempts on these fields via the API are ignored/stripped.
- Soft delete only permitted when `employeeCount == 0` and `assetCount == 0` (no live references) — otherwise reject with `409 Conflict`.

**Input Validation:** `name` 2–100 chars; `code` uppercase 2–10 chars; `description` ≤1000 chars; `status` ∈ `["active","inactive"]`.

**Output:** Department entity including standard audit fields; list responses support filter by `status`, sort by `name` (default) or `createdAt`, search by `name`/`code` prefix.

**Database Interaction:** Direct CRUD on `departments/{departmentId}` (auto-ID). Uniqueness check via transaction-scoped query before create/update.

**Possible Errors:** `400` invalid fields, `404` department/head employee not found, `409` duplicate name/code or delete-blocked-by-references.

---

### 13.2 Employees (`employees`)

**Responsibilities:** CRUD for employee records; employee code generation; department/role assignment; soft-delete/restore; status management.

**Business Rules:**
- `employeeId` **must equal the Firebase Auth UID** — employee creation is tied to an existing Firebase Auth user (backend creates the Firestore doc after Auth user provisioning, or accepts a pre-provisioned UID).
- `employeeCode` generated via `counters/employees`-equivalent sequence at creation, immutable thereafter.
- `departmentId` and `roleId` must reference existing, non-deleted documents; `departmentSnapshot`/`roleSnapshot` are populated server-side from the referenced documents at write time — never client-supplied.
- `email` must be unique among non-deleted employees.
- Changing `roleId` triggers a Firebase Auth custom-claims resync (Section 6.4).
- An employee with `status` ∈ `["suspended","inactive"]` is denied API access at the authentication layer (Section 5.3), independent of RBAC permission checks.

**Input Validation:** `fullName` 2–150 chars; `email` valid format; `phone` E.164 preferred; `designation` ≤100 chars; `status` ∈ `["active","on_leave","suspended","inactive"]`.

**Output:** Employee entity (with `departmentSnapshot`, `roleSnapshot`); financial-sensitive fields N/A for this module.

**Database Interaction:** CRUD on `employees/{uid}`. Reads `departments`/`roles` for snapshot population and reference validation. Triggers `departments.employeeCount` delta via Cloud Function.

**Possible Errors:** `400` invalid fields, `404` department/role not found, `409` duplicate email, `403` self-role-escalation attempt without permission.

---

### 13.3 Roles & Permissions (`roles`, `permissions`)

**Responsibilities:** CRUD for roles and permissions (admin-only, RBAC configuration); assignment of `permissionIds[]` to roles.

**Business Rules:**
- `permissions` are largely static reference data; `permissionId` slugs and `key` values must exactly match the enum-like set the system relies on for `require_permission()` checks — no ad-hoc permission keys.
- `roles.isSystemRole == true` roles (`role_admin`, `role_manager`, `role_employee`) **cannot be deleted**, and their `permissionIds` changes require elevated confirmation.
- Every ID in `permissionIds[]` must reference an existing `permissions` document.
- Changing a role's `permissionIds` triggers custom-claims resync for all employees holding that role.

**Input Validation:** `roles.name` 2–50 chars unique; `permissionIds` bounded (<200); `permissions.key`/`label` required, `module` ∈ enum list (database spec 25).

**Output:** Role/Permission entities; roles list includes resolved permission summary.

**Database Interaction:** CRUD on `roles/{roleId}`, `permissions/{permissionId}` (slug IDs, backend-controlled). No `isDeleted` lifecycle write path exposed for `permissions` beyond consistency (spec 10.4 note).

**Possible Errors:** `400` invalid module/enum, `403` non-admin attempting role/permission mutation, `409` system-role delete attempt, `404` referenced permission not found.

---

### 13.4 Asset Categories (`assetCategories`)

**Responsibilities:** CRUD for hierarchical asset categories; depreciation configuration; soft-delete/restore.

**Business Rules:**
- `name`/`code` unique among non-deleted categories.
- `parentCategoryId` must reference another `assetCategories` doc; hierarchy capped at 1 level deep (no grandparent chains) per database spec 10.5.
- `assetCount` is Cloud-Function-maintained only, never client-writable.
- Soft delete only permitted when `assetCount == 0`.

**Input Validation:** `name` 2–100 chars; `code` uppercase 2–10 chars; `depreciationMethod` ∈ `["straight_line","declining_balance","none"]`; `defaultUsefulLifeMonths` integer > 0.

**Output:** AssetCategory entity with hierarchy reference.

**Database Interaction:** CRUD on `assetCategories/{categoryId}` (auto-ID). Parent-category existence check at write time.

**Possible Errors:** `400` invalid enum/hierarchy depth, `404` parent category not found, `409` duplicate name/code, delete-blocked.

---

### 13.5 Assets (`assets`)

**Responsibilities:** CRUD for physical assets; asset lifecycle transitions (allocate/return handled in 13.6, but status-relevant transitions like retire/lost/send-to-maintenance are owned here); asset tag generation.

**Business Rules (Asset Lifecycle Logic — database spec Section 14):**
- **Create:** `assetId` (Asset Tag, `AST-######`) generated via `counters/assets` transaction; `status` defaults `"available"`; triggers `assetCategories.assetCount`/`departments.assetCount` increment; writes `auditLogs` `action="create"`.
- **Allocate:** delegated to `AllocationService` (13.6) — `AssetService` exposes only the status-mutation primitive used inside that transaction.
- **Send to Maintenance:** status → `"in_maintenance"`, driven only by an approved `maintenanceRequests` transition (13.9), never a direct client call to change status to `in_maintenance` outside that workflow.
- **Retire / Lost:** `status` → `"retired"` or `"lost"`; if an active allocation exists, it is force-closed in the same transaction (`assetAllocations.status` → `"lost"` mirrored, or `"returned"` with a note); writes `auditLogs`.
- **Soft Delete:** only permitted when `status` ∈ `["retired","lost"]` and no active allocation exists; decrements category/department counters.
- `categoryId`/`departmentId` must reference existing, non-deleted documents; `categorySnapshot`/`departmentSnapshot` populated server-side.
- `currentAllocationId`/`currentHolderSnapshot` are **never directly client-writable** — set only by the allocation transaction.
- Monetary fields (`purchaseCost`) stored as integer smallest-currency-unit; filtered from responses for callers without financial-view permission (Section 6.5).

**Input Validation:** `name` 2–150 chars; `status` ∈ `["available","allocated","in_maintenance","retired","lost"]`; `condition` ∈ `["new","good","fair","poor","damaged"]`; `purchaseCost` ≥ 0 integer; `currency` ISO 4217; `imageUrls` max 10.

**Output:** Asset entity; `purchaseCost`/`currency` omitted for non-financial-view roles.

**Database Interaction:** CRUD + status-transition writes on `assets/{assetId}`. Reads `assetCategories`/`departments` for snapshots. Transactional force-close of `assetAllocations` on retire/lost.

**Possible Errors:** `400` invalid status/condition/enum, `404` asset/category/department not found, `409` retire/lost with unresolvable active allocation conflict, delete-blocked (not retired/lost or has active allocation), `403` financial field access.

---

### 13.6 Asset Allocations (`assetAllocations`) — Allocation Rules

**Responsibilities:** Allocate an available asset to an employee; process returns; report loss; enforce single-active-allocation-per-asset invariant.

**Business Rules (Allocation Lifecycle — database spec Section 15):**
- **Allocate** (`POST /assets/{assetId}/allocate`): within a single Firestore transaction — (1) verify `assets/{assetId}.status == "available"` and not soft-deleted, (2) verify `employeeId` references an existing, non-deleted, non-suspended employee, (3) create `assetAllocations/{newId}` with `status="active"`, `conditionAtAllocation` from asset's current condition or override, (4) update `assets/{assetId}`: `status="allocated"`, `currentAllocationId`, `currentHolderSnapshot`. Only one `status=="active"` allocation may exist per `assetId` at any time — enforced by the same transaction re-checking asset status immediately before write (race-condition-safe).
- **Return** (`POST /asset-allocations/{allocationId}/return`): within a transaction — update the allocation `status="returned"`, `returnedAt`, `conditionAtReturn`; update `assets/{assetId}`: `status="available"`, `currentAllocationId=null`, `currentHolderSnapshot=null`, `condition=conditionAtReturn`.
- **Report Lost:** update allocation `status="lost"`; update `assets/{assetId}.status="lost"`.
- **Overdue:** never client-set — only the scheduled Cloud Function (Section 12) transitions `active` → `overdue` when `now() > expectedReturnDate`.
- Every transition writes `auditLogs`; employee-affecting transitions create `notifications` (`allocation_assigned`, `allocation_due`).

**Input Validation:** `expectedReturnDate` ≥ `allocatedAt` if set; `conditionAtAllocation`/`conditionAtReturn` ∈ condition enum; `notes` ≤1000 chars.

**Output:** AssetAllocation entity with `assetSnapshot`/`employeeSnapshot`.

**Database Interaction:** Transactional multi-document writes across `assetAllocations` and `assets`. Filterable by `assetId`, `employeeId`, `status`; sorted `allocatedAt DESC`.

**Possible Errors:** `409` asset not available (already allocated/in_maintenance/retired/lost), `404` asset/employee not found, `400` invalid condition/date, `403` insufficient permission to allocate/return on behalf of another employee.

---

### 13.7 Shared Resources (`sharedResources`)

**Responsibilities:** CRUD for bookable shared resources (rooms, vehicles, equipment); resource code generation; booking-rule configuration; soft-delete/restore.

**Business Rules:**
- `resourceId` (`RES-######`) generated via `counters/resources` transaction.
- `bookingRules` (`minDurationMinutes`, `maxDurationMinutes`, `advanceBookingDays`) default `{60, 480, 30}` and are enforced by `BookingService`, not re-validated here beyond shape.
- Soft delete only permitted when no `resourceBookings` with `status=="confirmed"` reference this resource.

**Input Validation:** `name` 2–150 chars; `type` ∈ `["conference_room","vehicle","equipment","other"]`; `status` ∈ `["active","under_maintenance","inactive"]`; `capacity` integer > 0 if set; `amenities`/`imageUrls` max 10.

**Output:** SharedResource entity.

**Database Interaction:** CRUD on `sharedResources/{resourceId}`.

**Possible Errors:** `400` invalid enum, `409` duplicate/delete-blocked, `404` not found.

---

### 13.8 Resource Bookings (`resourceBookings`) — Booking Conflict Detection

**Responsibilities:** Create/cancel bookings; enforce time-overlap conflict prevention; auto-complete past bookings (Cloud Function).

**Business Rules (Booking Lifecycle — database spec Section 16):**
- **Create:** within a Firestore transaction — query `resourceBookings` where `resourceId == X AND status == "confirmed"`, then in application code (Firestore cannot do native range-overlap queries) check whether `[startTime, endTime)` overlaps any existing confirmed booking for the same resource. If overlap found → reject `409 Conflict`. Else create `resourceBookings/{id}` with `status="confirmed"`.
- Booking duration and advance-booking window are validated against the target `sharedResources.bookingRules` (`minDurationMinutes` ≤ duration ≤ `maxDurationMinutes`; `startTime` within `advanceBookingDays` of now).
- `startTime < endTime` strictly enforced.
- **Cancel:** `status="cancelled"`; `cancellationReason` required (non-empty) when cancelling.
- **Auto-Complete:** only the scheduled Cloud Function transitions `confirmed` → `completed` for `endTime < now()`.
- Creates `notifications` (`booking_confirmed` on create, `booking_cancelled` on cancel) for the booking employee and `attendeeIds`.

**Input Validation:** `title` 2–200 chars; `attendeeIds` bounded (<100), each must reference an existing employee; `status` ∈ `["confirmed","cancelled","completed"]`.

**Output:** ResourceBooking entity with `resourceSnapshot`/`employeeSnapshot`.

**Database Interaction:** Transactional overlap-check + create on `resourceBookings`; reads `sharedResources.bookingRules`.

**Possible Errors:** `409` time overlap / resource not active, `400` invalid time range or duration outside booking rules, `404` resource/employee/attendee not found, `422` `cancellationReason` missing on cancel.

---

### 13.9 Maintenance Requests (`maintenanceRequests`, `/approvals`, `/logs`) — Maintenance Approval Workflow

**Responsibilities:** Create maintenance requests; approve/reject; assign technician; progress status through completion; append-only approval and log subcollections.

**Business Rules (Maintenance Lifecycle — database spec Section 17):**
- **Create:** `requestId` (`MR-YYYY-#####`) generated via `counters/maintenanceRequests`; `status` defaults `"pending_approval"`; `assets/{assetId}.status` untouched at this point; a `logs` subdoc `action="created"` is appended.
- **Approve** (`POST /{requestId}/approve`, requires `perm_maintenance_approve`): within a transaction — create `approvals/{id}` with `decision="approved"`; update request `status="approved"`; append `logs` `action="approved"`; update `assets/{assetId}.status="in_maintenance"`; notify requester (`maintenance_status_change`).
- **Reject:** create `approvals/{id}` `decision="rejected"`; request `status="rejected"`; append `logs` `action="rejected"`; asset status **unchanged**; notify requester.
- **Assign Technician:** `assignedTechnicianId` set (must reference an employee); `assignedTechnicianSnapshot` populated; append `logs` `action="assigned"`.
- **Progress to In Progress / Completed:** `status_changed` logged with `previousStatus`/`newStatus`; on completion, `completedAt` set, `actualCost` recorded, `assets/{assetId}.status` → `"available"` (or `"retired"` via a separate explicit action if unrepairable); notify requester.
- **Cancel:** permitted only while `status` ∈ `["pending_approval","approved"]`; `status="cancelled"`; `logs` appended.
- Every transition is written to both the request's `logs` subcollection **and** the global `auditLogs` collection.

**Input Validation:** `issueDescription` 10–5000 chars; `priority` ∈ `["low","medium","high","critical"]`; `status` ∈ `["pending_approval","approved","rejected","in_progress","completed","cancelled"]`; `approvals.decision` ∈ `["approved","rejected"]`; `logs.action` ∈ enum list (database spec 25); costs ≥ 0 integers; `attachmentUrls` max 10.

**Output:** MaintenanceRequest entity with nested/related `approvals`/`logs` available via dedicated subcollection endpoints (append-only, list/get only).

**Database Interaction:** CRUD + transitions on `maintenanceRequests/{requestId}`; append-only writes to `approvals`/`logs` subcollections; transactional asset-status updates on approve/complete.

**Possible Errors:** `400` invalid status/priority/enum, `403` approve/reject without `perm_maintenance_approve`, `404` asset/technician not found, `409` invalid state transition (e.g., approving an already-approved request), `422` cancel attempted outside allowed states.

---

### 13.10 Audit Cycles (`auditCycles`, `/reports`) — Audit Workflow

**Responsibilities:** Plan and run periodic asset verification audits; collect per-asset audit reports; compute compliance rate.

**Business Rules (Audit Lifecycle — database spec Section 18):**
- **Create Cycle:** `cycleId` (`AC-YYYY-Qn`) app-generated (not a sequential counter — a business-meaningful code supplied/validated at creation); `status="planned"`; backend computes `totalAssetsInScope` by querying `assets` where `departmentId in departmentIds` and (if set) `categoryId in categoryIds` and `isDeleted==false`; notifies `assignedAuditorIds` (`audit_assigned`).
- **Start Cycle:** manual or scheduled trigger at `scheduledStart` → `status="in_progress"`.
- **Submit Report** (`POST /{cycleId}/reports`, auditor only): create `reports/{reportId}`; Cloud Function increments `assetsAudited`; if `found==false` OR `actualCondition != expectedCondition`, increments `discrepanciesFound` and notifies department head/admins (`audit_discrepancy`); a discrepancy involving damage **may** trigger backend orchestration to auto-create a `maintenanceRequests` document (explicit service-layer call, not a native Firestore trigger).
- **Close Cycle:** `status="completed"`, `actualEnd=SERVER_TIMESTAMP`; recompute `dashboardAggregates.auditComplianceRate = (assetsAudited - discrepanciesFound) / totalAssetsInScope * 100`.
- `reports` subcollection is append-only/immutable — no update/delete endpoints.

**Input Validation:** `name` 2–150 chars; `scheduledEnd ≥ scheduledStart`; `status` ∈ `["planned","in_progress","completed","cancelled"]`; `departmentIds`/`assignedAuditorIds` must reference existing docs; `reports.actualCondition` ∈ condition enum; `discrepancyNotes` required if `found==false` or condition mismatch, ≤2000 chars; `photoUrls` max 10.

**Output:** AuditCycle entity; reports listed via dedicated subcollection endpoint.

**Database Interaction:** CRUD on `auditCycles/{cycleId}`; scoped read query against `assets` at creation; append-only writes to `reports`; Cloud-Function-maintained counters; write to `dashboardAggregates` on close.

**Possible Errors:** `400` invalid status/date range/enum, `403` non-auditor submitting report, `404` department/category/employee/asset not found, `409` invalid state transition (e.g., closing a `planned` cycle), `422` missing required `discrepancyNotes`.

---

### 13.11 Notifications (`notifications`) — Notification Generation

**Responsibilities:** Generate notifications as a side effect of other modules' events; list/mark-read/clear for the requesting employee only.

**Business Rules (Notification Lifecycle — database spec Section 19):**
- Notifications are **never created directly via a public "create notification" endpoint** — they are always a side effect emitted by the originating service (`AllocationService`, `BookingService`, `MaintenanceService`, `AuditService`) or a Cloud Function trigger, one document per recipient.
- A caller may only list/read/mark-read/clear notifications where `recipientId == self` — enforced at the service layer regardless of RBAC role (a manager cannot read another employee's notifications through this module).
- **Mark Read:** `isRead=true`, `readAt=SERVER_TIMESTAMP`.
- **Hard delete permitted** for `notifications` (user-cleared) — the one client-facing hard-delete path in the system beyond admin cleanup tools, per database spec Section 11.2.
- Archival of read notifications older than 6 months is Cloud-Function-only (Section 12), not client-triggered.

**Input Validation:** `type` ∈ enum list (database spec 25); `relatedEntityType` ∈ `["asset","allocation","resource","booking","maintenanceRequest","auditCycle", null]`; `title` 2–150 chars; `body` ≤1000 chars.

**Output:** Notification entity, scoped strictly to the authenticated employee.

**Database Interaction:** Read/update/hard-delete on `notifications/{notificationId}` filtered by `recipientId`; creation only from internal service calls, never from a public route handler.

**Possible Errors:** `403` accessing another employee's notification, `404` notification not found, `400` invalid type/relatedEntityType.

---

### 13.12 Dashboard Aggregation (`dashboardAggregates`)

**Responsibilities:** Serve precomputed KPI reads; provide the one sanctioned on-demand recomputation path.

**Business Rules (database spec Section 20):**
- **Dashboard reads never scan source collections** — they read `dashboardAggregates/{aggregateId}` documents only (`global_kpis`, `dept_{departmentId}`, `daily_{YYYY-MM-DD}`), O(1) regardless of org size.
- All counter fields (`totalAssets`, `assetsByStatus`, `totalActiveAllocations`, etc.) are written **exclusively** by Cloud Function triggers (Section 12) applying incremental deltas — the API layer for this module is **read-only** for regular callers.
- The single exception is `POST /api/v1/dashboard/recompute` (admin/elevated permission only): triggers a full, offline-style rebuild of a specified `dashboardAggregates` document from source collections — the only sanctioned full-collection-scan code path in the entire backend, and it must not run on any user-facing read path.
- Responses must surface `lastComputedAt` so the UI can present the value as "as of" rather than real-time-exact (eventually consistent model, database spec 20.4).

**Input Validation:** `scope` ∈ `["global","department","daily"]`; `scopeRefId` required/shaped per scope.

**Output:** DashboardAggregate entity, read-only for standard callers.

**Database Interaction:** `GET` reads on `dashboardAggregates/{aggregateId}`; `recompute` triggers scoped full-scan aggregation writes (`createdBy`/`updatedBy = "system"` even though admin-triggered, consistent with spec's system-write convention for this collection).

**Possible Errors:** `404` aggregate key not found/not yet computed, `403` recompute without elevated permission, `400` invalid scope/scopeRefId combination.

---

### 13.13 System Audit Trail (`auditLogs`)

**Responsibilities:** Immutable, cross-entity change trail; read-only reporting API for compliance/forensics.

**Business Rules:**
- Every mutating operation across every other module writes an `auditLogs` entry as part of the same logical operation (Section 10.5) — `entityType`, `entityId`, `action` ∈ `["create","update","delete","soft_delete","restore"]`, `performedBy` (or `"system"`), `changedFields`, `beforeSnapshot`/`afterSnapshot` (changed fields only, not full documents).
- **No public create/update/delete endpoints exist for this collection** — it is written only by the backend service layer itself (Section 11.4), consistent with database spec Section 21.5/21.6 (immutability, service-account-only writer).
- Only `GET` (list/get) endpoints are exposed, gated by an elevated/compliance-view permission.

**Input Validation:** N/A for client input (read-only module); query filters restricted to `entityType`, `entityId`, `performedBy` (declared filter fields, database spec 10.14).

**Output:** AuditLogEntry entities, sorted `createdAt DESC` by default.

**Database Interaction:** Read-only queries against `auditLogs`, using the composite indexes declared in database spec Section 9.2; collection-group queries used only where explicitly declared (e.g., cross-parent `logs` queries per database spec Section 8.4).

**Possible Errors:** `403` insufficient permission to view audit trail, `400` undeclared filter field.

---

## 14. Error Handling

1. All predictable failures are raised as typed exceptions from `shared/errors/` — never bare `Exception`/`ValueError` from service code:
   - `NotFoundError`, `ConflictError`, `ValidationError`, `ForbiddenError`, `UnauthenticatedError`, `BusinessRuleError` (base class per project rules Section 16, extended per-domain where useful, e.g. `AllocationConflictError(ConflictError)`, `BookingOverlapError(ConflictError)`).
2. A single global exception handler (`presentation/middleware/error_handler.py`) maps each exception type to the status codes and response envelope in Sections 8.3/9 — route handlers never construct error responses manually.
3. **No silent `except` blocks anywhere** — every caught exception is logged, re-raised as a typed domain exception, or explicitly handled with a documented reason (project rules Section 16).
4. User-facing error messages are safe/generic; full internal detail (stack trace, Firestore error codes, raw exception text) is written only to structured logs with a correlation/request ID, never returned in the API response.
5. Fail fast on invalid state: services validate all preconditions (existence, permission, business invariants) before issuing any Firestore write — no partial/corrupted writes are ever attempted.

---

## 15. Logging

1. Structured logger (JSON output) configured once in `shared/logging/`, used everywhere — no raw `print`/`logging.info` string concatenation.
2. Log levels: `debug` (verbose dev tracing), `info` (successful operations, lifecycle transitions), `warn` (recoverable issues, e.g., a Cloud Function retry), `error` (unhandled exceptions, failed transactions).
3. Every log entry includes: module, operation name, correlation/request ID, and (when available) `employeeId` of the acting user — never the full request payload if it may contain PII beyond what's needed to trace the failure.
4. **Never log secrets, tokens, passwords, or full PII payloads** — employee `email`/`phone` are logged only as references (`employeeId`) unless a specific debugging need is scoped and reviewed.
5. Every business-rule rejection (`409`, `422`) is logged at `info`/`warn` level with enough context to reconstruct why the rule fired, distinct from `error`-level logs reserved for genuine failures.

---

## 16. Exception Handling & Transactions

1. Any operation touching multiple documents that must stay consistent (allocate: allocation + asset; return: allocation + asset; maintenance approve: request + log + asset; booking create: overlap-check + create; audit report: report + cycle counters) is wrapped in a **Firestore transaction** (`infrastructure/firestore/transactions.py` helper) or `WriteBatch`, per database spec Section 4 and the Lifecycle Data Flow sections (14–19).
2. Transactions follow the **read-then-write** pattern required by Firestore: all reads needed to validate business rules occur before any writes within the same transaction, so Firestore's optimistic concurrency control can safely retry on contention.
3. Transactions are scoped to the **service layer only** — repositories provide the primitive read/write calls used inside a transaction; they never open/commit transactions themselves, keeping transaction boundaries a business-logic decision.
4. Firestore's transaction limits (documents/operations per transaction) are respected; any operation that would need to touch more documents than a single transaction allows is flagged rather than silently split into a non-atomic sequence of writes (project rules Section 1, database spec Section 2.9).
5. On transaction failure after Firestore's automatic retries are exhausted, the service raises a typed exception (`500`-mapped) and logs full context — no silent fallback to a non-transactional write path.

---

## 17. Security Rules Alignment

The backend assumes and relies on the following Firestore Security Rules posture (database spec Section 21), and must not implement anything that would require weakening it:

1. All reads/writes to Firestore require authentication — enforced at the rules layer as a baseline, with the backend's own auth dependency as the primary gate for all API traffic.
2. Firestore Security Rules restrict **direct client writes** to read-only for authenticated users on most collections — all writes are expected to flow through this backend's Admin-SDK-authenticated service account, which bypasses rules by design. The backend must never expose a code path that forwards a client's raw write intent straight to Firestore without passing through service-layer validation.
3. `counters`, `dashboardAggregates`, and `auditLogs` are writable only by the backend service account — no endpoint in this backend ever accepts a client-supplied value for fields in these collections beyond the sanctioned `recompute` admin action (13.12).
4. `approvals`, `logs` (maintenance), and `reports` (audit) subcollections are treated as immutable by the backend — no `update`/`delete` service methods are implemented for them, matching the rules-layer `deny update/delete` posture.
5. Sensitive/financial fields are filtered at the backend serialization layer (Section 6.5) because Firestore has no field-level security — this is a backend responsibility, not delegated to rules.

---

## 18. Testing Strategy

Per project rules Section 14, specialized for this stack:

1. **Unit tests** (`tests/unit/`, mirrors `src/` tree): test `domain/rules/` pure functions (overlap detection, status-transition validity, compliance-rate math) and `application/services/` with **mocked repository interfaces** — no live Firestore connection, fully deterministic, no network calls.
2. **Integration tests** (`tests/integration/`): test `infrastructure/firestore/repositories/` and `transactions.py` against the **Firestore Emulator** — verifies actual document shapes match the schema exactly, transaction atomicity, and composite-index-satisfiable queries.
3. **E2E tests** (`tests/e2e/`): full API tests via FastAPI `TestClient` against Firestore Emulator + Firebase Auth Emulator — cover the full request lifecycle including auth, RBAC, validation, and response envelope shape for every endpoint in Section 8/13.
4. Every module in Section 13 has: unit tests for each business rule listed, integration tests for its repository, and at least one E2E test per endpoint (happy path + each documented error case).
5. Tests must be deterministic — no reliance on real network calls, wall-clock timers, or unseeded random data; time-dependent logic (overdue allocation, booking auto-complete, archival) is tested by injecting a fixed/mockable clock.
6. Test file paths mirror source file paths exactly (project rules Section 14.4), e.g. `src/application/services/allocation_service.py` → `tests/unit/application/services/test_allocation_service.py`.
7. No PR merges with failing tests or reduced coverage on touched files (project rules Section 14.2), and CI runs unit + integration (emulator-backed) + e2e suites on every PR.

---

## 19. Scope Boundary (Explicit)

To satisfy "APIs only for features defined in the database specification" and "no extra functionality":

- **No collections, fields, endpoints, or background jobs exist in this backend beyond what Sections 5–25 of `01_database_claude.md` define.**
- No generic "admin panel" CRUD beyond the modules in Section 13 above.
- No payroll, vendor/supplier, cost-center, or depreciation-tracking endpoints — these are explicitly **future extensibility** items (database spec Section 24) and are out of scope until that document is updated first.
- No multi-tenant (`orgId`) logic — single-tenant scope only, per database spec Section 3.9/24.1, until the schema is extended.
- Any feature request not traceable to a specific section of `01_database_claude.md` must be flagged back to the requester rather than implemented, per project rules Section 1 and Section 26.

---

**End of Document — this file is the permanent, authoritative backend architecture specification for this project. All backend implementation must conform to it, and to `01_database_claude.md` and `04_project_rules_claude.md`, exactly. Any change to backend architecture, module scope, or API surface must be made here first.**
