from datetime import datetime
from google.cloud import firestore
from src.infrastructure.firestore.client import db

def get_next_sequence_id(transaction: firestore.Transaction, counter_id: str, default_prefix: str, default_padding: int) -> str:
    """
    Generate the next business-facing ID inside a Firestore transaction.
    E.g. AST-000123, RES-000045, EMP-00231, or MR-2026-00042.
    """
    counter_ref = db.collection("counters").document(counter_id)
    snapshot = counter_ref.get(transaction=transaction)
    
    current_year = datetime.utcnow().year
    
    if not snapshot.exists:
        prefix = default_prefix
        padding = default_padding
        new_value = 1
        data = {
            "value": new_value,
            "prefix": prefix,
            "padding": padding,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        if counter_id == "maintenanceRequests":
            data["year"] = current_year
        transaction.set(counter_ref, data)
    else:
        doc_data = snapshot.to_dict() or {}
        prefix = doc_data.get("prefix", default_prefix)
        padding = doc_data.get("padding", default_padding)
        new_value = doc_data.get("value", 0) + 1
        
        updates = {
            "value": new_value,
            "updatedAt": firestore.SERVER_TIMESTAMP
        }
        
        if counter_id == "maintenanceRequests":
            doc_year = doc_data.get("year")
            if doc_year != current_year:
                new_value = 1
                updates["value"] = 1
                updates["year"] = current_year
                
        transaction.update(counter_ref, updates)

    # Format the ID
    if counter_id == "maintenanceRequests":
        return f"{prefix}-{current_year}-{str(new_value).zfill(padding)}"
    else:
        return f"{prefix}-{str(new_value).zfill(padding)}"

def get_next_asset_tag(transaction: firestore.Transaction) -> str:
    return get_next_sequence_id(transaction, "assets", "AST", 6)

def get_next_resource_code(transaction: firestore.Transaction) -> str:
    return get_next_sequence_id(transaction, "resources", "RES", 6)

def get_next_employee_code(transaction: firestore.Transaction) -> str:
    return get_next_sequence_id(transaction, "employees", "EMP", 5)

def get_next_maintenance_request_number(transaction: firestore.Transaction) -> str:
    return get_next_sequence_id(transaction, "maintenanceRequests", "MR", 5)
