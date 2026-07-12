from fastapi import APIRouter, HTTPException
from src.infrastructure.firestore.client import db

router = APIRouter()


@router.get("", tags=["Audit Cycles"])
async def get_audit_cycles():
    try:
        cycles_ref = db.collection("auditCycles").stream()
        cycles = []
        for doc in cycles_ref:
            data = doc.to_dict()
            data["id"] = doc.id
            cycles.append(data)
        return {"data": cycles}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch audit cycles") from exc
