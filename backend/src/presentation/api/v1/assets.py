from fastapi import APIRouter, HTTPException, Body
from src.infrastructure.firestore.client import db
from firebase_admin import firestore
from datetime import datetime, timezone

router = APIRouter()

@firestore.transactional
def increment_asset_counter(transaction, counter_ref):
    snapshot = counter_ref.get(transaction=transaction)
    new_value = 1
    if snapshot.exists:
        new_value = snapshot.get("value") + 1
        transaction.update(counter_ref, {"value": new_value})
    else:
        transaction.set(counter_ref, {"value": new_value, "prefix": "AST", "padding": 6})
    return f"AST-{str(new_value).zfill(6)}"

@router.get("")
async def get_assets():
    try:
        assets_ref = db.collection('assets').stream()
        assets = []
        for doc in assets_ref:
            asset_data = doc.to_dict()
            asset_data['id'] = doc.id
            assets.append(asset_data)
        return {"data": assets}
    except Exception as e:
        print(f"Error fetching assets: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch assets")

@router.post("")
async def create_asset(payload: dict = Body(...)):
    try:
        # Generate new ID via transaction
        transaction = db.transaction()
        counter_ref = db.collection("counters").document("assets")
        new_asset_tag = increment_asset_counter(transaction, counter_ref)

        now = datetime.now(timezone.utc)
        
        asset_doc = {
            "assetTag": new_asset_tag,
            "name": payload.get("name", "Unknown Asset"),
            "categoryId": payload.get("categoryId", "cat_general"),
            "categorySnapshot": {"name": payload.get("categoryName", "General")},
            "departmentId": payload.get("departmentId", "dep_general"),
            "departmentSnapshot": {"name": payload.get("departmentName", "General")},
            "serialNumber": payload.get("serialNumber", ""),
            "purchaseCost": int(payload.get("purchaseCost", 0)),
            "currency": "USD",
            "status": "available",
            "condition": payload.get("condition", "good"),
            "createdAt": now,
            "updatedAt": now,
            "createdBy": "uid_admin001",
            "updatedBy": "uid_admin001",
            "isDeleted": False
        }

        # Save to DB
        db.collection("assets").document(new_asset_tag).set(asset_doc)
        
        asset_doc['id'] = new_asset_tag
        return {"message": "Asset created successfully", "data": asset_doc}

    except Exception as e:
        print(f"Error creating asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to create asset")
