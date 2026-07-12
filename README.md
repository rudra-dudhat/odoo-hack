# odoo-hack

## Overview

This repository contains a small Firebase-backed project with a frontend and Firestore configuration.

- `firebase/firestore.rules` — Firestore security rules for authenticated read access and admin/manager restrictions.
- `firebase/firestore.indexes.json` — Firestore composite index definitions for collections such as `employees`, `assets`, `resourceBookings`, `maintenanceRequests`, and `notifications`.
- `frontend/index.html` — Simple frontend entry point.
- `frontend/style.css` — Tailwind CSS configuration and stylesheet.

## Firebase Setup

This project uses Firestore for read-only client access and structured indexes.

### Firestore rules

The security rules allow:
- authenticated users to read most data collections,
- admin users to read audit logs and archive collections,
- manager/admin users to read dashboard aggregates,
- no client writes (all writes are intended to go through a trusted backend or Admin SDK).

### Firestore indexes

The `firebase/firestore.indexes.json` file defines required composite indexes for queries across collections like:
- `employees`
- `assets`
- `assetAllocations`
- `resourceBookings`
- `maintenanceRequests`
- `auditCycles`
- `notifications`
- `auditLogs`

## Deploying Firebase configuration

If you have the Firebase CLI installed and your project initialized, deploy the Firestore rules and indexes with:

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

## Notes

- The frontend currently includes only a basic `index.html` shell.
- The Firestore config files are intended to support an Odoo-like asset and maintenance tracking system.
- If you add Firebase initialization or authentication in the frontend, make sure to keep your Firebase API keys and project settings secure.
