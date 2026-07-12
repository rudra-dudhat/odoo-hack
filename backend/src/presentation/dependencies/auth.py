from fastapi import Header
from src.infrastructure.firestore.client import db
from src.infrastructure.auth.firebase_auth import verify_firebase_token
from src.shared.errors import UnauthenticatedError, ForbiddenError
from src.shared.logging import employee_id_ctx, logger
from src.domain.entities.employee import Employee
from src.domain.enums import EmployeeStatus

async def get_current_employee(authorization: str | None = Header(default=None)) -> Employee:
    """
    FastAPI dependency to authenticate requests.
    Validates the bearer ID token and returns the corresponding active Employee entity.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthenticatedError("Missing or invalid Authorization header")
    
    token = authorization.split("Bearer ")[1].strip()
    decoded_token = verify_firebase_token(token)
    uid = decoded_token.get("uid")
    if not uid:
        raise UnauthenticatedError("Invalid token: uid payload missing")
        
    # Bind employee ID to request logging context
    employee_id_ctx.set(uid)
    
    # Fetch employee record from Firestore
    employee_ref = db.collection("employees").document(uid)
    snapshot = employee_ref.get()
    
    if not snapshot.exists:
        raise UnauthenticatedError("Authenticated employee profile not found")
        
    employee_data = snapshot.to_dict() or {}
    employee_data["id"] = snapshot.id
    
    # Enforce access checks
    if employee_data.get("isDeleted", False):
        raise UnauthenticatedError("Employee account has been deleted")
        
    status = employee_data.get("status")
    if status in (EmployeeStatus.SUSPENDED, EmployeeStatus.INACTIVE):
        raise ForbiddenError("Access denied: Employee account is suspended or inactive")
        
    try:
        employee = Employee.model_validate(employee_data)
        return employee
    except Exception as e:
        logger.error(f"Error parsing authenticated employee record: {e}")
        raise UnauthenticatedError("Invalid employee profile schema")
