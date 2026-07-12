from fastapi import APIRouter, HTTPException, Body
from src.infrastructure.firestore.client import db
from firebase_admin import firestore
from datetime import datetime, timezone

router = APIRouter()

@firestore.transactional
def increment_alloc_counter(transaction, counter_ref):
    snapshot = counter_ref.get(transaction=transaction)
    new_value = 1
    if snapshot.exists:
        new_value = snapshot.get("value") + 1
        transaction.update(counter_ref, {"value": new_value})
    else:
        transaction.set(counter_ref, {"value": new_value, "prefix": "ALLOC", "padding": 6})
    return f"ALLOC-{str(new_value).zfill(6)}"

@router.get("")
async def get_allocations():
    try:
        allocs_ref = db.collection('assetAllocations').order_by('allocatedAt', direction=firestore.Query.DESCENDING).stream()
        allocs = []
        for doc in allocs_ref:
            data = doc.to_dict()
            data['id'] = doc.id
            allocs.append(data)
        return {"data": allocs}
    except Exception as e:
        print(f"Error fetching allocations: {e}")
        # Firestore composite index might be missing, fallback to unordered
        try:
            allocs_ref = db.collection('assetAllocations').stream()
            allocs = [ {**doc.to_dict(), 'id': doc.id} for doc in allocs_ref ]
            return {"data": allocs}
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to fetch allocations")

@router.post("")
async def create_allocation(payload: dict = Body(...)):
    try:
        asset_id = payload.get("assetId")
        employee_id = payload.get("employeeId")
        notes = payload.get("notes", "")

        if not asset_id or not employee_id:
            raise HTTPException(status_code=400, detail="assetId and employeeId are required")

        # 1. Fetch asset to check status and condition
        asset_ref = db.collection("assets").document(asset_id)
        asset_doc = asset_ref.get()

        if not asset_doc.exists:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset_data = asset_doc.to_dict()
        if asset_data.get("status") != "available":
            raise HTTPException(status_code=400, detail=f"Asset is not available. Current status: {asset_data.get('status')}")

        # 2. Generate allocation ID
        transaction = db.transaction()
        counter_ref = db.collection("counters").document("allocations")
        alloc_id = increment_alloc_counter(transaction, counter_ref)

        now = datetime.now(timezone.utc)
        
        # 3. Create allocation document
        allocation_doc = {
            "assetId": asset_id,
            "assetSnapshot": {"assetTag": asset_id, "name": asset_data.get("name")},
            "employeeId": employee_id,
            "employeeSnapshot": {"fullName": payload.get("employeeName", employee_id), "employeeCode": employee_id},
            "allocatedAt": now,
            "expectedReturnDate": None,
            "returnedAt": None,
            "status": "active",
            "conditionAtAllocation": asset_data.get("condition", "good"),
            "conditionAtReturn": None,
            "notes": notes,
            "createdAt": now,
            "updatedAt": now,
            "createdBy": "uid_admin001",
            "updatedBy": "uid_admin001",
            "isDeleted": False
        }

        # 4. Save allocation and update asset status (in a batch for atomicity)
        batch = db.batch()
        batch.set(db.collection("assetAllocations").document(alloc_id), allocation_doc)
        batch.update(asset_ref, {
            "status": "allocated",
            "currentAllocationId": alloc_id,
            "currentHolderSnapshot": {"employeeId": employee_id, "fullName": payload.get("employeeName", employee_id)},
            "updatedAt": now
        })
        batch.commit()
        
        allocation_doc['id'] = alloc_id
        return {"message": "Asset allocated successfully", "data": allocation_doc}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error allocating asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to allocate asset")
